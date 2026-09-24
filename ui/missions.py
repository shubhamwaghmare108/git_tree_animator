"""Multi-step Git missions with checkpoints and final-state validation."""

MISSIONS = [
    {
        "id": "feature-release",
        "level": "Beginner",
        "title": "Prepare a feature release",
        "brief": "Create a feature branch, make a commit, return to main, and tag the main release.",
        "steps": [
            {"goal": "Create and switch to a branch named feature.", "accepted": ["git switch -c feature"], "hint": "Use switch with -c."},
            {"goal": "Create the feature commit.", "accepted": ["git commit -m 'Feature work'", "git commit -m "Feature work""], "hint": "Commit the staged snapshot with the requested message."},
            {"goal": "Switch back to main.", "accepted": ["git switch main"], "hint": "Switch branches without creating a new one."},
            {"goal": "Create lightweight tag v1.0 on main.", "accepted": ["git tag v1.0"], "hint": "A lightweight tag is just a name for the current commit."},
        ],
        "setup": ["git init", "git commit -m 'Initial'"],
        "success": "main has the release tag while feature remains a separate branch.",
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
        "success": "The working changes are restored and the stash remains available.",
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


def mission_status(mission, repo, completed_steps):
    """Return a small, deterministic status payload for UI/checkpoint use."""
    return {
        "completed_steps": completed_steps,
        "total_steps": len(mission["steps"]),
        "complete": completed_steps >= len(mission["steps"]),
        "head": repo.state.get_head_commit_sha(),
        "branch": None if repo.state.head_is_detached else repo.state.head,
        "commits": len(repo.state.commits),
        "stashes": len(repo.state.stashes),
    }
