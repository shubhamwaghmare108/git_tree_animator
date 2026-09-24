"""
Immutable state models for Git repository simulation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import datetime
from copy import deepcopy


@dataclass(frozen=True)
class Commit:
    """Immutable commit object."""
    
    sha: str                          # Full SHA (7 chars for display)
    message: str
    parents: List[str] = field(default_factory=list)  # Parent commit SHAs
    author: str = "Git Learner"
    timestamp: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    
    @property
    def short_sha(self) -> str:
        """Return short SHA for display."""
        return self.sha[:7]
    
    def __str__(self) -> str:
        return f"{self.short_sha} {self.message}"
    
    def __repr__(self) -> str:
        return f"Commit(sha={self.sha[:7]}, message='{self.message}')"


@dataclass(frozen=True)
class BranchPointer:
    """Immutable branch reference."""
    
    name: str
    target_sha: Optional[str] = None  # Points to a commit SHA
    
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return f"Branch({self.name} -> {self.target_sha[:7] if self.target_sha else 'None'})"


@dataclass
class IndexState:
    """Staging area (index) state."""
    
    staged_files: Dict[str, str] = field(default_factory=dict)  # filename -> hash
    
    def __repr__(self) -> str:
        return f"Index({len(self.staged_files)} files)"


@dataclass
class WorkingTreeState:
    """Working directory state."""
    
    modified_files: Dict[str, str] = field(default_factory=dict)  # filename -> content
    new_files: Dict[str, str] = field(default_factory=dict)       # filename -> content
    deleted_files: Set[str] = field(default_factory=set)          # filename set
    
    def has_changes(self) -> bool:
        """Check if working tree has any changes."""
        return bool(self.modified_files or self.new_files or self.deleted_files)
    
    def __repr__(self) -> str:
        changes = len(self.modified_files) + len(self.new_files) + len(self.deleted_files)
        return f"WorkingTree({changes} changes)"


@dataclass(frozen=True)
class ReflogEntry:
    """Single reflog entry."""
    
    ref: str                          # "HEAD", "main", etc.
    action: str                       # "commit", "reset", "switch", "checkout", etc.
    sha: str                          # Target SHA (None for branch creation)
    message: str                      # Human-readable message
    timestamp: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    
    def __str__(self) -> str:
        return f"{self.ref}: {self.action} {self.message}"
    
    def __repr__(self) -> str:
        return f"ReflogEntry({self.ref}, {self.action})"


@dataclass
class GitState:
    """Complete, immutable snapshot of repository state."""
    
    commits: Dict[str, Commit] = field(default_factory=dict)  # sha -> Commit
    branches: Dict[str, BranchPointer] = field(default_factory=dict)  # name -> BranchPointer
    head: str = "main"                # Current branch name or detached commit SHA
    head_is_detached: bool = False    # True if HEAD points to commit directly
    
    index: IndexState = field(default_factory=IndexState)
    working_tree: WorkingTreeState = field(default_factory=WorkingTreeState)
    
    remotes: Dict[str, Dict[str, BranchPointer]] = field(default_factory=dict)  # origin -> {branch_name -> BranchPointer}
    reflog: List[ReflogEntry] = field(default_factory=list)
    
    timestamp: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    
    def copy(self) -> "GitState":
        """Create a deep copy of state."""
        return GitState(
            commits=deepcopy(self.commits),
            branches=deepcopy(self.branches),
            head=self.head,
            head_is_detached=self.head_is_detached,
            index=IndexState(staged_files=self.index.staged_files.copy()),
            working_tree=WorkingTreeState(
                modified_files=self.working_tree.modified_files.copy(),
                new_files=self.working_tree.new_files.copy(),
                deleted_files=self.working_tree.deleted_files.copy(),
            ),
            remotes=deepcopy(self.remotes),
            reflog=list(self.reflog),
            timestamp=int(datetime.now().timestamp()),
        )
    
    def get_head_commit_sha(self) -> Optional[str]:
        """Get SHA of commit pointed to by HEAD."""
        if self.head_is_detached:
            return self.head  # HEAD points directly to a commit
        
        if self.head in self.branches:
            return self.branches[self.head].target_sha
        
        return None
    
    def __repr__(self) -> str:
        return f"GitState(commits={len(self.commits)}, branches={len(self.branches)}, head={self.head})"
