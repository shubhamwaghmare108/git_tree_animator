"""Mistake Recovery Mode: recover a repository from an intentional Git mistake."""

RECOVERY_LABS = [
    {
        "id": "lost-after-reset",
        "level": "Intermediate",
        "title": "Recover a lost commit",
        "brief": "A hard reset moved main backward. Use reflog to find the lost commit and restore the branch.",
        "setup": [
            "git init",
            "git commit -m 'Initial'",
            "git commit -m 'Important work'",
        ],
        "mistake": "git reset --hard HEAD~1",
        "hint": "Run git reflog. Find the commit recorded immediately before the reset, then reset main back to that SHA.",
        "target": "pre_mistake_head",
        "success": "main points to the Important work commit again.",
    },
    {
        "id": "recover-after-detach",
        "level": "Beginner",
        "title": "Escape a detached HEAD",
        "brief": "HEAD was detached at a commit. Recover the normal branch without losing the commit history.",
        "setup": [
            "git init",
            "git commit -m 'Initial'",
            "git commit -m 'Important work'",
        ],
        "mistake": "git detach HEAD~1",
        "hint": "Check the repository state, then switch back to main. The branch pointer is still safe.",
        "target": "pre_mistake_head",
        "success": "HEAD is back on main and main still points to Important work.",
    },
]


def get_recovery_labs(level="All"):
    if level and level != "All":
        return [lab for lab in RECOVERY_LABS if lab["level"] == level]
    return list(RECOVERY_LABS)


def capture_recovery_target(lab, repo):
    """Capture the state that the learner must restore after the mistake."""
    if lab["target"] == "pre_mistake_head":
        return {"head_sha": repo.state.get_head_commit_sha(), "branch": repo.state.head}
    return {}


def validate_recovery(lab, repo, target):
    """Validate the recovered repository state rather than a command sequence."""
    state = repo.state
    if lab["id"] == "lost-after-reset":
        return (
            not state.head_is_detached
            and state.head == target.get("branch")
            and state.branches.get("main")
            and state.branches["main"].target_sha == target.get("head_sha")
        )
    if lab["id"] == "recover-after-detach":
        return (
            not state.head_is_detached
            and state.head == target.get("branch")
            and state.branches.get("main")
            and state.branches["main"].target_sha == target.get("head_sha")
        )
    return False


def recovery_status(lab, repo, target):
    return {
        "complete": validate_recovery(lab, repo, target),
        "head": repo.state.get_head_commit_sha(),
        "branch": None if repo.state.head_is_detached else repo.state.head,
        "detached": repo.state.head_is_detached,
        "reflog_entries": len(repo.state.reflog),
    }
