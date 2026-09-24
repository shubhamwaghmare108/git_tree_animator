"""Tests for semantic Git animation timeline."""

from git_simulator.repository import GitRepository
from ui.animation_timeline import build_timeline, summarize_transition, state_at_step, state_diff


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



def test_state_at_step_returns_historical_copy():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.execute_command('git commit -m "Initial"')

    initial = state_at_step(repo.history, 1)
    assert len(initial.commits) == 0

    after_commit = state_at_step(repo.history, 2)
    assert len(after_commit.commits) == 1

    original_target = repo.state.branches["main"].target_sha
    after_commit.branches["main"] = after_commit.branches["main"].__class__(
        name="main", target_sha="mutated"
    )
    assert repo.state.branches["main"].target_sha == original_target


def test_state_at_step_zero_is_initial_state():
    repo = GitRepository()
    repo.execute_command("git init")
    state = state_at_step(repo.history, 0)
    assert state.commits == {}
    assert state.branches == {}


def test_state_diff_reports_repository_changes():
    repo = GitRepository()
    repo.execute_command("git init")
    before = state_at_step(repo.history, 1)
    repo.execute_command('git commit -m "Initial"')
    after = state_at_step(repo.history, 2)

    diff = state_diff(before, after)
    assert diff["commits_added"] == 1
    assert diff["files_added"] == []
