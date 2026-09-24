"""State-aware interactive Git challenge scenarios."""

QUIZZES = [
    {
        "id": "branch-pointer",
        "level": "Beginner",
        "title": "Where does the branch point?",
        "setup": [
            "git init",
            "git commit -m 'Initial'",
            "git branch feature",
            "git switch feature",
            "git commit -m 'Feature work'",
        ],
        "question": "After the scenario is executed, where does the feature branch point?",
        "options": [
            "The Initial commit",
            "The Feature work commit",
            "HEAD itself, independently of commits",
            "Branches contain copies of all commits",
        ],
        "answer": 1,
        "explanation": "A branch is a movable reference to one commit. The feature branch moves when the commit is created while feature is checked out.",
    },
    {
        "id": "reset-soft",
        "level": "Intermediate",
        "title": "Predict a soft reset",
        "setup": [
            "git init",
            "git commit -m 'C1'",
            "git commit -m 'C2'",
            "git reset --soft HEAD~1",
        ],
        "question": "Which state change should the simulator show after --soft reset?",
        "options": [
            "The branch moves back one commit while staged changes are preserved",
            "The branch moves and the index is discarded",
            "The C2 commit object is deleted",
            "A new commit is created",
        ],
        "answer": 0,
        "explanation": "Soft reset moves the branch pointer but preserves the index and working-tree state represented by the changes from the removed tip.",
    },
    {
        "id": "merge-commit",
        "level": "Advanced",
        "title": "Predict a merge graph",
        "setup": [
            "git init",
            "git commit -m 'C1'",
            "git branch feature",
            "git switch feature",
            "git commit -m 'Feature'",
            "git switch main",
            "git commit -m 'Main'",
            "git merge feature",
        ],
        "question": "What graph shape should appear after the merge?",
        "options": [
            "A merge commit with two parents",
            "The feature branch is deleted automatically",
            "The feature commit is copied without a new commit",
            "HEAD becomes detached",
        ],
        "answer": 0,
        "explanation": "Both branches diverged after C1, so merging feature into main creates a merge commit with the main and feature tips as parents.",
    },
    {
        "id": "cherry-pick",
        "level": "Advanced",
        "title": "Predict cherry-pick",
        "setup": [
            "git init",
            "git commit -m 'C1'",
            "git branch feature",
            "git switch feature",
            "git commit -m 'Feature'",
            "git switch main",
            "git cherry-pick feature",
        ],
        "question": "What should happen to main?",
        "options": [
            "main receives a new commit containing the picked change",
            "main becomes the same branch object as feature",
            "feature is deleted",
            "HEAD becomes detached",
        ],
        "answer": 0,
        "explanation": "Cherry-pick replays a commit's change on the current branch and creates a new commit identity.",
    },
    {
        "id": "detached-head",
        "level": "Advanced",
        "title": "Identify detached HEAD",
        "setup": [
            "git init",
            "git commit -m 'C1'",
            "git detach HEAD",
        ],
        "question": "What does the resulting repository state show?",
        "options": [
            "HEAD points directly to a commit rather than a branch",
            "All branches were deleted",
            "The repository is corrupted",
            "HEAD points to the remote server",
        ],
        "answer": 0,
        "explanation": "Detached HEAD means HEAD stores a commit SHA directly instead of naming a branch. The graph can show HEAD at that commit while main remains unchanged.",
    },
]


def get_quizzes(level=None):
    """Return quiz scenarios, optionally filtered by level."""
    if level and level != "All":
        return [quiz for quiz in QUIZZES if quiz["level"] == level]
    return list(QUIZZES)


def run_quiz_scenario(quiz):
    """Execute a scenario in a fresh simulator and return its real resulting state."""
    from git_simulator.repository import GitRepository

    repo = GitRepository()
    results = []
    for command in quiz["setup"]:
        success, output, state = repo.execute_command(command)
        results.append({"command": command, "success": success, "output": output})
        if not success:
            raise RuntimeError(f"Quiz setup failed for {command}: {output}")
    return repo, results
