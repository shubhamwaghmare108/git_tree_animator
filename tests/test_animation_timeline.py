"""Tests for semantic Git animation timeline."""

from git_simulator.repository import GitRepository
from ui.animation_timeline import build_timeline, summarize_transition


def test_timeline_describes_commit_transition():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.execute_command('git commit -m "Initial"')

    events = build_timeline(repo.history)

    assert len(events) == 2
    assert events[-1].step == 2
    assert "Created a commit" in events[-1].summary
    assert events[-1].commits_after == 1


def test_timeline_describes_reset():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.execute_command('git commit -m "C1"')
    repo.execute_command('git commit -m "C2"')
    repo.execute_command("git reset --hard HEAD~1")

    event = build_timeline(repo.history)[-1]
    assert "reflog preserved" in event.summary
    assert event.head_before != event.head_after


def test_empty_timeline_is_safe():
    assert build_timeline([]) == []
