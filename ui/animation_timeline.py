"""Semantic command-to-state timeline helpers for Git visualization."""

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from git_simulator.state import GitState


@dataclass(frozen=True)
class TimelineEvent:
    step: int
    command: str
    summary: str
    head_before: Optional[str]
    head_after: Optional[str]
    branch_before: Optional[str]
    branch_after: Optional[str]
    commits_before: int
    commits_after: int
    working_changes_before: int
    working_changes_after: int
    staged_before: int
    staged_after: int


def _working_changes(state: GitState) -> int:
    wt = state.working_tree
    return len(wt.modified_files) + len(wt.new_files) + len(wt.deleted_files)


def _staged_changes(state: GitState) -> int:
    return len(state.index.staged_files) + len(state.index.staged_deletions)


def summarize_transition(command: str, before: GitState, after: GitState) -> str:
    """Turn a raw state transition into a learner-friendly explanation."""
    if command.startswith("git commit"):
        return f"Created a commit; HEAD moved from {(before.get_head_commit_sha() or 'None')[:7]} to {(after.get_head_commit_sha() or 'None')[:7]}."
    if command.startswith("git switch") or command.startswith("git checkout"):
        return f"HEAD moved from {before.head} to {after.head}."
    if command.startswith("git reset"):
        return f"Branch {after.head} moved from {(before.get_head_commit_sha() or 'None')[:7]} to {(after.get_head_commit_sha() or 'None')[:7]}; reflog preserved the old position."
    if command.startswith("git merge"):
        if after.get_head_commit_sha() != before.get_head_commit_sha():
            return "Merge changed the current branch history."
        return "Merge started or changed merge state without moving HEAD."
    if command.startswith("git stash"):
        return f"Stash operation changed saved work from {len(before.stashes)} to {len(after.stashes)} entries."
    if command.startswith("git add"):
        return f"Staging area changed from {_staged_changes(before)} to {_staged_changes(after)} staged paths."
    if command.startswith("git restore"):
        return f"Working-tree changes changed from {_working_changes(before)} to {_working_changes(after)}."
    if command.startswith("git branch") or command.startswith("git tag"):
        return "References changed while commit history stayed in place."
    if command.startswith("git fetch") or command.startswith("git pull") or command.startswith("git push"):
        return "Remote or remote-tracking references changed."
    if command.startswith("git rebase"):
        return "Rebase replayed or prepared commits against a new base."
    if command.startswith("git cherry-pick"):
        return "A commit change was applied to the current branch."
    return f"Repository state changed: {len(before.commits)} → {len(after.commits)} commits."


def build_timeline(history: List[tuple]) -> List[TimelineEvent]:
    """Build semantic events from GitRepository history."""
    events: List[TimelineEvent] = []
    previous: Optional[GitState] = None
    for step, (command, state) in enumerate(history, start=1):
        before = previous or GitState()
        events.append(
            TimelineEvent(
                step=step,
                command=command,
                summary=summarize_transition(command, before, state),
                head_before=before.get_head_commit_sha(),
                head_after=state.get_head_commit_sha(),
                branch_before=None if before.head_is_detached else before.head,
                branch_after=None if state.head_is_detached else state.head,
                commits_before=len(before.commits),
                commits_after=len(state.commits),
                working_changes_before=_working_changes(before),
                working_changes_after=_working_changes(state),
                staged_before=_staged_changes(before),
                staged_after=_staged_changes(state),
            )
        )
        previous = state
    return events



def state_at_step(history: Sequence[Tuple[str, GitState]], step: int) -> GitState:
    """Return a copied historical state; step 0 is the initial empty state."""
    if step < 0 or step > len(history):
        raise ValueError(f"step must be between 0 and {len(history)}")
    if step == 0:
        return GitState()
    return history[step - 1][1].copy()


def state_diff(before: GitState, after: GitState) -> dict:
    """Summarize visible repository changes between two timeline states."""
    before_head = before.get_head_commit_sha()
    after_head = after.get_head_commit_sha()
    before_tree = before.commits[before_head].tree if before_head in before.commits else {}
    after_tree = after.commits[after_head].tree if after_head in after.commits else {}
    return {
        "commits_added": len(set(after.commits) - set(before.commits)),
        "commits_removed": len(set(before.commits) - set(after.commits)),
        "branches_added": sorted(set(after.branches) - set(before.branches)),
        "branches_removed": sorted(set(before.branches) - set(after.branches)),
        "tags_added": sorted(set(after.tags) - set(before.tags)),
        "tags_removed": sorted(set(before.tags) - set(after.tags)),
        "files_added": sorted(set(after_tree) - set(before_tree)),
        "files_removed": sorted(set(before_tree) - set(after_tree)),
        "working_changes_delta": _working_changes(after) - _working_changes(before),
        "staged_delta": _staged_changes(after) - _staged_changes(before),
    }
