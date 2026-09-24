"""Tests for Mistake Recovery Mode."""

from git_simulator.repository import GitRepository
from ui.recovery import (
    get_recovery_labs,
    capture_recovery_target,
    validate_recovery,
)


def _prepare(lab):
    repo = GitRepository()
    for command in lab["setup"]:
        success, message, _ = repo.execute_command(command)
        assert success, message
    target = capture_recovery_target(lab, repo)
    success, message, _ = repo.execute_command(lab["mistake"])
    assert success, message
    return repo, target


def test_lost_commit_can_be_recovered_from_reflog():
    lab = get_recovery_labs("Intermediate")[0]
    repo, target = _prepare(lab)

    assert repo.state.get_head_commit_sha() != target["head_sha"]
    success, message, _ = repo.execute_command("git reflog")
    assert success
    assert target["head_sha"][:7] in message

    success, message, _ = repo.execute_command(
        f"git reset --hard {target['head_sha']}"
    )
    assert success, message
    assert validate_recovery(lab, repo, target)


def test_detached_head_recovery_restores_branch():
    lab = get_recovery_labs("Beginner")[0]
    repo, target = _prepare(lab)

    assert repo.state.head_is_detached
    success, message, _ = repo.execute_command("git switch main")
    assert success, message
    assert validate_recovery(lab, repo, target)


def test_recovery_labs_have_required_fields():
    for lab in get_recovery_labs():
        assert lab["setup"]
        assert lab["mistake"]
        assert lab["hint"]
        assert lab["target"]
