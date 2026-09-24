"""Goal-oriented Git command challenges.

Each challenge gives the learner a repository situation and a goal. The learner
must enter a Git command that produces the requested state.
"""

COMMAND_CHALLENGES = [
    {
        "id": "soft-reset",
        "level": "Intermediate",
        "title": "Keep the changes staged",
        "setup": ["git init", "git commit -m 'C1'", "git commit -m 'C2'"],
        "goal": "Move the current branch back one commit while keeping the changes from C2 staged.",
        "accepted": ["git reset --soft HEAD~1"],
        "hint": "Choose the reset mode that moves the branch but preserves the index.",
        "explanation": "git reset --soft HEAD~1 moves the branch pointer to its parent and leaves the index and working tree unchanged.",
    },
    {
        "id": "new-branch",
        "level": "Beginner",
        "title": "Create a feature branch",
        "setup": ["git init", "git commit -m 'Initial'"],
        "goal": "Create a branch named feature and switch to it.",
        "accepted": ["git switch -c feature"],
        "hint": "One switch command can create and check out a branch.",
        "explanation": "git switch -c feature creates feature at the current commit and moves HEAD to it.",
    },
    {
        "id": "stash",
        "level": "Intermediate",
        "title": "Temporarily clean the worktree",
        "setup": ["git init", "git commit -m 'Initial'"],
        "goal": "Save your current working changes away and return to a clean working tree.",
        "accepted": ["git stash", "git stash push"],
        "hint": "Use the command designed to temporarily store uncommitted changes.",
        "explanation": "git stash saves working-tree and staged changes and restores a clean working tree.",
    },
    {
        "id": "tag-release",
        "level": "Beginner",
        "title": "Mark a release",
        "setup": ["git init", "git commit -m 'Release'"],
        "goal": "Create a lightweight tag named v1.0 on the current commit.",
        "accepted": ["git tag v1.0"],
        "hint": "A lightweight tag is a simple name pointing at a commit.",
        "explanation": "git tag v1.0 creates a lightweight tag at the current commit.",
    },
    {
        "id": "fetch",
        "level": "Advanced",
        "title": "Update remote-tracking refs",
        "setup": ["git init", "git commit -m 'Initial'", "git remote add origin https://example.test/repo.git"],
        "goal": "Update local remote-tracking references without merging remote work into the current branch.",
        "accepted": ["git fetch origin"],
        "hint": "Use the operation that downloads/refreshes remote-tracking information without integrating it.",
        "explanation": "git fetch updates remote-tracking references while leaving the current local branch and working tree unchanged.",
    },
]


def get_command_challenges(level=None):
    if level and level != "All":
        return [c for c in COMMAND_CHALLENGES if c["level"] == level]
    return list(COMMAND_CHALLENGES)


def normalize_command(command):
    command = command.strip()
    if not command.startswith("git "):
        command = "git " + command
    return " ".join(command.split())


def check_command(challenge, command):
    """Execute the submitted command and validate the resulting state/goal."""
    from git_simulator.repository import GitRepository

    repo = GitRepository()
    for setup_command in challenge["setup"]:
        success, output, _ = repo.execute_command(setup_command)
        if not success:
            return False, repo, f"Challenge setup failed: {output}"

    normalized = normalize_command(command)
    accepted = {normalize_command(value) for value in challenge["accepted"]}
    success, output, _ = repo.execute_command(normalized)
    correct = success and normalized in accepted
    return correct, repo, output if success else output
