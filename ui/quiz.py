"""Interactive Git quiz scenarios for the Streamlit application."""

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
        "question": "After the commands, where does the feature branch point?",
        "options": [
            "The Initial commit",
            "The Feature work commit",
            "It points to HEAD itself",
            "Branches contain copies of all commits",
        ],
        "answer": 1,
        "explanation": "A branch is a movable reference to one commit. After the commit on feature, feature points to the new commit.",
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
        "question": "What does --soft reset change?",
        "options": [
            "Only the branch pointer; staged changes are preserved",
            "The branch pointer and working tree, but not the index",
            "It deletes the C2 commit object",
            "It creates a new commit",
        ],
        "answer": 0,
        "explanation": "A soft reset moves the current branch pointer while preserving the index and working-tree state.",
    },
    {
        "id": "stash",
        "level": "Intermediate",
        "title": "Where did my work go?",
        "setup": [
            "git init",
            "git commit -m 'Initial'",
            "edit app.py",
            "git stash",
        ],
        "question": "What should you expect after git stash?",
        "options": [
            "The changes are committed to main",
            "The changes are saved in the stash and the working tree becomes clean",
            "The changes are permanently deleted",
            "A new branch named stash is created",
        ],
        "answer": 1,
        "explanation": "Stash saves the current changes separately so the working tree can become clean. git stash apply can restore them.",
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
        "question": "What does detached HEAD mean?",
        "options": [
            "HEAD points directly to a commit rather than a branch",
            "All branches were deleted",
            "The repository is corrupted",
            "HEAD points to the remote server",
        ],
        "answer": 0,
        "explanation": "In detached HEAD state, HEAD identifies a commit directly. Creating a branch from that commit preserves new work.",
    },
]


def get_quizzes(level=None):
    """Return quiz scenarios, optionally filtered by level."""
    if level and level != "All":
        return [quiz for quiz in QUIZZES if quiz["level"] == level]
    return list(QUIZZES)
