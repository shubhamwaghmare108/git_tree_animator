# 🌳 Git Tree Animator

A Python-based interactive web application that helps students **visually understand how Git commands affect repository state**.

Rather than just showing a commit graph, Git Tree Animator animates the state transitions and clearly displays:

- **Commits** with SHA identifiers
- **Branches** as pointers to commits
- **HEAD** reference
- **Working Directory** and **Staging Area**
- **Reflog** entries for recovery
- Real-time state changes as commands are executed

## Features (Phase 1)

### ✅ Implemented

- **Repository**
  - `git init` - Initialize repository
  - `git status` - Show repository status
  - `git log` - Display commit history
  - `git reflog` - Show reference log

- **Staging**
  - `git add .` - Stage files
  - `git restore --staged <file>` - Unstage files

- **Commits**
  - `git commit -m "message"` - Create commits

- **Branches**
  - `git branch [name]` - List/create branches
  - `git branch -d <name>` - Delete branches

- **Switching**
  - `git switch <branch>` - Switch branches
  - `git switch -c <branch>` - Create and switch
  - `git checkout <branch>` - Legacy checkout
  - `git checkout -b <branch>` - Legacy create+switch

- **Merging**
  - `git merge <branch>` - Merge branches
  - Fast-forward merge detection
  - Ancestor-aware three-way merge with merge commits
  - Interactive conflict resolution with `git merge --continue` / `--abort`

- **Rebase**
  - `git rebase <branch>` - Replay current-branch commits onto another branch
  - New commit snapshots and parent relationships for replayed commits
  - Interactive conflict pause/resolution with `git rebase --continue`
  - `git rebase --abort` restores the original branch tip

- **Reset**
  - `git reset --soft HEAD~1` - Soft reset
  - `git reset --mixed HEAD~1` - Mixed reset (default)
  - `git reset --hard HEAD~1` - Hard reset

- **Restore**
  - `git restore <file>` - Discard changes
  - `git restore --staged <file>` - Unstage files

- **Interactive Features**
  - Command history with step-by-step replay
  - Revert to any previous state
  - Educational explanations
  - Built-in lessons
  - Commit graph visualization

## Technology Stack

- **Backend**: Python 3.10+
- **Frontend**: Streamlit (interactive web framework)
- **Visualization**: Plotly (interactive graphs)
- **Testing**: pytest
- **Type Safety**: Python dataclasses + type hints

## Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Setup

1. **Clone or download this repository:**

```bash
cd git-tree-animator
```

2. **Create a virtual environment (recommended):**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

## Running the Application

### Start the web app:

```bash
python run.py
```

The app will open in your default browser at `http://localhost:8501`

## Running Tests

Run the full test suite:

```bash
pytest tests/ -v
```

Run specific test file:

```bash
pytest tests/test_git_commands.py -v
```

Run with coverage:

```bash
pytest tests/ --cov=git_simulator --cov-report=html
```

## Project Structure

```
git-tree-animator/
├── git_simulator/              # Core Git simulation engine
│   ├── __init__.py
│   ├── state.py               # snapshot-based state models
│   ├── command_executor.py    # Git command parser/executor
│   ├── repository.py          # Main repository class
│   └── errors.py              # Custom exceptions
│
├── ui/                         # Streamlit UI components
│   ├── __init__.py
│   ├── app.py                 # Main Streamlit app
│   ├── graph_renderer.py      # Plotly commit graph
│   └── file_display.py        # File state display
│
├── tests/                      # Test suite
│   ├── conftest.py            # Pytest fixtures
│   ├── test_git_commands.py   # Command tests
│   └── __init__.py
│
├── requirements.txt           # Python dependencies
├── run.py                     # Entry point
└── README.md                  # This file
```

## How It Works

### Git Simulator Engine

The simulator maintains an snapshot-based `GitState` that tracks:

```python
class GitState:
    commits: Dict[sha, Commit]          # All commits
    branches: Dict[name, BranchPointer] # Branch references
    head: str                           # Current branch/commit
    index: IndexState                   # Staging area
    working_tree: WorkingTreeState      # Working directory changes
    reflog: List[ReflogEntry]           # Reference log
```

### Command Execution

1. User enters a command (e.g., `git commit -m "message"`)
2. `GitCommandExecutor` parses the command
3. Executor creates a new `GitState` with the changes
4. Streamlit UI re-renders with the new state
5. Previous state is saved in history for replay

### Visualization

The commit graph is rendered using Plotly:

- Commits are positioned based on topological sort
- Branches point to their target commits
- HEAD indicates the current reference
- Edges show parent-child relationships
- Interactive hover shows commit details

## Usage Examples

### Basic Git Workflow

```
$ git init
$ git add .
$ git commit -m "Initial commit"
$ git branch feature
$ git switch feature
$ git commit -m "Feature work"
$ git switch main
$ git merge feature
```

### Reset & Recovery

```
$ git commit -m "Oops"
$ git reset --soft HEAD~1
$ git reflog
$ git reset --hard <recovered-sha>
```

## Lessons

The app includes built-in lessons:

1. **Basic Git** - init, add, commit
2. **Branching** - create and switch branches
3. **Merge** - merge branches together
4. **Reset** - practice different reset modes

Click the lesson buttons in the sidebar to auto-load the commands.

## Educational Value

This tool teaches:

✅ Commits are snapshots with identifiers  
✅ Branches are pointers, not copies  
✅ HEAD points to the current reference  
✅ Staging area vs working directory  
✅ Merge strategies (fast-forward vs 3-way)  
✅ Reset modes (--soft, --mixed, --hard)  
✅ Reflog for recovery  
✅ Detached HEAD state  

## Phase 2+ Roadmap

- [ ] Revert commits
- [x] Rebase with animation and conflict workflow
- [x] Cherry-pick with conflict resolution
- [x] Detached HEAD visualization and recovery
- [x] Remote repository simulation
- [x] Push/pull/fetch animations
- [x] Merge conflicts
- [x] Stash
- [x] Tags
- [x] Interactive quizzes
- [ ] Real Git repository mode (libgit2)

## Architecture Decisions

### Immutability

`GitState` is snapshot-based (via dataclasses). Each command creates a new state:

```python
new_state = state.copy()  # Doesn't mutate the original
# ... modify new_state ...
return new_state  # Return new reference
```

This makes history replay trivial and prevents bugs.

### Deterministic SHAs

Commits get fake but deterministic SHAs based on:

```
sha1(message + parent_sha + counter)
```

This ensures the same sequence of commands produces the same SHAs.

### No External Git

The simulator doesn't call the actual `git` CLI. It's 100% Python, making it:

- Fast
- Educational (you can read the code)
- Platform-independent
- Easy to extend

### Streamlit

Streamlit handles:

- Hot reload (change code, app updates instantly)
- Session state management
- Reactive UI
- No frontend framework needed

## Testing

The test suite covers:

- ✅ 50+ unit tests
- ✅ All Git commands
- ✅ Edge cases and error handling
- ✅ State transitions
- ✅ History replay
- ✅ Merge strategies

Run: `pytest tests/ -v`

## Performance

- Commit graph with 100+ commits: instant
- Command execution: < 100ms
- Animation: GPU-accelerated via Plotly
- No database required

## Troubleshooting

### Port already in use

If port 8501 is taken:

```bash
streamlit run ui/app.py --server.port 8502
```

### Module not found

Make sure you're in the project directory and dependencies are installed:

```bash
pip install -r requirements.txt
```

### Tests failing

Ensure pytest is installed:

```bash
pip install pytest
pytest tests/ -v
```

## Contributing

Ideas for improvement:

1. Add more Git commands (stash, tag, etc.)
2. Improve graph layout algorithm
3. Add keyboard shortcuts
4. Export scenario as image
5. Create quiz mode
6. Add real repository mode

## License

MIT

## Author

Built for educational purposes. Learn Git by seeing exactly what it does! 🚀

---

**Questions?** Check the [inline comments](git_simulator/command_executor.py) in the code or run the tests to understand how it works.


## New in the state-transition upgrade

The simulator now keeps a simplified committed file tree on every commit. The UI includes a working-tree editor so learners can make a file change, run `git add .`, and then commit it. The graph can replay command-history states with Play/Pause controls and a step slider.

The simulator also uses shell-style argument parsing for quoted commit messages and performs an ancestor-aware three-way merge. Files changed differently on both sides receive visible conflict markers.


## Rebase visualization

The simulator models rebase as a sequence of snapshot transformations. Original
commits are retained, while replayed commits receive new deterministic SHAs and
new parents. If a replay cannot be applied cleanly, the operation pauses and
the UI exposes the conflicted files.

Example:

```
git switch feature
git rebase main
# resolve conflicts if necessary
git add .
git rebase --continue
# or:
git rebase --abort
```

This is an educational model rather than a byte-for-byte implementation of
Git's internal rebase machinery.


## Cherry-pick visualization

The simulator models cherry-pick as applying the selected commit's snapshot
delta to the current branch. A successful operation creates a new commit with
the current HEAD as its parent while preserving the source commit.

Example:

```
git switch main
git cherry-pick <commit-sha>
```

When the patch conflicts, the operation pauses so the learner can edit the
conflicted file, run `git add .`, and choose `git cherry-pick --continue`.
The operation can also be cancelled with `git cherry-pick --abort`.


## Detached HEAD visualization

The simulator includes an educational `git detach <commit>` command that moves
HEAD directly to a commit without moving any branch pointer. The UI highlights
this state and provides a recovery control to switch back to an existing branch.

The reflog records the detached transition, making it possible to teach the
relationship between HEAD, branch references, and recoverable history.


## Remote repository simulation

The simulator models a remote as an in-memory teaching repository:

```
git remote add origin https://example.com/student/demo.git
git push origin main
git fetch origin
git pull origin main
```

The graph distinguishes local branches from remote-tracking references such as
`origin/main`. Push moves the simulated remote ref, fetch refreshes the local
remote-tracking ref without moving the current branch, and pull performs a
fast-forward when the histories are compatible. Divergent pull histories are
reported instead of silently creating a merge.


## Stash workflow

The simulator includes an educational stash stack:

```
git stash
git stash list
git stash apply stash@{0}
git stash pop
git stash drop stash@{0}
```

A stash captures simulated working-tree and staged changes, then returns the
working tree to a clean state. **apply** restores the changes while keeping the
stash; **pop** restores and removes it. The Streamlit UI exposes the latest
stash for quick apply/pop demonstrations.


## Tag workflow

Tags give commits stable, human-readable names:

```
git tag v1.0
git tag -a v1.0 -m "first release"
git tag v1.0 <commit>
git tag
git tag -d v1.0
```

The graph displays tags directly beside their target commits. Annotated tags are
distinguished from lightweight tags, and tag names can be used anywhere the
simulator resolves a commit reference.


## Interactive Git challenges

The app includes prediction-based quizzes at Beginner, Intermediate, and
Advanced levels. Each challenge gives a command scenario, asks the learner to
predict the resulting Git state, then explains the expected result.

The quiz score is tracked during the current Streamlit session so learners can
repeat scenarios and build confidence before using the terminal.


### State-aware Git challenges

Quiz scenarios now execute against a fresh GitRepository before the answer is revealed. After a prediction, learners can inspect the actual HEAD, branch pointers, commit graph, and command-by-command results. This turns the quiz from a static multiple-choice exercise into a simulator-backed prediction exercise.
