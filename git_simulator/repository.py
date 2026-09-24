"""
Main Git repository simulator.
Maintains history and state of Git operations.
"""

from typing import List, Tuple, Optional
from .state import GitState
from .command_executor import GitCommandExecutor
from .errors import GitError


class GitRepository:
    """Simulates a Git repository."""
    
    def __init__(self):
        self.state = GitState()
        self.executor = GitCommandExecutor()
        self.history: List[Tuple[str, GitState]] = []  # (command, resulting_state)
    
    def execute_command(self, command: str) -> Tuple[bool, str, GitState]:
        """
        Execute a git command.
        
        Args:
            command: Git command (e.g., "git commit -m 'message'")
        
        Returns:
            (success: bool, message: str, new_state: GitState)
        """
        command = command.strip()
        
        if not command.startswith("git "):
            return False, "error: command must start with 'git'", self.state
        
        try:
            new_state, output = self.executor.execute(command, self.state)
            self.state = new_state
            self.history.append((command, new_state))
            return True, output, new_state
        except GitError as e:
            return False, f"error: {str(e)}", self.state
        except Exception as e:
            return False, f"fatal: {str(e)}", self.state
    
    def reset_to_step(self, step_index: int) -> bool:
        """
        Reset to a previous command in history.
        
        Args:
            step_index: Index in history to reset to
        
        Returns:
            Success boolean
        """
        if 0 <= step_index < len(self.history):
            _, self.state = self.history[step_index]
            # Trim history to this point
            self.history = self.history[:step_index + 1]
            return True
        return False
    
    def get_commit_graph_data(self) -> dict:
        """
        Return data for rendering the commit graph.
        
        Returns:
            dict with commits, branches, HEAD info
        """
        return {
            "commits": self.state.commits,
            "branches": self.state.branches,
            "head": self.state.head,
            "head_is_detached": self.state.head_is_detached,
        }
    
    def clear(self):
        """Reset repository to initial state."""
        self.state = GitState()
        self.executor = GitCommandExecutor()
        self.history = []
    
    def get_current_branch(self) -> str:
        """Get the name of the current branch."""
        return self.state.head
    
    def is_head_detached(self) -> bool:
        """Check if HEAD is detached."""
        return self.state.head_is_detached
    
    def get_all_commits(self) -> dict:
        """Get all commits in the repository."""
        return self.state.commits
    
    def get_all_branches(self) -> dict:
        """Get all branches in the repository."""
        return self.state.branches
