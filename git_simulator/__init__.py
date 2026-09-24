"""
Git Tree Animator - Git Simulation Engine

A pure Python Git repository simulator for educational visualization.
"""

from .repository import GitRepository
from .state import GitState, Commit, BranchPointer, ReflogEntry, IndexState, WorkingTreeState
from .command_executor import GitCommandExecutor
from .errors import GitError, GitCommandError, GitRepositoryError, GitMergeConflictError, GitRefNotFoundError

__version__ = "0.1.0"
__all__ = [
    "GitRepository",
    "GitState",
    "Commit",
    "BranchPointer",
    "ReflogEntry",
    "IndexState",
    "WorkingTreeState",
    "GitCommandExecutor",
    "GitError",
    "GitCommandError",
    "GitRepositoryError",
    "GitMergeConflictError",
    "GitRefNotFoundError",
]
