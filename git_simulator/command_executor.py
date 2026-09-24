"""
Git command parser and executor.
Simulates the effect of Git commands on repository state.
"""

import hashlib
import shlex
from typing import List, Optional, Tuple
from datetime import datetime

from .state import GitState, Commit, BranchPointer, ReflogEntry, WorkingTreeState
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
        
        # Stage all modified and new files
        for filename, content in new_state.working_tree.modified_files.items():
            new_state.index.staged_files[filename] = self._hash_content(content)
            new_state.index.staged_content[filename] = content
        
        for filename, content in new_state.working_tree.new_files.items():
            new_state.index.staged_files[filename] = self._hash_content(content)
            new_state.index.staged_content[filename] = content
        
        staged_count = len(new_state.index.staged_files)
        
        # Simulate: working tree is updated (files added to index)
        # In real git, this would be tracked per file
        
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
        
        # Clear only the changes that were actually committed.
        for filename in list(new_state.index.staged_content):
            new_state.working_tree.modified_files.pop(filename, None)
            new_state.working_tree.new_files.pop(filename, None)
            new_state.working_tree.deleted_files.discard(filename)
        new_state.index.staged_files.clear()
        new_state.index.staged_content.clear()
        
        # Add reflog entry
        new_state.reflog.append(ReflogEntry(
            ref="HEAD",
            action="commit",
            sha=new_sha,
            message=message
        ))
        
        return new_state, f"[{new_state.head} {new_sha[:7]}] {message}"
    
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
        
        # Get the commit being reset to
        target_commit = new_state.commits[target_sha]
        
        # Move branch pointer
        new_state.branches[new_state.head] = BranchPointer(
            name=new_state.head,
            target_sha=target_sha
        )
        
        if reset_mode == "--soft":
            # Keep staged and working tree changes
            pass
        
        elif reset_mode == "--mixed":
            # Move changes to working tree
            new_state.index.staged_files.clear()
            new_state.index.staged_content.clear()
        
        elif reset_mode == "--hard":
            # Discard all changes
            new_state.index.staged_files.clear()
            new_state.index.staged_content.clear()
            new_state.working_tree = WorkingTreeState()
        
        # Add reflog entry
        new_state.reflog.append(ReflogEntry(
            ref="HEAD",
            action="reset",
            sha=target_sha,
            message=f"reset: moving to {target_ref}"
        ))
        
        return new_state, f"HEAD is now at {target_sha[:7]} {target_commit.message}"
    
    # ========== Merge Commands ==========
    
    def cmd_merge(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
        """git merge <branch> - Merge a branch."""
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
            
            merge_commit = Commit(
                sha=merge_sha_new,
                message=f"Merge branch '{merge_branch}' into {new_state.head}",
                parents=[current_sha, merge_sha],
                author="Git Learner",
                timestamp=int(datetime.now().timestamp()),
                tree=self._merge_trees(current_sha, merge_sha, new_state),
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
    

    def _merge_trees(self, current_sha: str, merge_sha: str, state: GitState) -> dict:
        """Create a deterministic educational merge tree.

        Non-conflicting files from the merge side are applied over the current
        tree. Conflicting files get visible conflict markers.
        """
        current = dict(state.commits[current_sha].tree)
        incoming = dict(state.commits[merge_sha].tree)
        result = dict(current)
        for filename, content in incoming.items():
            if filename not in current or current[filename] == content:
                result[filename] = content
            else:
                result[filename] = (
                    "<<<<<<< current\n" + current[filename] +
                    "\n=======\n" + content +
                    "\n>>>>>>> " + state.head
                )
        return result

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
