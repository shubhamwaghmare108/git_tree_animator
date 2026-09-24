"""
Git command parser and executor.
Simulates the effect of Git commands on repository state.
"""

import hashlib
import shlex
from typing import List, Optional, Tuple
from datetime import datetime

from .state import GitState, Commit, BranchPointer, TagPointer, ReflogEntry, WorkingTreeState, StashEntry
from .errors import GitError, GitCommandError, GitRefNotFoundError


class GitCommandExecutor:
    """Executes Git commands on repository state."""
    
    def __init__(self):
        self._sha_counter = 0  # For deterministic SHA generation
    
    def execute(self, command: str, state: GitState) -> Tuple[GitState, str]:
        """
        Parse and execute a git command.
        
        Returns:
            (new_state, output_message)
        
        Raises:
            GitCommandError: If command execution fails
        """
        command = command.strip()
        
        if not command.startswith("git "):
            raise GitCommandError("Command must start with 'git'")
        
        # Remove 'git ' prefix and split
        try:
            parts = shlex.split(command[4:])
        except ValueError as exc:
            raise GitCommandError(f"invalid command quoting: {exc}")
        if not parts:
            raise GitCommandError("No command specified")
        
        git_cmd = parts[0].replace("-", "_")
        args = parts[1:]
        
        # Find and call the handler method
        method_name = f"cmd_{git_cmd}"
        if not hasattr(self, method_name):
            raise GitCommandError(f"unknown command '{parts[0]}'")
        
        try:
            method = getattr(self, method_name)
            return method(args, state)
        except GitCommandError:
            raise
        except Exception as e:
            raise GitCommandError(f"Error executing '{parts[0]}': {str(e)}")
    
    # ========== Stash Commands ==========

    def cmd_stash(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git stash [push] [-m message] - Save working tree and index changes."""
        if not state.branches:
            raise GitCommandError("Not a git repository")
        if args and args[0] not in ("push",):
            if args[0] == "list":
                return state, self._format_stash_list(state)
            raise GitCommandError("Usage: git stash [push] [-m \"message\"]")
        if args and args[0] == "push":
            args = args[1:]
        message = "WIP on " + (state.head if not state.head_is_detached else state.head[:7])
        if "-m" in args:
            i = args.index("-m")
            if i + 1 >= len(args):
                raise GitCommandError("Stash message cannot be empty")
            message = " ".join(args[i + 1:]).strip('"').strip("'")
        if not state.working_tree.has_changes() and not state.index.staged_content and not state.index.staged_deletions:
            raise GitCommandError("No local changes to save")
        new_state = state.copy()
        stash_id = len(new_state.stashes)
        new_state.stashes.insert(0, StashEntry(
            stash_id=stash_id,
            message=message,
            base_sha=state.get_head_commit_sha(),
            modified_files=dict(state.working_tree.modified_files),
            new_files=dict(state.working_tree.new_files),
            deleted_files=set(state.working_tree.deleted_files),
            staged_content=dict(state.index.staged_content),
            staged_deletions=set(state.index.staged_deletions),
        ))
        new_state.working_tree = WorkingTreeState()
        new_state.index.staged_files.clear()
        new_state.index.staged_content.clear()
        new_state.index.staged_deletions.clear()
        self._renumber_stashes(new_state)
        new_state.reflog.append(ReflogEntry(ref="HEAD", action="stash", sha=state.get_head_commit_sha() or "", message=message))
        return new_state, f"Saved working directory and index state as {new_state.stashes[0].name}"

    def _renumber_stashes(self, state: GitState) -> None:
        for index, stash in enumerate(state.stashes):
            state.stashes[index] = StashEntry(
                stash_id=index,
                message=stash.message,
                base_sha=stash.base_sha,
                modified_files=dict(stash.modified_files),
                new_files=dict(stash.new_files),
                deleted_files=set(stash.deleted_files),
                staged_content=dict(stash.staged_content),
                staged_deletions=set(stash.staged_deletions),
            )

    def _format_stash_list(self, state: GitState) -> str:
        if not state.stashes:
            return ""
        return "\n".join(f"{stash.name}: {stash.message}" for stash in state.stashes)

    def _get_stash(self, args: List[str], state: GitState) -> StashEntry:
        if not state.stashes:
            raise GitCommandError("No stash entries found")
        if not args:
            return state.stashes[0]
        token = args[0]
        if token.startswith("stash@{") and token.endswith("}"):
            try:
                index = int(token[7:-1])
            except ValueError:
                raise GitCommandError(f"Invalid stash reference '{token}'")
            if index < 0 or index >= len(state.stashes):
                raise GitCommandError(f"stash entry '{token}' not found")
            return state.stashes[index]
        raise GitCommandError("Usage: git stash apply [stash@{n}]")

    def _apply_stash(self, stash: StashEntry, state: GitState) -> GitState:
        new_state = state.copy()
        for filename, content in stash.modified_files.items():
            new_state.working_tree.modified_files[filename] = content
        for filename, content in stash.new_files.items():
            new_state.working_tree.new_files[filename] = content
        for filename in stash.deleted_files:
            new_state.working_tree.deleted_files.add(filename)
        for filename, content in stash.staged_content.items():
            new_state.index.staged_files[filename] = self._hash_content(content)
            new_state.index.staged_content[filename] = content
        new_state.index.staged_deletions.update(stash.staged_deletions)
        return new_state

    def cmd_stash_list(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        return state, self._format_stash_list(state)

    def cmd_stash_apply(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        stash = self._get_stash(args, state)
        new_state = self._apply_stash(stash, state)
        new_state.reflog.append(ReflogEntry(ref="HEAD", action="stash", sha=stash.base_sha or "", message=f"apply {stash.name}"))
        return new_state, f"Applied {stash.name}"

    def cmd_stash_pop(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        stash = self._get_stash(args, state)
        new_state = self._apply_stash(stash, state)
        new_state.stashes.pop(stash.stash_id)
        self._renumber_stashes(new_state)
        new_state.reflog.append(ReflogEntry(ref="HEAD", action="stash", sha=stash.base_sha or "", message=f"pop {stash.name}"))
        return new_state, f"Applied and dropped {stash.name}"

    def cmd_stash_drop(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        stash = self._get_stash(args, state)
        new_state = state.copy()
        new_state.stashes.pop(stash.stash_id)
        self._renumber_stashes(new_state)
        new_state.reflog.append(ReflogEntry(ref="HEAD", action="stash", sha=stash.base_sha or "", message=f"drop {stash.name}"))
        return new_state, f"Dropped {stash.name}"

    # ========== Repository Commands ==========
    
    def cmd_init(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git init - Initialize a new repository."""
        if state.commits:
            raise GitCommandError("Reinitialization of existing repository")
        
        new_state = state.copy()
        new_state.branches["main"] = BranchPointer("main", None)
        new_state.head = "main"
        
        new_state.reflog.append(ReflogEntry(
            ref="HEAD",
            action="init",
            sha="",
            message="init repository"
        ))
        
        return new_state, "Initialized empty Git repository in current directory"
    
    # ========== Staging Commands ==========
    
    def cmd_add(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git add [files] - Stage files."""
        if not state.branches:
            raise GitCommandError("Not a git repository")
        
        if not args or args[0] not in (".", "*"):
            raise GitCommandError("Usage: git add . or git add <file>")
        
        new_state = state.copy()
        head_tree = self._head_tree(state)
        staged_count = 0

        # Stage modified and new files. The working tree stores only
        # differences from HEAD, so successfully staged paths leave the
        # working-tree delta and live in the index until commit/unstage.
        for filename, content in list(new_state.working_tree.modified_files.items()):
            new_state.index.staged_files[filename] = self._hash_content(content)
            new_state.index.staged_content[filename] = content
            new_state.index.staged_deletions.discard(filename)
            del new_state.working_tree.modified_files[filename]
            staged_count += 1

        for filename, content in list(new_state.working_tree.new_files.items()):
            new_state.index.staged_files[filename] = self._hash_content(content)
            new_state.index.staged_content[filename] = content
            new_state.index.staged_deletions.discard(filename)
            del new_state.working_tree.new_files[filename]
            staged_count += 1

        for filename in list(new_state.working_tree.deleted_files):
            if filename in head_tree:
                new_state.index.staged_deletions.add(filename)
                new_state.index.staged_files.pop(filename, None)
                new_state.index.staged_content.pop(filename, None)
                new_state.working_tree.deleted_files.discard(filename)
                staged_count += 1

        return new_state, f"Added {staged_count} files to index"
    
    def cmd_restore(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git restore [--staged] <file> - Restore files."""
        if not args:
            raise GitCommandError("Usage: git restore [--staged] <file>")
        
        new_state = state.copy()
        
        if "--staged" in args:
            # Unstage file
            filename = args[1] if len(args) > 1 else args[0]
            if filename in new_state.index.staged_files:
                del new_state.index.staged_files[filename]
                new_state.index.staged_content.pop(filename, None)
                new_state.index.staged_deletions.discard(filename)
                return new_state, f"Unstaged '{filename}'"
            else:
                raise GitCommandError(f"pathspec '{filename}' did not match any files")
        else:
            # Discard changes in working tree
            filename = args[0]
            if filename in new_state.working_tree.modified_files:
                del new_state.working_tree.modified_files[filename]
                return new_state, f"Restored '{filename}'"
            elif filename in new_state.working_tree.new_files:
                del new_state.working_tree.new_files[filename]
                return new_state, f"Restored '{filename}'"
            else:
                raise GitCommandError(f"pathspec '{filename}' did not match any files")
    
    # ========== Commit Commands ==========
    
    def cmd_commit(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git commit -m "message" - Create a new commit."""
        if not state.branches:
            raise GitCommandError("Not a git repository")
        
        # Parse -m flag
        if not args or args[0] != "-m":
            raise GitCommandError('Usage: git commit -m "message"')
        
        if len(args) < 2:
            raise GitCommandError("Commit message cannot be empty")
        
        message = " ".join(args[1:]).strip('"').strip("'")
        
        # Get current branch
        if state.merge_in_progress:
            raise GitCommandError("You are in the middle of a merge. Resolve conflicts and use 'git merge --continue'.")
        if state.rebase_in_progress:
            raise GitCommandError("You are in the middle of a rebase. Resolve conflicts and use 'git rebase --continue'.")
        if state.cherry_pick_in_progress:
            raise GitCommandError("You are in the middle of a cherry-pick. Resolve conflicts and use 'git cherry-pick --continue'.")
        if state.head_is_detached:
            raise GitCommandError(
                f"Not currently on any branch.\n"
                f"To create a new branch, use git switch -c <branch-name>"
            )
        
        if state.head not in state.branches:
            raise GitCommandError(f"Branch '{state.head}' does not exist")
        
        # Get parent commit
        parent_sha = state.branches[state.head].target_sha
        
        if not parent_sha and state.commits:
            raise GitCommandError("Branch has no commits yet")
        
        new_state = state.copy()
        
        # Build a real snapshot from the parent tree plus staged content.
        parent_tree = {}
        if parent_sha and parent_sha in state.commits:
            parent_tree = dict(state.commits[parent_sha].tree)
        commit_tree = dict(parent_tree)
        for filename, content in new_state.index.staged_content.items():
            commit_tree[filename] = content
        for filename in new_state.index.staged_deletions:
            commit_tree.pop(filename, None)

        # Create new commit
        new_sha = self._generate_sha(message, parent_sha)
        
        parents = [parent_sha] if parent_sha else []
        commit = Commit(
            sha=new_sha,
            message=message,
            parents=parents,
            author="Git Learner",
            timestamp=int(datetime.now().timestamp()),
            tree=commit_tree,
        )
        
        new_state.commits[new_sha] = commit
        
        # Move branch pointer
        new_state.branches[new_state.head] = BranchPointer(
            name=new_state.head,
            target_sha=new_sha
        )
        
        # A successful commit consumes the entire index. Any remaining
        # working-tree deltas are genuinely unstaged and must survive.
        new_state.working_tree.deleted_files.difference_update(new_state.index.staged_deletions)
        new_state.index.staged_files.clear()
        new_state.index.staged_content.clear()
        new_state.index.staged_deletions.clear()
        
        # Add reflog entry
        new_state.reflog.append(ReflogEntry(
            ref="HEAD",
            action="commit",
            sha=new_sha,
            message=message
        ))
        
        return new_state, f"[{new_state.head} {new_sha[:7]}] {message}"
    
    # ========== Remote Commands ==========

    def cmd_remote(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git remote add/list - Manage simulated remotes."""
        new_state = state.copy()
        if not args:
            return new_state, "\n".join(sorted(new_state.remote_urls))
        if args[0] == "add":
            if len(args) != 3:
                raise GitCommandError("Usage: git remote add <name> <url>")
            name, url = args[1], args[2]
            if name in new_state.remote_urls:
                raise GitCommandError(f"remote '{name}' already exists")
            new_state.remote_urls[name] = url
            new_state.remote_servers[name] = {}
            new_state.remotes[name] = {}
            return new_state, f"Added remote '{name}'"
        if args[0] == "-v":
            lines = [
                f"{name}\t{url} (fetch)\n{name}\t{url} (push)"
                for name, url in sorted(new_state.remote_urls.items())
            ]
            return new_state, "\n".join(lines)
        raise GitCommandError("Usage: git remote [add <name> <url>] or git remote -v")

    def cmd_push(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git push <remote> <branch> - Update a simulated remote ref."""
        if len(args) not in (1, 2):
            raise GitCommandError("Usage: git push <remote> [branch]")
        remote_name = args[0]
        if remote_name not in state.remote_servers:
            raise GitCommandError(f"fatal: '{remote_name}' is not a configured remote")
        branch_name = args[1] if len(args) == 2 else state.head
        if state.head_is_detached and len(args) == 1:
            raise GitCommandError("fatal: HEAD is detached; specify a branch to push")
        if branch_name not in state.branches:
            raise GitCommandError(f"error: src refspec '{branch_name}' does not match any branch")
        target_sha = state.branches[branch_name].target_sha
        if not target_sha:
            raise GitCommandError(f"error: branch '{branch_name}' has no commits to push")

        new_state = state.copy()
        new_state.remote_servers.setdefault(remote_name, {})[branch_name] = BranchPointer(
            name=branch_name, target_sha=target_sha
        )
        new_state.remotes.setdefault(remote_name, {})[branch_name] = BranchPointer(
            name=branch_name, target_sha=target_sha
        )
        new_state.reflog.append(ReflogEntry(
            ref=f"{remote_name}/{branch_name}",
            action="push",
            sha=target_sha,
            message=f"pushed {branch_name} to {remote_name}",
        ))
        return new_state, f"To {remote_name}\n * [new branch] {branch_name} -> {branch_name}"

    def cmd_fetch(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git fetch <remote> - Refresh local remote-tracking refs."""
        if len(args) > 1:
            raise GitCommandError("Usage: git fetch [remote]")
        remote_names = [args[0]] if args else sorted(state.remote_servers)
        if not remote_names:
            raise GitCommandError("No remotes configured")

        new_state = state.copy()
        lines = []
        for remote_name in remote_names:
            if remote_name not in new_state.remote_servers:
                raise GitCommandError(f"fatal: '{remote_name}' does not appear to be a git repository")
            tracking = new_state.remotes.setdefault(remote_name, {})
            for branch_name, remote_ptr in new_state.remote_servers[remote_name].items():
                tracking[branch_name] = BranchPointer(branch_name, remote_ptr.target_sha)
                lines.append(f" {remote_name}/{branch_name} -> {remote_name}/{branch_name}")
        new_state.reflog.append(ReflogEntry(
            ref="FETCH_HEAD",
            action="fetch",
            sha="",
            message=f"fetched {', '.join(remote_names)}",
        ))
        return new_state, "\n".join(lines) or "Everything up-to-date"

    def _is_ancestor(self, ancestor_sha: Optional[str], descendant_sha: Optional[str], state: GitState) -> bool:
        if not ancestor_sha:
            return True
        if not descendant_sha:
            return False
        stack = [descendant_sha]
        seen = set()
        while stack:
            sha = stack.pop()
            if sha in seen:
                continue
            seen.add(sha)
            if sha == ancestor_sha:
                return True
            commit = state.commits.get(sha)
            if commit:
                stack.extend(commit.parents)
        return False

    def cmd_pull(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git pull <remote> [branch] - Fetch and fast-forward the current branch."""
        if len(args) not in (1, 2):
            raise GitCommandError("Usage: git pull <remote> [branch]")
        if state.head_is_detached:
            raise GitCommandError("fatal: cannot pull with detached HEAD")
        remote_name = args[0]
        branch_name = args[1] if len(args) == 2 else state.head
        if state.head != branch_name:
            raise GitCommandError("fatal: pull target must be the current branch")
        if remote_name not in state.remote_servers:
            raise GitCommandError(f"fatal: '{remote_name}' is not a configured remote")

        fetched, fetch_msg = self.cmd_fetch([remote_name], state)
        remote_ptr = fetched.remotes.get(remote_name, {}).get(branch_name)
        if not remote_ptr or not remote_ptr.target_sha:
            return fetched, f"{fetch_msg}\nNo remote branch '{branch_name}' to pull from"

        current_sha = fetched.branches[branch_name].target_sha
        target_sha = remote_ptr.target_sha
        if current_sha == target_sha:
            return fetched, f"{fetch_msg}\nAlready up to date."
        if not self._is_ancestor(current_sha, target_sha, fetched):
            raise GitCommandError(
                "fatal: branches have diverged; this educational pull only supports fast-forward"
            )

        new_state = fetched.copy()
        new_state.branches[branch_name] = BranchPointer(branch_name, target_sha)
        new_state.reflog.append(ReflogEntry(
            ref="HEAD",
            action="pull",
            sha=target_sha,
            message=f"fast-forward {branch_name} from {remote_name}/{branch_name}",
        ))
        return new_state, f"{fetch_msg}\nFast-forwarded {branch_name} to {target_sha[:7]}"

    # ========== Tag Commands ==========

    def cmd_tag(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git tag - Create/list/delete lightweight or annotated tags."""
        if not args:
            return state, "\n".join(sorted(state.tags))
        if args[0] == "-d":
            if len(args) != 2:
                raise GitCommandError("Usage: git tag -d <tag>")
            name = args[1]
            if name not in state.tags:
                raise GitCommandError(f"error: tag '{name}' not found")
            new_state = state.copy()
            del new_state.tags[name]
            return new_state, f"Deleted tag '{name}'"
        if args[0] == "-a":
            if len(args) < 2:
                raise GitCommandError('Usage: git tag -a <tag> -m "message" [<commit>]')
            name = args[1]
            if name in state.tags:
                raise GitCommandError(f"fatal: tag '{name}' already exists")
            if "-m" not in args:
                raise GitCommandError('Usage: git tag -a <tag> -m "message" [<commit>]')
            m = args.index("-m")
            if m + 1 >= len(args):
                raise GitCommandError("Tag message cannot be empty")
            message = " ".join(args[m + 1:]).strip('"').strip("'")
            target_ref = args[m + 2] if len(args) > m + 2 else None
            target_sha = self._resolve_ref(target_ref, state) if target_ref else state.get_head_commit_sha()
            if not target_sha:
                raise GitCommandError("fatal: no commit to tag")
            new_state = state.copy()
            new_state.tags[name] = TagPointer(name, target_sha, message, True)
            new_state.reflog.append(ReflogEntry(ref=name, action="tag", sha=target_sha, message=f"tagged {target_sha[:7]}"))
            return new_state, f"Created annotated tag '{name}' at {target_sha[:7]}"
        name = args[0]
        if name.startswith("-"):
            raise GitCommandError('Usage: git tag [-a] <tag> [-m "message"] [<commit>]')
        if name in state.tags:
            raise GitCommandError(f"fatal: tag '{name}' already exists")
        target_ref = args[1] if len(args) > 1 else None
        target_sha = self._resolve_ref(target_ref, state) if target_ref else state.get_head_commit_sha()
        if not target_sha:
            raise GitCommandError("fatal: no commit to tag")
        new_state = state.copy()
        new_state.tags[name] = TagPointer(name, target_sha)
        new_state.reflog.append(ReflogEntry(ref=name, action="tag", sha=target_sha, message=f"tagged {target_sha[:7]}"))
        return new_state, f"Created tag '{name}' at {target_sha[:7]}"

    # ========== Branch Commands ==========
    
    def cmd_branch(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git branch [<branch-name>] - List or create branches."""
        if not args:
            # List branches
            if not state.branches:
                return state, ""
            
            output_lines = []
            for branch_name in sorted(state.branches.keys()):
                marker = "* " if branch_name == state.head else "  "
                output_lines.append(f"{marker}{branch_name}")
            
            return state, "\n".join(output_lines)
        
        # Create new branch
        branch_name = args[0]
        
        if branch_name in state.branches:
            raise GitCommandError(f"A branch named '{branch_name}' already exists")
        
        new_state = state.copy()
        
        # New branch points to current HEAD commit
        current_sha = new_state.get_head_commit_sha()
        
        if not current_sha:
            raise GitCommandError("Cannot create branch: no commits yet")
        
        new_state.branches[branch_name] = BranchPointer(
            name=branch_name,
            target_sha=current_sha
        )
        
        new_state.reflog.append(ReflogEntry(
            ref=branch_name,
            action="branch",
            sha=current_sha,
            message=f"created branch {branch_name}"
        ))
        
        return new_state, f"Created branch '{branch_name}'"
    
    def cmd_branch_d(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git branch -d <branch-name> - Delete a branch."""
        if not args:
            raise GitCommandError("Usage: git branch -d <branch-name>")
        
        branch_name = args[0]
        
        if branch_name == state.head:
            raise GitCommandError(f"error: Cannot delete branch '{branch_name}' checked out at")
        
        if branch_name not in state.branches:
            raise GitCommandError(f"error: branch '{branch_name}' not found")
        
        new_state = state.copy()
        del new_state.branches[branch_name]
        
        return new_state, f"Deleted branch '{branch_name}'"
    
    # ========== Detached HEAD / Recovery Commands ==========

    def _ensure_no_operation_in_progress(self, state: GitState, operation: str) -> None:
        if state.merge_in_progress or state.rebase_in_progress or state.cherry_pick_in_progress:
            raise GitCommandError(f"Cannot {operation} while another Git operation is in progress")

    def cmd_detach(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """Educational helper: detach HEAD at a commit."""
        if not args:
            raise GitCommandError("Usage: git detach <commit>")
        self._ensure_no_operation_in_progress(state, "detach HEAD")
        target_sha = self._resolve_ref(args[0], state)
        if not target_sha:
            raise GitCommandError(f"fatal: bad revision '{args[0]}'")
        new_state = state.copy()
        new_state.head_is_detached = True
        new_state.head = target_sha
        new_state.reflog.append(
            ReflogEntry(
                ref="HEAD",
                action="checkout",
                sha=target_sha,
                message=f"detached HEAD at {target_sha[:7]}",
            )
        )
        return new_state, f"HEAD is now detached at {target_sha[:7]}"

    # ========== Switching/Checkout Commands ==========
    
    def cmd_switch(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git switch <branch> or git switch -c <branch> - Switch branches."""
        if not args:
            raise GitCommandError("Usage: git switch <branch> or git switch -c <new-branch>")
        
        create_new = False
        branch_name = None
        
        if args[0] == "-c":
            create_new = True
            if len(args) < 2:
                raise GitCommandError("Usage: git switch -c <new-branch>")
            branch_name = args[1]
        else:
            branch_name = args[0]
        
        new_state = state.copy()
        
        if create_new:
            # Create and switch to new branch
            if branch_name in new_state.branches:
                raise GitCommandError(f"A branch named '{branch_name}' already exists")
            
            current_sha = new_state.get_head_commit_sha()
            if not current_sha:
                raise GitCommandError("Cannot create branch: no commits yet")
            
            new_state.branches[branch_name] = BranchPointer(
                name=branch_name,
                target_sha=current_sha
            )
        else:
            # Switch to existing branch
            if branch_name not in new_state.branches:
                raise GitCommandError(f"error: pathspec '{branch_name}' did not match any file(s) known to git")
        
        new_state.head = branch_name
        new_state.head_is_detached = False
        
        new_state.reflog.append(ReflogEntry(
            ref="HEAD",
            action="switch",
            sha=new_state.branches[branch_name].target_sha or "",
            message=f"switched to branch '{branch_name}'"
        ))
        
        return new_state, f"Switched to branch '{branch_name}'"
    
    def cmd_checkout(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git checkout <branch> or git checkout -b <branch> - Checkout branch (legacy)."""
        if not args:
            raise GitCommandError("Usage: git checkout <branch> or git checkout -b <new-branch>")
        
        create_new = False
        branch_name = None
        
        if args[0] == "-b":
            create_new = True
            if len(args) < 2:
                raise GitCommandError("Usage: git checkout -b <new-branch>")
            branch_name = args[1]
        else:
            branch_name = args[0]
        
        # Reuse switch logic
        new_args = ["-c", branch_name] if create_new else [branch_name]
        return self.cmd_switch(new_args, state)
    
    # ========== History Commands ==========
    
    def cmd_log(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git log [--oneline] - Show commit history."""
        if not state.commits:
            return state, "fatal: your current branch has no commits yet"
        
        oneline = "--oneline" in args
        
        # Walk the commit tree from current HEAD
        current_sha = state.get_head_commit_sha()
        if not current_sha:
            return state, "HEAD is detached"
        
        visited = set()
        output_lines = []
        
        def walk_commits(sha: str):
            if not sha or sha in visited:
                return
            visited.add(sha)
            
            if sha not in state.commits:
                return
            
            commit = state.commits[sha]
            
            if oneline:
                output_lines.append(f"{commit.short_sha} {commit.message}")
            else:
                output_lines.append(f"commit {commit.sha}")
                output_lines.append(f"Author: {commit.author}")
                output_lines.append(f"Date:   {datetime.fromtimestamp(commit.timestamp)}")
                output_lines.append(f"\n    {commit.message}\n")
            
            # Walk parents
            for parent_sha in commit.parents:
                walk_commits(parent_sha)
        
        walk_commits(current_sha)
        
        return state, "\n".join(output_lines) if output_lines else "No commits to display"
    
    # ========== Status Commands ==========
    
    def cmd_status(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git status - Show repository status."""
        lines = []
        
        if not state.branches:
            return state, "fatal: not a git repository"
        
        branch_name = state.head if not state.head_is_detached else f"HEAD detached at {state.head[:7]}"
        lines.append(f"On branch {branch_name}")
        
        if state.index.staged_files:
            lines.append("\nChanges to be committed:")
            for filename in state.index.staged_files:
                lines.append(f"  (use \"git restore --staged <file>...\" to unstage)")
                lines.append(f"  modified:   {filename}")
        
        if state.working_tree.has_changes():
            lines.append("\nChanges not staged for commit:")
            lines.append("  (use \"git add <file>...\" to update what will be committed)")
            for filename in state.working_tree.modified_files:
                lines.append(f"  modified:   {filename}")
            for filename in state.working_tree.new_files:
                lines.append(f"  new file:   {filename}")
            for filename in state.working_tree.deleted_files:
                lines.append(f"  deleted:    {filename}")
        
        if not state.index.staged_files and not state.working_tree.has_changes():
            lines.append("\nnothing to commit, working tree clean")
        
        return state, "\n".join(lines)
    
    # ========== Reflog Commands ==========
    
    def cmd_reflog(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git reflog - Show reference logs."""
        if not state.reflog:
            return state, ""
        
        lines = []
        for i, entry in enumerate(reversed(state.reflog)):
            index = len(state.reflog) - 1 - i
            sha_display = entry.sha[:7] if entry.sha else ""
            lines.append(f"{entry.ref}@{{{i}}} {sha_display} {entry.action}: {entry.message}")
        
        return state, "\n".join(lines)
    
    # ========== Reset Commands ==========

    def _head_tree(self, state: GitState) -> dict:
        """Return the full snapshot at HEAD, or an empty tree."""
        sha = state.get_head_commit_sha()
        if sha and sha in state.commits:
            return dict(state.commits[sha].tree)
        return {}

    def _working_tree_snapshot(self, state: GitState) -> dict:
        """Materialize the user's current working-tree snapshot."""
        tree = self._head_tree(state)
        for filename, content in state.index.staged_content.items():
            tree[filename] = content
        for filename in state.index.staged_deletions:
            tree.pop(filename, None)
        for filename, content in state.working_tree.modified_files.items():
            tree[filename] = content
        for filename, content in state.working_tree.new_files.items():
            tree[filename] = content
        for filename in state.working_tree.deleted_files:
            tree.pop(filename, None)
        return tree

    def _delta_to_working_tree(self, base_tree: dict, target_tree: dict) -> WorkingTreeState:
        """Represent target_tree as working changes relative to base_tree."""
        modified = {
            filename: content
            for filename, content in target_tree.items()
            if filename in base_tree and base_tree[filename] != content
        }
        new_files = {
            filename: content
            for filename, content in target_tree.items()
            if filename not in base_tree
        }
        deleted = set(base_tree) - set(target_tree)
        return WorkingTreeState(
            modified_files=modified,
            new_files=new_files,
            deleted_files=deleted,
        )

    def _tree_to_index(self, base_tree: dict, target_tree: dict) -> IndexState:
        """Represent target_tree as staged changes relative to base_tree."""
        staged_content = {
            filename: content
            for filename, content in target_tree.items()
            if filename not in base_tree or base_tree[filename] != content
        }
        staged_deletions = set(base_tree) - set(target_tree)
        return IndexState(
            staged_files={name: self._hash_content(content) for name, content in staged_content.items()},
            staged_content=staged_content,
            staged_deletions=staged_deletions,
        )

    def _trees_equal(self, left: dict, right: dict) -> bool:
        return left == right

    def _replace_working_state(self, state: GitState, tree: dict) -> None:
        """Replace index/working tree with a clean checkout of tree."""
        state.index = IndexState()
        state.working_tree = WorkingTreeState()

    def cmd_reset(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git reset [--soft|--mixed|--hard] [<commit>] - Reset HEAD."""
        if not state.branches:
            raise GitCommandError("Not a git repository")
        
        if state.head_is_detached:
            raise GitCommandError("Cannot reset: HEAD is detached")
        
        # Parse args
        reset_mode = "--mixed"  # Default
        target_ref = "HEAD~1"  # Default: reset to parent
        
        for arg in args:
            if arg in ("--soft", "--mixed", "--hard"):
                reset_mode = arg
            else:
                target_ref = arg
        
        # Resolve target commit
        target_sha = self._resolve_ref(target_ref, state)
        
        if target_sha not in state.commits:
            raise GitCommandError(f"fatal: bad revision '{target_ref}'")
        
        new_state = state.copy()
        target_commit = new_state.commits[target_sha]
        old_head_tree = self._head_tree(state)
        current_working_tree = self._working_tree_snapshot(state)
        target_tree = dict(target_commit.tree)

        # Reset moves the branch ref first. The index and working tree are
        # then reconstructed from the old snapshots, matching Git's three
        # reset modes rather than merely clearing dictionaries.
        new_state.branches[new_state.head] = BranchPointer(
            name=new_state.head,
            target_sha=target_sha
        )

        if reset_mode == "--soft":
            # HEAD moves; index and working tree remain the same snapshots.
            new_state.index = self._tree_to_index(target_tree, old_head_tree)
            new_state.working_tree = self._delta_to_working_tree(
                old_head_tree, current_working_tree
            )
        elif reset_mode == "--mixed":
            # HEAD and index move to target; working files remain as-is.
            new_state.index = IndexState()
            new_state.working_tree = self._delta_to_working_tree(
                target_tree, current_working_tree
            )
        elif reset_mode == "--hard":
            new_state.index = IndexState()
            new_state.working_tree = WorkingTreeState()
        
        # Add reflog entry
        new_state.reflog.append(ReflogEntry(
            ref="HEAD",
            action="reset",
            sha=target_sha,
            message=f"reset: moving to {target_ref}"
        ))
        
        return new_state, f"HEAD is now at {target_sha[:7]} {target_commit.message}"
    
    # ========== Cherry-pick Commands ==========

    def cmd_cherry_pick(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git cherry-pick <commit>, --continue, or --abort."""
        if args and args[0] == "--abort":
            return self.cmd_cherry_pick_abort([], state)
        if args and args[0] == "--continue":
            return self.cmd_cherry_pick_continue([], state)
        if not args or len(args) != 1:
            raise GitCommandError("Usage: git cherry-pick <commit>")
        if state.merge_in_progress or state.rebase_in_progress or state.cherry_pick_in_progress:
            raise GitCommandError("Another Git operation is already in progress")
        if state.head_is_detached:
            raise GitCommandError("Cannot cherry-pick: HEAD is detached")
        if state.index.staged_files or state.index.staged_content or state.index.staged_deletions or state.working_tree.has_changes():
            raise GitCommandError("Cannot cherry-pick: working tree or index has changes")

        current_sha = state.get_head_commit_sha()
        target_sha = self._resolve_ref(args[0], state)
        if not current_sha or not target_sha:
            raise GitCommandError(f"fatal: bad revision '{args[0]}'")

        target = state.commits[target_sha]
        if len(target.parents) != 1:
            raise GitCommandError("Cherry-picking merge commits is not supported by this educational simulator")

        parent_tree = state.commits[target.parents[0]].tree
        current_tree = state.commits[current_sha].tree
        result_tree, conflicts = self._apply_commit_patch(parent_tree, target.tree, current_tree)
        new_state = state.copy()

        if conflicts:
            new_state.cherry_pick_in_progress = True
            new_state.cherry_pick_commit_sha = target_sha
            new_state.conflict_files = set(conflicts)
            modified_files = {k: v for k, v in result_tree.items() if k in current_tree and current_tree[k] != v}
            new_files = {k: v for k, v in result_tree.items() if k not in current_tree}
            deleted_files = set(current_tree) - set(result_tree)
            new_state.working_tree = WorkingTreeState(
                modified_files=modified_files,
                new_files=new_files,
                deleted_files=deleted_files,
            )
            return new_state, (
                f"Cherry-pick paused at {target_sha[:7]} ({target.message}). "
                "Resolve conflicts, run 'git add .', then 'git cherry-pick --continue'."
            )

        return self._finish_cherry_pick(new_state, target_sha, result_tree)

    def cmd_cherry_pick_continue(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git cherry-pick --continue after resolving conflicts."""
        if not state.cherry_pick_in_progress or not state.cherry_pick_commit_sha:
            raise GitCommandError("There is no cherry-pick to continue")
        if state.conflict_files:
            raise GitCommandError("Cherry-pick conflicts remain: " + ", ".join(sorted(state.conflict_files)))
        if not state.index.staged_files and not state.index.staged_deletions:
            raise GitCommandError("Stage the resolved files before continuing the cherry-pick")

        target_sha = state.cherry_pick_commit_sha
        target = state.commits.get(target_sha)
        current_sha = state.get_head_commit_sha()
        if not target or not current_sha:
            raise GitCommandError("Cannot continue cherry-pick: missing commit state")

        tree = dict(state.commits[current_sha].tree)
        for filename, content in state.index.staged_content.items():
            tree[filename] = content
        for filename in state.index.staged_deletions:
            tree.pop(filename, None)
        return self._finish_cherry_pick(state.copy(), target_sha, tree)

    def cmd_cherry_pick_abort(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git cherry-pick --abort - cancel an in-progress cherry-pick."""
        if not state.cherry_pick_in_progress:
            raise GitCommandError("There is no cherry-pick to abort")
        new_state = state.copy()
        new_state.index.staged_files.clear()
        new_state.index.staged_content.clear()
        new_state.index.staged_deletions.clear()
        new_state.working_tree = WorkingTreeState()
        new_state.conflict_files.clear()
        new_state.cherry_pick_in_progress = False
        new_state.cherry_pick_commit_sha = None
        return new_state, "Cherry-pick aborted; branch restored to its pre-cherry-pick state"

    def _finish_cherry_pick(self, state: GitState, target_sha: str, tree: dict) -> Tuple[GitState, str]:
        target = state.commits[target_sha]
        current_sha = state.get_head_commit_sha()
        if not current_sha:
            raise GitCommandError("Cannot finish cherry-pick without HEAD")
        new_sha = self._generate_sha(f"cherry-pick: {target.message}", current_sha)
        state.commits[new_sha] = Commit(
            sha=new_sha,
            message=target.message,
            parents=[current_sha],
            author=target.author,
            timestamp=int(datetime.now().timestamp()),
            tree=dict(tree),
        )
        state.branches[state.head] = BranchPointer(state.head, new_sha)
        state.index.staged_files.clear()
        state.index.staged_content.clear()
        state.index.staged_deletions.clear()
        state.working_tree = WorkingTreeState()
        state.conflict_files.clear()
        state.cherry_pick_in_progress = False
        state.cherry_pick_commit_sha = None
        state.reflog.append(ReflogEntry(ref="HEAD", action="cherry-pick", sha=new_sha, message=f"cherry-pick {target_sha[:7]}"))
        return state, f"Cherry-pick created commit {new_sha[:7]} from {target_sha[:7]}"

    # ========== Rebase Commands ==========

    def cmd_rebase(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git rebase <branch>, --continue, or --abort.

        Rebase replays the current branch's unique commits on top of the
        target branch. Original commits are retained so the visualization can
        show the old and newly-created history side by side.
        """
        if args and args[0] == "--abort":
            return self.cmd_rebase_abort([], state)
        if args and args[0] == "--continue":
            return self.cmd_rebase_continue([], state)
        if not args:
            raise GitCommandError("Usage: git rebase <branch>")
        if state.merge_in_progress:
            raise GitCommandError("Cannot rebase while a merge is in progress")
        if state.rebase_in_progress:
            raise GitCommandError("A rebase is already in progress")
        if state.head_is_detached:
            raise GitCommandError("Cannot rebase: HEAD is detached")
        if state.index.staged_files or state.index.staged_content or state.index.staged_deletions or state.working_tree.has_changes():
            raise GitCommandError("Cannot rebase: working tree or index has changes")

        onto_ref = args[0]
        if onto_ref not in state.branches:
            raise GitCommandError(f"error: branch '{onto_ref}' not found")

        current_sha = state.get_head_commit_sha()
        onto_sha = state.branches[onto_ref].target_sha
        if not current_sha or not onto_sha:
            raise GitCommandError("Cannot rebase: missing commits")
        if current_sha == onto_sha:
            return state, "Current branch is already up to date."
        if self._is_ancestor(current_sha, onto_sha, state.commits):
            new_state = state.copy()
            new_state.branches[new_state.head] = BranchPointer(new_state.head, onto_sha)
            new_state.reflog.append(ReflogEntry(ref="HEAD", action="rebase", sha=onto_sha, message=f"rebase onto {onto_ref}"))
            return new_state, "Fast-forwarded branch during rebase."

        base_sha = self._find_merge_base(current_sha, onto_sha, state.commits)
        if base_sha is None:
            raise GitCommandError("Cannot rebase: branches have no common ancestor")

        pending = self._collect_first_parent_commits(current_sha, base_sha, state.commits)
        new_state = state.copy()
        new_state.rebase_in_progress = True
        new_state.rebase_original_head = current_sha
        new_state.rebase_onto_sha = onto_sha
        new_state.rebase_pending_commits = pending
        new_state.rebase_current_commit = None
        new_state.branches[new_state.head] = BranchPointer(new_state.head, onto_sha)
        new_state.reflog.append(ReflogEntry(ref="HEAD", action="rebase", sha=onto_sha, message=f"rebase {new_state.head} onto {onto_ref}"))

        return self._replay_rebase_commits(new_state)

    def cmd_rebase_continue(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git rebase --continue after resolving and staging conflicts."""
        if not state.rebase_in_progress or not state.rebase_current_commit:
            raise GitCommandError("There is no rebase to continue")
        if state.conflict_files:
            raise GitCommandError("Rebase conflicts remain: " + ", ".join(sorted(state.conflict_files)))
        if not state.index.staged_files and not state.index.staged_deletions:
            raise GitCommandError("Stage the resolved files before continuing the rebase")

        new_state = state.copy()
        original_sha = new_state.rebase_current_commit
        original = new_state.commits.get(original_sha)
        parent_sha = new_state.get_head_commit_sha()
        if not original or not parent_sha:
            raise GitCommandError("Cannot continue rebase: missing replay state")

        tree = dict(new_state.commits[parent_sha].tree)
        for filename, content in new_state.index.staged_content.items():
            tree[filename] = content
        for filename in new_state.index.staged_deletions:
            tree.pop(filename, None)

        replay_sha = self._generate_sha(f"rebase: {original.message}", parent_sha)
        new_state.commits[replay_sha] = Commit(
            sha=replay_sha,
            message=original.message,
            parents=[parent_sha],
            author=original.author,
            timestamp=int(datetime.now().timestamp()),
            tree=tree,
        )
        new_state.branches[new_state.head] = BranchPointer(new_state.head, replay_sha)
        new_state.index.staged_files.clear()
        new_state.index.staged_content.clear()
        new_state.index.staged_deletions.clear()
        new_state.working_tree = WorkingTreeState()
        new_state.conflict_files.clear()
        new_state.rebase_current_commit = None
        if new_state.rebase_pending_commits and new_state.rebase_pending_commits[0] == original_sha:
            new_state.rebase_pending_commits.pop(0)
        return self._replay_rebase_commits(new_state)

    def cmd_rebase_abort(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git rebase --abort - restore the branch to its pre-rebase tip."""
        if not state.rebase_in_progress or not state.rebase_original_head:
            raise GitCommandError("There is no rebase to abort")
        new_state = state.copy()
        new_state.branches[new_state.head] = BranchPointer(new_state.head, new_state.rebase_original_head)
        new_state.index.staged_files.clear()
        new_state.index.staged_content.clear()
        new_state.index.staged_deletions.clear()
        new_state.working_tree = WorkingTreeState()
        new_state.conflict_files.clear()
        new_state.rebase_in_progress = False
        new_state.rebase_original_head = None
        new_state.rebase_onto_sha = None
        new_state.rebase_pending_commits.clear()
        new_state.rebase_current_commit = None
        new_state.reflog.append(ReflogEntry(ref="HEAD", action="rebase-abort", sha=new_state.branches[new_state.head].target_sha or "", message="rebase --abort"))
        return new_state, "Rebase aborted; branch restored to its original tip"

    def _replay_rebase_commits(self, state: GitState) -> Tuple[GitState, str]:
        """Replay pending commits until completion or the first conflict."""
        new_state = state.copy()
        replayed = []
        while new_state.rebase_pending_commits:
            original_sha = new_state.rebase_pending_commits[0]
            original = new_state.commits[original_sha]
            original_parent = original.parents[0] if original.parents else None
            current_sha = new_state.get_head_commit_sha()
            if not current_sha:
                raise GitCommandError("Cannot replay commit without a current base")

            if original_parent is None:
                base_tree = {}
            else:
                base_tree = new_state.commits[original_parent].tree
            # Compare the original commit against its original parent and apply
            # that patch to the newly-rebased parent.
            merged_tree, conflicts = self._apply_commit_patch(
                base_tree, original.tree, new_state.commits[current_sha].tree
            )
            if conflicts:
                new_state.rebase_current_commit = original_sha
                new_state.conflict_files = set(conflicts)
                current_tree = new_state.commits[current_sha].tree
                new_files = {
                    k: v for k, v in merged_tree.items()
                    if k not in current_tree
                }
                modified_files = {
                    k: v for k, v in merged_tree.items()
                    if k in current_tree and current_tree[k] != v
                }
                deleted_files = set(current_tree) - set(merged_tree)
                new_state.working_tree = WorkingTreeState(
                    modified_files=modified_files,
                    new_files=new_files,
                    deleted_files=deleted_files,
                )
                return new_state, (
                    f"Rebase paused at {original_sha[:7]} ({original.message}). "
                    "Resolve conflicts, run 'git add .', then 'git rebase --continue'."
                )

            replay_sha = self._generate_sha(f"rebase: {original.message}", current_sha)
            new_state.commits[replay_sha] = Commit(
                sha=replay_sha,
                message=original.message,
                parents=[current_sha],
                author=original.author,
                timestamp=int(datetime.now().timestamp()),
                tree=merged_tree,
            )
            new_state.branches[new_state.head] = BranchPointer(new_state.head, replay_sha)
            new_state.rebase_pending_commits.pop(0)
            replayed.append(f"{original_sha[:7]} -> {replay_sha[:7]}")

        new_state.rebase_in_progress = False
        new_state.rebase_original_head = None
        new_state.rebase_onto_sha = None
        new_state.rebase_current_commit = None
        new_state.conflict_files.clear()
        new_state.reflog.append(ReflogEntry(ref="HEAD", action="rebase", sha=new_state.get_head_commit_sha() or "", message="rebase finished"))
        detail = ", ".join(replayed) if replayed else "no commits to replay"
        return new_state, f"Rebase finished: {detail}"

    def _collect_first_parent_commits(self, tip_sha: str, base_sha: str, commits: dict) -> List[str]:
        """Return first-parent commits from base-exclusive to tip, oldest first."""
        result = []
        current = tip_sha
        while current and current != base_sha:
            result.append(current)
            commit = commits.get(current)
            if not commit or not commit.parents:
                break
            current = commit.parents[0]
        if current != base_sha:
            raise GitCommandError("Cannot determine linear rebase sequence")
        result.reverse()
        return result

    def _apply_commit_patch(self, base_tree: dict, original_tree: dict, new_base_tree: dict) -> Tuple[dict, List[str]]:
        """Apply one commit's tree delta to a new base using three-way rules."""
        missing = object()
        result = dict(new_base_tree)
        conflicts = []
        for filename in set(base_tree) | set(original_tree) | set(new_base_tree):
            base_value = base_tree.get(filename, missing)
            original_value = original_tree.get(filename, missing)
            current_value = new_base_tree.get(filename, missing)
            if original_value == base_value:
                merged = current_value
            elif current_value == base_value or current_value == original_value:
                merged = original_value
            else:
                current_text = "" if current_value is missing else current_value
                original_text = "" if original_value is missing else original_value
                merged = (
                    "<<<<<<< rebased-base\\n" + current_text +
                    "\\n=======\\n" + original_text +
                    "\\n>>>>>>> replayed-commit"
                )
                conflicts.append(filename)
            if merged is missing:
                result.pop(filename, None)
            else:
                result[filename] = merged
        return result, conflicts

    # ========== Merge Commands ==========

    def cmd_merge_abort(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git merge --abort - cancel an in-progress merge."""
        if not state.merge_in_progress:
            raise GitCommandError("There is no merge to abort")
        new_state = state.copy()
        new_state.working_tree = WorkingTreeState()
        new_state.index.staged_files.clear()
        new_state.index.staged_content.clear()
        new_state.index.staged_deletions.clear()
        new_state.merge_in_progress = False
        new_state.merge_head_sha = None
        new_state.conflict_files.clear()
        return new_state, "Merge aborted; working tree restored to HEAD"

    def cmd_merge_continue(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git merge --continue - finish a conflict-resolved merge."""
        if not state.merge_in_progress or not state.merge_head_sha:
            raise GitCommandError("There is no merge to continue")
        if state.conflict_files:
            raise GitCommandError("Merge conflicts remain: " + ", ".join(sorted(state.conflict_files)))
        if not state.index.staged_files and not state.index.staged_deletions:
            raise GitCommandError("Stage the resolved files before continuing the merge")

        current_sha = state.get_head_commit_sha()
        merge_sha = state.merge_head_sha
        if not current_sha or merge_sha not in state.commits:
            raise GitCommandError("Cannot continue merge: missing merge heads")

        new_state = state.copy()
        tree = dict(new_state.commits[current_sha].tree)
        for filename, content in new_state.index.staged_content.items():
            tree[filename] = content
        for filename in new_state.index.staged_deletions:
            tree.pop(filename, None)

        merge_sha_new = self._generate_sha("merge --continue", current_sha)
        commit = Commit(
            sha=merge_sha_new,
            message=f"Merge branch into {new_state.head}",
            parents=[current_sha, merge_sha],
            author="Git Learner",
            timestamp=int(datetime.now().timestamp()),
            tree=tree,
        )
        new_state.commits[merge_sha_new] = commit
        new_state.branches[new_state.head] = BranchPointer(new_state.head, merge_sha_new)
        new_state.index.staged_files.clear()
        new_state.index.staged_content.clear()
        new_state.index.staged_deletions.clear()
        new_state.working_tree = WorkingTreeState()
        new_state.merge_in_progress = False
        new_state.merge_head_sha = None
        new_state.conflict_files.clear()
        new_state.reflog.append(ReflogEntry(ref="HEAD", action="merge", sha=merge_sha_new, message="merge --continue"))
        return new_state, f"Merge committed as {merge_sha_new[:7]}"

    def cmd_merge(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git merge <branch>, --continue, or --abort."""
        if args and args[0] == "--abort":
            return self.cmd_merge_abort([], state)
        if args and args[0] == "--continue":
            return self.cmd_merge_continue([], state)
        if not args:
            raise GitCommandError("Usage: git merge <branch>")
        
        if state.head_is_detached:
            raise GitCommandError("Cannot merge: HEAD is detached")
        
        merge_branch = args[0]
        
        if merge_branch not in state.branches:
            raise GitCommandError(f"error: branch '{merge_branch}' not found")
        
        if merge_branch == state.head:
            raise GitCommandError("Already up to date")
        
        new_state = state.copy()
        
        # Get current and merge branch commits
        current_sha = new_state.get_head_commit_sha()
        merge_sha = new_state.branches[merge_branch].target_sha
        
        if not current_sha or not merge_sha:
            raise GitCommandError("Cannot merge: missing commits")
        
        # Check if fast-forward is possible
        if self._is_ancestor(current_sha, merge_sha, new_state.commits):
            # Fast-forward merge
            new_state.branches[new_state.head] = BranchPointer(
                name=new_state.head,
                target_sha=merge_sha
            )
            
            merge_commit = new_state.commits[merge_sha]
            
            new_state.reflog.append(ReflogEntry(
                ref="HEAD",
                action="merge",
                sha=merge_sha,
                message=f"merge {merge_branch}"
            ))
            
            return new_state, f"Fast-forward merge of {merge_branch}"
        
        else:
            # Create merge commit
            merge_sha_new = self._generate_sha(
                f"Merge branch '{merge_branch}'",
                current_sha
            )
            
            merged_tree, conflicts = self._merge_trees(current_sha, merge_sha, new_state)

            if conflicts:
                new_state.merge_in_progress = True
                new_state.merge_head_sha = merge_sha
                new_state.conflict_files = set(conflicts)
                for filename in conflicts:
                    new_state.working_tree.modified_files[filename] = merged_tree[filename]
                return new_state, (
                    "Automatic merge failed; resolve conflicts, run 'git add .', "
                    "'git merge --continue'. Conflicts: " + ", ".join(sorted(conflicts))
                )

            merge_commit = Commit(
                sha=merge_sha_new,
                message=f"Merge branch '{merge_branch}' into {new_state.head}",
                parents=[current_sha, merge_sha],
                author="Git Learner",
                timestamp=int(datetime.now().timestamp()),
                tree=merged_tree,
            )
            
            new_state.commits[merge_sha_new] = merge_commit
            new_state.branches[new_state.head] = BranchPointer(
                name=new_state.head,
                target_sha=merge_sha_new
            )
            
            new_state.reflog.append(ReflogEntry(
                ref="HEAD",
                action="merge",
                sha=merge_sha_new,
                message=f"merge {merge_branch}"
            ))
            
            return new_state, f"Merge made by the 'recursive' strategy."
    
    # ========== Helper Methods ==========
    

    def _merge_trees(self, current_sha: str, merge_sha: str, state: GitState) -> Tuple[dict, List[str]]:
        """Perform a simplified three-way merge using the common ancestor.

        For each path:
        - if both sides agree, keep that content;
        - if only the current side changed from the base, keep current;
        - if only the incoming side changed from the base, take incoming;
        - if both changed differently, keep conflict markers.

        Missing paths are treated as deleted files. This is intentionally a
        compact educational model rather than a byte-for-byte Git merge.
        """
        base_sha = self._find_merge_base(current_sha, merge_sha, state.commits)
        base = dict(state.commits[base_sha].tree) if base_sha else {}
        current = dict(state.commits[current_sha].tree)
        incoming = dict(state.commits[merge_sha].tree)

        missing = object()
        result = {}
        conflicts = []
        for filename in set(base) | set(current) | set(incoming):
            base_value = base.get(filename, missing)
            current_value = current.get(filename, missing)
            incoming_value = incoming.get(filename, missing)

            if current_value == incoming_value:
                merged = current_value
            elif current_value == base_value:
                merged = incoming_value
            elif incoming_value == base_value:
                merged = current_value
            else:
                current_text = "" if current_value is missing else current_value
                incoming_text = "" if incoming_value is missing else incoming_value
                merged = (
                    "<<<<<<< current\\n" + current_text +
                    "\\n=======\\n" + incoming_text +
                    "\\n>>>>>>> incoming"
                )

            if merged is not missing:
                result[filename] = merged

        return result

    def _find_merge_base(self, first_sha: str, second_sha: str, commits: dict) -> Optional[str]:
        """Find a nearest common ancestor for two commits."""
        first_distances = self._ancestor_distances(first_sha, commits)
        second_distances = self._ancestor_distances(second_sha, commits)
        common = set(first_distances) & set(second_distances)
        if not common:
            return None

        return min(
            common,
            key=lambda sha: (
                first_distances[sha] + second_distances[sha],
                first_distances[sha],
                sha,
            ),
        )

    def _ancestor_distances(self, start_sha: str, commits: dict) -> dict:
        """Return minimum parent distance for every reachable ancestor."""
        distances = {start_sha: 0}
        queue = [start_sha]
        while queue:
            sha = queue.pop(0)
            distance = distances[sha]
            commit = commits.get(sha)
            if not commit:
                continue
            for parent_sha in commit.parents:
                if parent_sha not in distances or distance + 1 < distances[parent_sha]:
                    distances[parent_sha] = distance + 1
                    queue.append(parent_sha)
        return distances

    def _generate_sha(self, message: str, parent_sha: Optional[str]) -> str:
        """Generate deterministic SHA for a commit."""
        self._sha_counter += 1
        content = f"{message}:{parent_sha or 'root'}:{self._sha_counter}"
        hash_obj = hashlib.sha1(content.encode())
        return hash_obj.hexdigest()
    
    def _hash_content(self, content: str) -> str:
        """Generate hash for file content."""
        return hashlib.sha1(content.encode()).hexdigest()[:7]
    
    def _resolve_ref(self, ref: str, state: GitState) -> Optional[str]:
        """Resolve a reference to a commit SHA."""
        # Handle HEAD~1, HEAD~2, etc.
        if ref.startswith("HEAD"):
            current_sha = state.get_head_commit_sha()
            
            if "~" in ref:
                depth = int(ref.split("~")[1])
                for _ in range(depth):
                    if not current_sha or current_sha not in state.commits:
                        return None
                    commit = state.commits[current_sha]
                    if commit.parents:
                        current_sha = commit.parents[0]
                    else:
                        return None
                return current_sha
            
            return current_sha
        
        # Handle branch names
        if ref in state.branches:
            return state.branches[ref].target_sha

        # Handle tag names
        if ref in state.tags:
            return state.tags[ref].target_sha

        # Handle commit SHAs
        if ref in state.commits:
            return ref
        
        return None
    
    def _is_ancestor(self, ancestor_sha: str, descendant_sha: str, commits: dict) -> bool:
        """Check if ancestor_sha is an ancestor of descendant_sha."""
        visited = set()
        
        def walk(sha: str) -> bool:
            if not sha or sha in visited:
                return False
            visited.add(sha)
            
            if sha == ancestor_sha:
                return True
            
            if sha not in commits:
                return False
            
            commit = commits[sha]
            for parent_sha in commit.parents:
                if walk(parent_sha):
                    return True
            
            return False
        
        return walk(descendant_sha)
