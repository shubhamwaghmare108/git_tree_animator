"""Custom exceptions for Git simulator."""


class GitError(Exception):
    """Base exception for Git operations."""
    pass


class GitCommandError(GitError):
    """Error executing a Git command."""
    pass


class GitRepositoryError(GitError):
    """Error in repository state."""
    pass


class GitMergeConflictError(GitError):
    """Merge conflict detected."""
    pass


class GitRefNotFoundError(GitError):
    """Reference (branch/commit) not found."""
    pass
