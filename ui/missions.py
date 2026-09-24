"""Multi-step Git missions with state-based checkpoint validation."""

MISSIONS = [
    {
        "id": "feature-release",
        "level": "Beginner",
        "title": "Prepare a feature release",
        "brief": "Create a feature branch, make a commit, return to main, and tag the main release.",
        "steps": [
            {"goal": "Create and switch to a branch named feature.", "accepted": ["git switch -c feature"], "hint": "Use switch with -c."},
            {"goal": "Create the feature commit.", "accepted": ["git commit -m 'Feature work'", 'git commit -m "Feature work"'], "hint": "Commit the staged snapshot with the requested message."},
            {"goal": "Switch back to main.", "accepted": ["git switch main"], "hint": "Switch branches without creating a new one."},
            {"goal": "Create lightweight tag v1.0 on main.", "accepted": ["git tag v1.0"], "hint": "A lightweight tag is a simple name pointing at the current commit."},
        ],
        "setup": ["git init", "git commit -m 'Initial'"],
        "success": "main has the release tag while feature remains a separate branch.",
        "validator": "feature_release",
    },
    {
        "id": "safe-work",
        "level": "Intermediate",
        "title": "Safely park unfinished work",
        "brief": "Save unfinished changes, switch branches, then restore the work.",
        "steps": [
            {"goal": "Save the current unfinished work in a stash.", "accepted": ["git stash", "git stash push"], "hint": "Temporarily store uncommitted changes."},
            {"goal": "Switch to main.", "accepted": ["git switch main"], "hint": "Return to the main branch."},
            {"goal": "Restore the latest stash without deleting it.", "accepted": ["git stash apply"], "hint": "Apply restores; pop restores and removes."},
        ],
        "setup": ["git init", "git commit -m 'Initial'"],
        "setup_files": {"notes.txt": "unfinished work"},
        "success": "The working changes are restored and the stash remains available.",
        "validator": "safe_work",
    },
]


def get_missions(level="All"):
    if level and level != "All":
        return [m for m in MISSIONS if m["level"] == level]
    return list(MISSIONS)


def command_matches(command, accepted):
    normalized = " ".join(command.strip().split())
    if not normalized.startswith("git "):
        normalized = "git " + normalized
    return normalized in {" ".join(a.split()) for a in accepted}


def validate_mission(mission, repo):
    """Validate the actual repository state, independent of command history."""
    state = repo.state

    if mission["validator"] == "feature_release":
        feature = state.branches.get("feature")
        main = state.branches.get("main")
        tag = state.tags.get("v1.0")
        if not feature or not main or not tag:
            return False
        if tag.target_sha != main.target_sha:
            return False
        return feature.target_sha != main.target_sha

    if mission["validator"] == "safe_work":
        if not state.stashes:
            return False
        restored = (
            state.working_tree.modified_files.get("notes.txt")
            or state.working_tree.new_files.get("notes.txt")
        )
        return restored == "unfinished work"

    return False


def mission_status(mission, repo, completed_steps):
    return {
        "completed_steps": completed_steps,
        "total_steps": len(mission["steps"]),
        "complete": validate_mission(mission, repo),
        "head": repo.state.get_head_commit_sha(),
        "branch": None if repo.state.head_is_detached else repo.state.head,
        "commits": len(repo.state.commits),
        "stashes": len(repo.state.stashes),
    }
