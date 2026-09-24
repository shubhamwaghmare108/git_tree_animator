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
    # Simplified committed tree: filename -> file content. This makes commits
    # actual snapshots instead of metadata-only graph nodes.
    tree: Dict[str, str] = field(default_factory=dict)
    
    @property
    def short_sha(self) -> str:
        """Return short SHA for display."""
        return self.sha[:7]
    
    def __str__(self) -> str:
        return f"{self.short_sha} {self.message}"
    
    def __repr__(self) -> str:
        return f"Commit(sha={self.sha[:7]}, message='{self.message}')"


@dataclass(frozen=True)
class TagPointer:
    """Immutable tag reference pointing at a commit."""

    name: str
    target_sha: str
    message: Optional[str] = None
    annotated: bool = False

    def __str__(self) -> str:
        return self.name


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
    """Staging area (index) state.

    ``staged_files`` keeps the content hash for compact display, while
    ``staged_content`` preserves the actual content needed to build a commit tree.
    """
    
    staged_files: Dict[str, str] = field(default_factory=dict)  # filename -> hash
    staged_content: Dict[str, str] = field(default_factory=dict)  # filename -> content
    staged_deletions: Set[str] = field(default_factory=set)  # filenames removed from the tree
    
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
class StashEntry:
    """Saved working-tree and index snapshot used by the stash workflow."""

    stash_id: int
    message: str
    base_sha: Optional[str]
    modified_files: Dict[str, str] = field(default_factory=dict)
    new_files: Dict[str, str] = field(default_factory=dict)
    deleted_files: Set[str] = field(default_factory=set)
    staged_content: Dict[str, str] = field(default_factory=dict)
    staged_deletions: Set[str] = field(default_factory=set)

    @property
    def name(self) -> str:
        return f"stash@{{{self.stash_id}}}"


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
    """Complete repository snapshot at a point in the simulator history."""
    
    commits: Dict[str, Commit] = field(default_factory=dict)  # sha -> Commit
    branches: Dict[str, BranchPointer] = field(default_factory=dict)  # name -> BranchPointer
    tags: Dict[str, TagPointer] = field(default_factory=dict)  # name -> TagPointer
    head: str = "main"                # Current branch name or detached commit SHA
    head_is_detached: bool = False    # True if HEAD points to commit directly
    
    index: IndexState = field(default_factory=IndexState)
    working_tree: WorkingTreeState = field(default_factory=WorkingTreeState)
    
    # Local remote-tracking refs: origin -> {branch_name -> BranchPointer}
    remotes: Dict[str, Dict[str, BranchPointer]] = field(default_factory=dict)
    # Simulated remote servers: remote -> {branch_name -> BranchPointer}.
    # The simulator keeps these refs in the same object database for teaching purposes.
    remote_servers: Dict[str, Dict[str, BranchPointer]] = field(default_factory=dict)
    remote_urls: Dict[str, str] = field(default_factory=dict)
    stashes: List["StashEntry"] = field(default_factory=list)
    reflog: List[ReflogEntry] = field(default_factory=list)
    
    timestamp: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    merge_in_progress: bool = False
    merge_head_sha: Optional[str] = None
    conflict_files: Set[str] = field(default_factory=set)
    # Rebase workflow state. Original commits remain in the object database;
    # these fields describe the temporary replay operation.
    rebase_in_progress: bool = False
    rebase_original_head: Optional[str] = None
    rebase_onto_sha: Optional[str] = None
    rebase_pending_commits: List[str] = field(default_factory=list)
    rebase_current_commit: Optional[str] = None
    cherry_pick_in_progress: bool = False
    cherry_pick_commit_sha: Optional[str] = None
    # Snapshot of local changes before an operation that can be aborted.
    operation_original_index: Optional[IndexState] = None
    operation_original_working_tree: Optional[WorkingTreeState] = None
    
    def copy(self) -> "GitState":
        """Create a deep copy of state."""
        return GitState(
            commits=deepcopy(self.commits),
            branches=deepcopy(self.branches),
            tags=deepcopy(self.tags),
            head=self.head,
            head_is_detached=self.head_is_detached,
            index=IndexState(
                staged_files=self.index.staged_files.copy(),
                staged_content=self.index.staged_content.copy(),
                staged_deletions=self.index.staged_deletions.copy(),
            ),
            working_tree=WorkingTreeState(
                modified_files=self.working_tree.modified_files.copy(),
                new_files=self.working_tree.new_files.copy(),
                deleted_files=self.working_tree.deleted_files.copy(),
            ),
            remotes=deepcopy(self.remotes),
            remote_servers=deepcopy(self.remote_servers),
            remote_urls=self.remote_urls.copy(),
            stashes=deepcopy(self.stashes),
            reflog=list(self.reflog),
            timestamp=int(datetime.now().timestamp()),
            merge_in_progress=self.merge_in_progress,
            merge_head_sha=self.merge_head_sha,
            conflict_files=self.conflict_files.copy(),
            rebase_in_progress=self.rebase_in_progress,
            rebase_original_head=self.rebase_original_head,
            rebase_onto_sha=self.rebase_onto_sha,
            rebase_pending_commits=self.rebase_pending_commits.copy(),
            rebase_current_commit=self.rebase_current_commit,
            cherry_pick_in_progress=self.cherry_pick_in_progress,
            cherry_pick_commit_sha=self.cherry_pick_commit_sha,
            operation_original_index=deepcopy(self.operation_original_index),
            operation_original_working_tree=deepcopy(self.operation_original_working_tree),
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
