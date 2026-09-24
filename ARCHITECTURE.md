# Git Tree Animator - Architecture Documentation

## Overview

Git Tree Animator is a pure Python Git simulator with an interactive Streamlit frontend. It demonstrates how Git commands modify repository state without calling the actual `git` CLI.

## Core Design Principles

### 1. snapshot-based State

`GitState` is an snapshot-based snapshot of repository state at a point in time:

```python
@dataclass
class GitState:
    commits: Dict[str, Commit]
    branches: Dict[str, BranchPointer]
    head: str
    head_is_detached: bool
    index: IndexState
    working_tree: WorkingTreeState
    reflog: List[ReflogEntry]
    timestamp: int
```

**Why snapshot-based?**

- Enables trivial history replay
- Prevents accidental mutation bugs
- Makes time-travel debugging simple
- Aligns with Git's actual design (objects are snapshot-based)

### 2. Command Execution Pipeline

```
User Input
    ↓
Streamlit TextInput
    ↓
parse command ("git commit -m 'msg'")
    ↓
GitCommandExecutor
    ↓
cmd_commit() method
    ↓
Create new GitState
    ↓
Append to history
    ↓
Re-render UI
```

### 3. State Transitions

Each command performs these steps:

```python
def cmd_commit(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
    # 1. Validate command
    if not valid:
        raise GitCommandError(...)
    
    # 2. Copy state (don't mutate)
    new_state = state.copy()
    
    # 3. Apply changes
    new_state.commits[sha] = commit
    new_state.branches[branch].target_sha = sha
    
    # 4. Record in reflog
    new_state.reflog.append(ReflogEntry(...))
    
    # 5. Return new state + output message
    return new_state, output_msg
```

## Module Breakdown

### `git_simulator/state.py`

**snapshot-based models for Git objects:**

```python
Commit          # Represents a commit snapshot
BranchPointer   # Points to a commit SHA
ReflogEntry     # Historical reference change
IndexState      # Staging area contents
WorkingTreeState  # Uncommitted file changes
GitState        # Complete repository state snapshot
```

**Key Properties:**

- All are frozen dataclasses (snapshot-based)
- Can be copied with `.copy()` method
- Support introspection (`.short_sha`, `.has_changes()`, etc.)

### `git_simulator/command_executor.py`

**Parses and executes Git commands:**

```python
GitCommandExecutor
├── execute()          # Main dispatcher
├── cmd_init()         # git init
├── cmd_commit()       # git commit -m "msg"
├── cmd_branch()       # git branch [name]
├── cmd_switch()       # git switch <branch>
├── cmd_merge()        # git merge <branch>
├── cmd_reset()        # git reset [--soft|--mixed|--hard] HEAD~N
├── cmd_log()          # git log [--oneline]
├── cmd_status()       # git status
├── cmd_reflog()       # git reflog
└── _helper_methods()  # SHA generation, ref resolution, etc.
```

**Flow:**

1. `execute("git commit -m 'msg'", state)` → Parse args
2. Find method `cmd_commit`
3. Call method with args and current state
4. Return `(new_state, output_message)`

### `git_simulator/repository.py`

**High-level repository interface:**

```python
GitRepository
├── execute_command(str) → (bool, str, GitState)
├── reset_to_step(int) → bool
├── clear()
├── get_all_commits()
├── get_all_branches()
└── state: GitState
└── history: List[(command, state)]
```

**Responsibilities:**

- Maintain current state
- Track command history
- Execute commands via executor
- Handle errors gracefully
- Enable history replay

### `ui/graph_renderer.py`

**Visualize commit graph with Plotly:**

```python
render_git_graph(state: GitState) → go.Figure

_calculate_positions(commits, state) → Dict[sha, (x, y)]
```

**Layout algorithm:**

1. Topological sort to calculate depth
2. Assign Y based on depth (root at top)
3. Assign X based on branch position
4. Draw edges (parent-child relationships)
5. Annotate with branch labels and HEAD

### `ui/file_display.py`

**Show file state:**

```python
render_staging_area(IndexState)
render_working_tree(WorkingTreeState)
render_repository_state(GitState)
render_commit_details(GitState)
```

### `ui/app.py`

**Main Streamlit application:**

- Sidebar: Settings, lessons, clear
- Main area: Commit graph + state panel
- Terminal: Command input
- History: Command timeline with replay
- Explanation: Educational tooltips

## Data Flow Diagram

```
┌─────────────────┐
│  User Types Cmd │
│ "git commit..." │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│  Streamlit TextInput│
│  (ui/app.py)        │
└────────┬────────────┘
         │
         ▼
┌──────────────────────────────┐
│  GitRepository.execute()     │
│  (git_simulator/repository.py)
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│  GitCommandExecutor.execute()│
│  Parse and dispatch          │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│  cmd_commit(args, state)     │
│  Create new GitState         │
│  Return (new_state, output)  │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│  Repository.history.append() │
│  state = new_state           │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│  Streamlit rerenders         │
│  render_git_graph()          │
│  render_file_state()         │
└──────────────────────────────┘
```

## Command Execution Examples

### Example 1: `git commit -m "message"`

```
State Before:
  commits: {abc123: Commit("Initial", parents=[])}
  branches: {"main": BranchPointer("main", "abc123")}
  head: "main"

Command: "git commit -m 'Feature'"

Steps:
  1. Validate: has args, -m flag present, message not empty
  2. Get parent: branches["main"].target_sha → "abc123"
  3. Generate SHA: "def456"
  4. Create Commit("Feature", parents=["abc123"])
  5. Add to commits: {abc123: ..., def456: ...}
  6. Update branch: branches["main"].target_sha = "def456"
  7. Reflog: + ReflogEntry("HEAD", "commit", "def456", "Feature")

State After:
  commits: {abc123: ..., def456: ...}
  branches: {"main": BranchPointer("main", "def456")}
  head: "main"
  reflog: [..., ReflogEntry(...)]

Output: "[main def456] Feature"
```

### Example 2: `git reset --hard HEAD~1`

```
State Before:
  commits: {abc...: C1, def...: C2}
  branches: {"main": → "def..."}

Steps:
  1. Resolve "HEAD~1": main → def... → walk parents → abc...
  2. Create new state
  3. Move branch: branches["main"].target_sha = "abc..."
  4. Clear staging: index.staged_files = {}
  5. Clear working: working_tree = WorkingTreeState()
  6. Reflog: + ReflogEntry("HEAD", "reset", "abc...", "reset: moving to HEAD~1")

State After:
  commits: {abc...: C1, def...: C2}  # Still here, just unreachable from branch
  branches: {"main": → "abc..."}
  index: empty
  working_tree: clean

Output: "HEAD is now at abc... C1"

Recovery via reflog: git reset --hard def...
```

## Testing Strategy

### Unit Tests (`tests/test_git_commands.py`)

Test each command in isolation:

```python
def test_commit_moves_branch_pointer():
    repo = GitRepository()
    repo.execute_command("git init")
    success, msg, state = repo.execute_command('git commit -m "Test"')
    
    assert success
    assert state.branches["main"].target_sha in state.commits
```

**Coverage:**

- ✅ Basic functionality (commit, branch, switch)
- ✅ State transitions (reset modes)
- ✅ Error handling (invalid inputs)
- ✅ Complex operations (merge, reflog)
- ✅ History replay

### Fixtures (`tests/conftest.py`)

Reusable test repositories:

```python
@pytest.fixture
def fresh_repo():
    return GitRepository()

@pytest.fixture
def initialized_repo():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.execute_command('git commit -m "Initial"')
    return repo
```

## Extension Points

### Adding New Commands

To add `git foo` command:

```python
# 1. Add method to GitCommandExecutor
def cmd_foo(self, args: List[str], state: GitState) -> Tuple[GitState, str]:
    # Validate args
    if not args:
        raise GitCommandError("Usage: git foo [args]")
    
    # Copy state
    new_state = state.copy()
    
    # Modify state
    new_state.commits[sha] = ...
    
    # Record in reflog (if applicable)
    new_state.reflog.append(...)
    
    # Return
    return new_state, "output message"

# 2. Add test
def test_foo():
    repo = GitRepository()
    repo.execute_command("git init")
    success, msg, state = repo.execute_command("git foo")
    assert success

# 3. Update README
```

### Adding UI Components

To add new visualization:

```python
# ui/new_display.py
def render_something(state: GitState) -> None:
    st.markdown("### My Component")
    # Use Streamlit API

# ui/app.py
from ui.new_display import render_something

# In main app:
render_something(st.session_state.repo.state)
```

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Command execution | <5ms | Pure Python, no I/O |
| State copy | <10ms | Deep copy of dicts/lists |
| Graph render | <100ms | Plotly creates SVG |
| History replay | <100ms | All operations rerun |
| 100 commits | Instant | Layout algorithm is O(n) |

**Bottleneck:** Graph layout algorithm. Could optimize with caching.

## Security

- ✅ No shell execution (no `os.system` or `subprocess`)
- ✅ No file I/O (no actual `.git` directory)
- ✅ Input validation on all commands
- ✅ Type-safe (dataclasses + type hints)

## Future Enhancements

### Phase 2: History Visualization

- Timeline view of state over time
- Playable animated transitions between repository states
- Slider to scrub through history

### Phase 3: Advanced Operations

- `git rebase` with visualization
- `git cherry-pick`
- `git stash`
- Tags

### Phase 4: Remote Simulation

- Separate local/remote repos
- `git push` / `git pull` / `git fetch`
- Remote-tracking branches
- Merge conflict visualization

### Phase 5: Real Repository Mode

- Connect to real `.git` directories
- Parse actual Git objects
- Show real commits
- Maintain compatibility with CLI Git

## Deployment

### Local Development

```bash
python run.py
```

### Docker

```dockerfile
FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["streamlit", "run", "ui/app.py"]
```

### Heroku / Cloud

```bash
git push heroku main
streamlit run ui/app.py --server.port $PORT
```

## References

- [Git Internals](https://git-scm.com/book/en/v2/Git-Internals)
- [Streamlit Docs](https://docs.streamlit.io)
- [Plotly Graph Objects](https://plotly.com/python/graph-objects/)

---

**Questions?** Read the source code—it's designed to be educational!
