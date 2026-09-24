# Quick Start Guide

Get Git Tree Animator running in 5 minutes! 🚀

## 1. Prerequisites

Make sure you have Python 3.10+ installed:

```bash
python --version
```

## 2. Setup

### Clone/Download

```bash
# If you have git
git clone <repository-url>
cd git-tree-animator

# Or extract the zip file and navigate to it
```

### Create Virtual Environment

```bash
# Create venv
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

## 3. Run the Application

```bash
python run.py
```

Your browser should open at `http://localhost:8501`

If not, open it manually and navigate to that URL.

## 4. Try Your First Commands

In the terminal input at the bottom:

```bash
# Type this (without "git " - it adds it automatically)
init
```

Click **Run**. You should see the repository initialized.

Now try:

```bash
commit -m "First commit"
```

You should see a commit appear in the graph!

## 5. Explore

### Use the Sidebar

- **Settings**: Change education mode
- **Lessons**: Click "📖 Basic Git" to auto-load commands
- **Clear Everything**: Reset to start over

### Try Commands

```bash
branch feature
switch feature
commit -m "Feature work"
switch main
merge feature
```

Watch the graph update in real-time!

### Step Back in Time

Scroll down to "Command History" and click "↶" to revert to any previous step.

## 6. Run Tests

Make sure everything works:

```bash
pytest tests/ -v
```

You should see 50+ passing tests.

## 7. Learn More

Read these files:

- **README.md** - Full documentation
- **ARCHITECTURE.md** - How it works internally
- **git_simulator/command_executor.py** - Core command logic

## Common Issues

### Port 8501 already in use

```bash
streamlit run ui/app.py --server.port 8502
```

### ModuleNotFoundError

Make sure virtual environment is activated:

```bash
# Check if you see (venv) in your prompt
# If not, activate it:
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate      # Windows
```

### Tests not found

Make sure you're in the project root directory:

```bash
ls tests/  # Should show test files
pytest tests/ -v
```

## Next Steps

### 1. Try All Lessons

- Basic Git
- Branching
- Merge
- Reset

### 2. Practice Commands

```bash
# Create a complex scenario
init
commit -m "v1"
switch -c dev
commit -m "Feature A"
switch main
merge dev
reset --soft HEAD~1
branch -d dev
```

### 3. Read the Code

The codebase is educational:

- `git_simulator/state.py` - How Git state is modeled
- `git_simulator/command_executor.py` - How commands work
- `ui/app.py` - How the UI is built

### 4. Extend It

Add a new command (e.g., `git revert`):

1. Add method to `GitCommandExecutor`
2. Write test in `tests/test_git_commands.py`
3. Run tests
4. It automatically appears in the app!

## Example Scenarios

### Scenario 1: Basic Workflow

```bash
init
add .
commit -m "Initial commit"
status
log --oneline
```

### Scenario 2: Feature Branch

```bash
init
commit -m "Main"
branch feature
switch feature
commit -m "Feature v1"
commit -m "Feature v2"
switch main
merge feature
```

### Scenario 3: Mistake & Recovery

```bash
init
commit -m "Good"
commit -m "Oops"
reflog
reset --hard HEAD~1
reflog
```

### Scenario 4: Reset Modes

```bash
init
commit -m "C1"
commit -m "C2"
reset --soft HEAD~1        # Keep changes staged
reset --mixed HEAD~1       # Keep changes unstaged
reset --hard HEAD~1        # Discard changes
```

## Tips & Tricks

### Use Keyboard Shortcuts

- Click on the input field and press Enter to run
- Use Ctrl+A to select all and clear

### View Commit Details

Hover over commits in the graph to see:
- Full SHA
- Commit message
- Parent commits

### Monitor Repository State

The right panel shows:
- Current branch
- Number of commits
- Staging area
- Working directory changes

### History Timeline

The "Command History" section shows every command you've run.

Click "↶" next to any command to go back to that point in time.

## Educational Mode

**Beginner Mode** (default):
- Commits
- Branches
- HEAD
- Basic operations

**Intermediate Mode**:
- + Merge
- + Reset
- + Restore
- + Reflog

**Advanced Mode**:
- + Rebase
- + Detached HEAD
- + Cherry-pick
- + Remote branches

Select from the sidebar.

## Understanding Git Better

After running commands, check:

1. **Commit Graph** - See how commits connect
2. **Repository State** - See current branch, commits, reflog
3. **Command Explanation** - Understand what just happened
4. **History Timeline** - Review all steps taken

This combines all the mental models Git requires!

## Get Stuck?

1. Check the error message - it tells you exactly what's wrong
2. Review the explanation panel
3. Look at previous commands in history
4. Read ARCHITECTURE.md to understand internals
5. Check tests in `tests/test_git_commands.py` for examples

## You're Ready! 🎉

You now understand:

✅ How Git commits are created  
✅ How branches work  
✅ How to merge  
✅ How reset affects state  
✅ What reflog does  

Now go explore and learn more about Git! 🚀

---

**Questions?** Open an issue or check the README.
