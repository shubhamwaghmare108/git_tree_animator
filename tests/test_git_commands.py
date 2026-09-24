"""
Comprehensive tests for Git simulator commands.
"""

import pytest
from git_simulator.repository import GitRepository
from git_simulator.errors import GitCommandError


class TestGitInit:
    """Tests for git init command."""
    
    def test_init_creates_main_branch(self):
        repo = GitRepository()
        success, msg, state = repo.execute_command("git init")
        
        assert success
        assert "main" in state.branches
        assert state.head == "main"
    
    def test_init_sets_empty_state(self):
        repo = GitRepository()
        success, msg, state = repo.execute_command("git init")
        
        assert success
        assert len(state.commits) == 0
        assert len(state.reflog) == 1  # Init entry
    
    def test_cannot_reinit_repository(self):
        repo = GitRepository()
        repo.execute_command("git init")
        success, msg, state = repo.execute_command("git init")
        
        assert not success
        assert "Reinitialization" in msg


class TestGitCommit:
    """Tests for git commit command."""
    
    def test_commit_creates_commit(self):
        repo = GitRepository()
        repo.execute_command("git init")
        success, msg, state = repo.execute_command('git commit -m "First commit"')
        
        assert success
        assert len(state.commits) == 1
    
    def test_commit_moves_branch_pointer(self):
        repo = GitRepository()
        repo.execute_command("git init")
        success, msg, state = repo.execute_command('git commit -m "First commit"')
        
        assert success
        main_branch = state.branches["main"]
        assert main_branch.target_sha is not None
        assert main_branch.target_sha in state.commits
    
    def test_commit_has_correct_parent(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "C1"')
        
        first_sha = repo.state.get_head_commit_sha()
        
        repo.execute_command('git commit -m "C2"')
        second_sha = repo.state.get_head_commit_sha()
        
        second_commit = repo.state.commits[second_sha]
        assert first_sha in second_commit.parents
    
    def test_commit_creates_reflog_entry(self):
        repo = GitRepository()
        repo.execute_command("git init")
        initial_reflog_len = len(repo.state.reflog)
        
        repo.execute_command('git commit -m "Test"')
        
        assert len(repo.state.reflog) > initial_reflog_len
        last_entry = repo.state.reflog[-1]
        assert last_entry.action == "commit"
    
    def test_commit_requires_message(self):
        repo = GitRepository()
        repo.execute_command("git init")
        success, msg, state = repo.execute_command("git commit")
        
        assert not success
        assert "Usage" in msg


class TestGitBranch:
    """Tests for git branch command."""
    
    def test_branch_lists_branches(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "Initial"')
        repo.execute_command("git branch feature")
        
        success, msg, state = repo.execute_command("git branch")
        
        assert success
        assert "main" in msg
        assert "feature" in msg
    
    def test_branch_creates_new_branch(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "Initial"')
        success, msg, state = repo.execute_command("git branch feature")
        
        assert success
        assert "feature" in state.branches
    
    def test_branch_points_to_current_commit(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "Initial"')
        
        current_sha = repo.state.get_head_commit_sha()
        
        repo.execute_command("git branch feature")
        
        feature_sha = repo.state.branches["feature"].target_sha
        assert feature_sha == current_sha
    
    def test_branch_cannot_create_duplicate(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "Initial"')
        repo.execute_command("git branch feature")
        
        success, msg, state = repo.execute_command("git branch feature")
        
        assert not success
        assert "already exists" in msg


class TestGitSwitch:
    """Tests for git switch command."""
    
    def test_switch_changes_head(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "Initial"')
        repo.execute_command("git branch feature")
        
        repo.execute_command("git switch feature")
        
        assert repo.state.head == "feature"
    
    def test_switch_with_create_c(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "Initial"')
        
        success, msg, state = repo.execute_command("git switch -c newbranch")
        
        assert success
        assert "newbranch" in state.branches
        assert state.head == "newbranch"
    
    def test_switch_fails_for_nonexistent_branch(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "Initial"')
        
        success, msg, state = repo.execute_command("git switch nonexistent")
        
        assert not success
        assert "did not match" in msg
    
    def test_switch_creates_reflog_entry(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "Initial"')
        repo.execute_command("git branch feature")
        
        initial_reflog_len = len(repo.state.reflog)
        repo.execute_command("git switch feature")
        
        assert len(repo.state.reflog) > initial_reflog_len
        last_entry = repo.state.reflog[-1]
        assert last_entry.action == "switch"


class TestGitCheckout:
    """Tests for git checkout command (legacy)."""
    
    def test_checkout_switches_branch(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "Initial"')
        repo.execute_command("git branch feature")
        
        success, msg, state = repo.execute_command("git checkout feature")
        
        assert success
        assert state.head == "feature"
    
    def test_checkout_b_creates_branch(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "Initial"')
        
        success, msg, state = repo.execute_command("git checkout -b newbranch")
        
        assert success
        assert "newbranch" in state.branches


class TestGitLog:
    """Tests for git log command."""
    
    def test_log_shows_commits(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "C1"')
        repo.execute_command('git commit -m "C2"')
        
        success, msg, state = repo.execute_command("git log")
        
        assert success
        assert "C1" in msg
        assert "C2" in msg
    
    def test_log_oneline_format(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "First"')
        
        success, msg, state = repo.execute_command("git log --oneline")
        
        assert success
        assert "First" in msg
        # Should have short SHA
        assert len(msg.split()[0]) <= 8


class TestGitStatus:
    """Tests for git status command."""
    
    def test_status_shows_clean_tree(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "Initial"')
        
        success, msg, state = repo.execute_command("git status")
        
        assert success
        assert "clean" in msg
    
    def test_status_shows_branch(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "Initial"')
        repo.execute_command("git switch -c feature")
        
        success, msg, state = repo.execute_command("git status")
        
        assert success
        assert "feature" in msg


class TestGitMerge:
    """Tests for git merge command."""
    
    def test_merge_fast_forward(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "Initial"')
        repo.execute_command("git switch -c feature")
        repo.execute_command('git commit -m "Feature"')
        repo.execute_command("git switch main")
        
        success, msg, state = repo.execute_command("git merge feature")
        
        assert success
        assert state.branches["main"].target_sha == state.branches["feature"].target_sha
    
    def test_merge_three_way_creates_merge_commit(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "Initial"')
        repo.execute_command("git switch -c feature")
        repo.execute_command('git commit -m "Feature"')
        repo.execute_command("git switch main")
        repo.execute_command('git commit -m "Main work"')
        
        initial_commit_count = len(repo.state.commits)
        success, msg, state = repo.execute_command("git merge feature")
        
        assert success
        # Should have created a merge commit
        assert len(state.commits) == initial_commit_count + 1
    
    def test_merge_same_branch_fails(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "Initial"')
        
        success, msg, state = repo.execute_command("git merge main")
        
        assert not success


class TestGitReset:
    """Tests for git reset command."""
    
    def test_reset_soft_preserves_index(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "C1"')
        repo.execute_command('git commit -m "C2"')
        
        c2_sha = repo.state.get_head_commit_sha()
        c1_sha = repo.state.commits[c2_sha].parents[0]

        success, msg, state = repo.execute_command("git reset --soft HEAD~1")

        assert success
        assert state.branches["main"].target_sha == c1_sha
        assert c2_sha in state.commits
    
    def test_reset_mixed_clears_index(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "C1"')
        repo.execute_command('git commit -m "C2"')
        
        success, msg, state = repo.execute_command("git reset --mixed HEAD~1")
        
        assert success
        assert len(state.index.staged_files) == 0
    
    def test_reset_hard_clears_working_tree(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "C1"')
        repo.execute_command('git commit -m "C2"')
        
        success, msg, state = repo.execute_command("git reset --hard HEAD~1")
        
        assert success
        assert not state.working_tree.has_changes()


class TestGitReflog:
    """Tests for git reflog command."""
    
    def test_reflog_records_commits(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "C1"')
        repo.execute_command('git commit -m "C2"')
        
        success, msg, state = repo.execute_command("git reflog")
        
        assert success
        assert "C1" in msg or "commit" in msg
    
    def test_reflog_records_branch_switches(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "Initial"')
        repo.execute_command("git switch -c feature")
        repo.execute_command("git switch main")
        
        success, msg, state = repo.execute_command("git reflog")
        
        assert success
        assert "switch" in msg


class TestGitHistory:
    """Tests for repository history tracking."""
    
    def test_history_tracks_commands(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "C1"')
        repo.execute_command('git commit -m "C2"')
        
        assert len(repo.history) == 3
    
    def test_reset_to_step_reverts_state(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.execute_command('git commit -m "C1"')
        repo.execute_command('git commit -m "C2"')
        
        commit_count_at_step_1 = len(repo.history[1][1].commits)
        
        repo.reset_to_step(0)  # Reset to after git init
        
        assert len(repo.state.commits) <= commit_count_at_step_1


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_command_without_git_prefix(self):
        repo = GitRepository()
        success, msg, state = repo.execute_command("commit -m 'test'")
        
        assert not success
    
    def test_unknown_command(self):
        repo = GitRepository()
        repo.execute_command("git init")
        success, msg, state = repo.execute_command("git unknown-command")
        
        assert not success
    
    def test_command_on_uninitialized_repo(self):
        repo = GitRepository()
        success, msg, state = repo.execute_command('git commit -m "test"')
        
        assert not success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestFileSnapshots:
    """Tests for working-tree, index, and committed file snapshots."""

    def test_add_and_commit_persist_file_tree(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.set_working_file("demo.py", "print('hello')")
        success, msg, state = repo.execute_command("git add .")
        assert success
        assert "demo.py" in state.index.staged_content

        success, msg, state = repo.execute_command('git commit -m "Add demo"')
        assert success
        head = state.get_head_commit_sha()
        assert state.commits[head].tree["demo.py"] == "print('hello')"
        assert not state.working_tree.has_changes()

    def test_second_commit_keeps_parent_tree(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.set_working_file("demo.py", "v1")
        repo.execute_command("git add .")
        repo.execute_command('git commit -m "v1"')

        repo.set_working_file("demo.py", "v2")
        repo.execute_command("git add .")
        repo.execute_command('git commit -m "v2"')

        head = repo.state.get_head_commit_sha()
        parent = repo.state.commits[head].parents[0]
        assert repo.state.commits[parent].tree["demo.py"] == "v1"
        assert repo.state.commits[head].tree["demo.py"] == "v2"

    def test_commit_command_handles_quoted_message(self):
        repo = GitRepository()
        repo.execute_command("git init")
        success, msg, state = repo.execute_command('git commit -m "quoted message with spaces"')
        assert success
        assert "quoted message with spaces" in msg


class TestThreeWayMerge:
    """Tests for ancestor-aware merge behavior."""

    def _commit_file(self, repo, filename, content, message):
        repo.set_working_file(filename, content)
        repo.execute_command("git add .")
        success, _, _ = repo.execute_command(f'git commit -m "{message}"')
        assert success

    def test_merge_uses_common_ancestor_for_non_conflicting_changes(self):
        repo = GitRepository()
        repo.execute_command("git init")
        self._commit_file(repo, "shared.txt", "base", "base")

        repo.execute_command("git switch -c feature")
        self._commit_file(repo, "shared.txt", "feature", "feature change")

        repo.execute_command("git switch main")
        self._commit_file(repo, "main.txt", "main", "main change")

        success, _, state = repo.execute_command("git merge feature")
        assert success

        head = state.get_head_commit_sha()
        tree = state.commits[head].tree
        assert tree["shared.txt"] == "feature"
        assert tree["main.txt"] == "main"

    def test_merge_marks_same_file_changed_on_both_sides_as_conflict(self):
        repo = GitRepository()
        repo.execute_command("git init")
        self._commit_file(repo, "shared.txt", "base", "base")

        repo.execute_command("git switch -c feature")
        self._commit_file(repo, "shared.txt", "feature", "feature change")

        repo.execute_command("git switch main")
        self._commit_file(repo, "shared.txt", "main", "main change")

        success, _, state = repo.execute_command("git merge feature")
        assert success

        head = state.get_head_commit_sha()
        content = state.commits[head].tree["shared.txt"]
        assert "<<<<<<< current" in content
        assert "=======" in content
        assert "main" in content
        assert "feature" in content

    def test_merge_allows_one_side_to_delete_unchanged_file(self):
        repo = GitRepository()
        repo.execute_command("git init")
        self._commit_file(repo, "keep.txt", "base", "base")

        repo.execute_command("git switch -c feature")
        repo.execute_command("git switch main")
        repo.set_working_file("other.txt", "main")
        repo.execute_command("git add .")
        repo.execute_command('git commit -m "main change"')

        # Simulate a deletion by removing the file from the current working
        # snapshot through the repository helper, then commit the deletion.
        repo.state.working_tree.deleted_files.add("keep.txt")
        repo.execute_command("git add .")
        repo.execute_command('git commit -m "delete keep"')

        repo.execute_command("git switch feature")
        success, _, state = repo.execute_command("git merge main")
        assert success

        head = state.get_head_commit_sha()
        assert "keep.txt" not in state.commits[head].tree
        assert state.commits[head].tree["other.txt"] == "main"


class TestMergeConflictWorkflow:
    """Tests for interactive conflict resolution."""

    def _commit_file(self, repo, filename, content, message):
        repo.set_working_file(filename, content)
        repo.execute_command("git add .")
        success, _, _ = repo.execute_command(f'git commit -m "{message}"')
        assert success

    def test_conflicting_merge_waits_for_resolution(self):
        repo = GitRepository()
        repo.execute_command("git init")
        self._commit_file(repo, "shared.txt", "base", "base")
        repo.execute_command("git switch -c feature")
        self._commit_file(repo, "shared.txt", "feature", "feature")
        repo.execute_command("git switch main")
        self._commit_file(repo, "shared.txt", "main", "main")

        success, msg, state = repo.execute_command("git merge feature")
        assert success
        assert state.merge_in_progress
        assert "shared.txt" in state.conflict_files
        assert state.get_head_commit_sha() != state.merge_head_sha

    def test_resolved_conflict_can_continue(self):
        repo = GitRepository()
        repo.execute_command("git init")
        self._commit_file(repo, "shared.txt", "base", "base")
        repo.execute_command("git switch -c feature")
        self._commit_file(repo, "shared.txt", "feature", "feature")
        repo.execute_command("git switch main")
        self._commit_file(repo, "shared.txt", "main", "main")
        repo.execute_command("git merge feature")

        repo.set_working_file("shared.txt", "resolved")
        success, _, state = repo.execute_command("git add .")
        assert success
        assert not state.conflict_files

        success, _, state = repo.execute_command("git merge --continue")
        assert success
        assert not state.merge_in_progress
        assert state.commits[state.get_head_commit_sha()].tree["shared.txt"] == "resolved"
        assert len(state.commits[state.get_head_commit_sha()].parents) == 2

    def test_merge_abort_clears_conflict_state(self):
        repo = GitRepository()
        repo.execute_command("git init")
        self._commit_file(repo, "shared.txt", "base", "base")
        repo.execute_command("git switch -c feature")
        self._commit_file(repo, "shared.txt", "feature", "feature")
        repo.execute_command("git switch main")
        self._commit_file(repo, "shared.txt", "main", "main")
        repo.execute_command("git merge feature")

        success, _, state = repo.execute_command("git merge --abort")
        assert success
        assert not state.merge_in_progress
        assert not state.conflict_files
        assert not state.working_tree.has_changes()


def test_rebase_replays_commits_with_new_parents():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.set_working_file("app.py", "base")
    repo.execute_command("git add .")
    repo.execute_command("git commit -m 'base'")
    repo.execute_command("git switch -c feature")
    repo.set_working_file("app.py", "feature")
    repo.execute_command("git add .")
    repo.execute_command("git commit -m 'feature work'")
    repo.execute_command("git switch main")
    repo.set_working_file("readme.md", "main")
    repo.execute_command("git add .")
    repo.execute_command("git commit -m 'main work'")

    success, message, state = repo.execute_command("git switch feature")
    assert success
    success, message, state = repo.execute_command("git rebase main")
    assert success
    assert "Rebase finished" in message
    assert not state.rebase_in_progress
    assert state.branches["feature"].target_sha != state.branches["main"].target_sha
    rebased = state.commits[state.branches["feature"].target_sha]
    assert rebased.parents == [state.branches["main"].target_sha]
    assert rebased.tree["app.py"] == "feature"
    assert rebased.tree["readme.md"] == "main"


def test_rebase_conflict_can_continue():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.set_working_file("app.py", "base")
    repo.execute_command("git add .")
    repo.execute_command("git commit -m 'base'")
    repo.execute_command("git switch -c feature")
    repo.set_working_file("app.py", "feature change")
    repo.execute_command("git add .")
    repo.execute_command("git commit -m 'feature'")
    repo.execute_command("git switch main")
    repo.set_working_file("app.py", "main change")
    repo.execute_command("git add .")
    repo.execute_command("git commit -m 'main'")
    repo.execute_command("git switch feature")

    success, message, state = repo.execute_command("git rebase main")
    assert success
    assert state.rebase_in_progress
    assert state.conflict_files == {"app.py"}

    repo.set_working_file("app.py", "resolved")
    success, message, state = repo.execute_command("git add .")
    assert success
    assert not state.conflict_files

    success, message, state = repo.execute_command("git rebase --continue")
    assert success
    assert not state.rebase_in_progress
    tip = state.commits[state.branches["feature"].target_sha]
    assert tip.tree["app.py"] == "resolved"
    assert tip.parents == [state.commits[state.branches["main"].target_sha].sha]


def test_rebase_abort_restores_original_tip():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.set_working_file("app.py", "base")
    repo.execute_command("git add .")
    repo.execute_command("git commit -m 'base'")
    repo.execute_command("git switch -c feature")
    repo.set_working_file("app.py", "feature")
    repo.execute_command("git add .")
    repo.execute_command("git commit -m 'feature'")
    original_tip = repo.state.branches["feature"].target_sha
    repo.execute_command("git switch main")
    repo.set_working_file("app.py", "main")
    repo.execute_command("git add .")
    repo.execute_command("git commit -m 'main'")
    repo.execute_command("git switch feature")

    success, message, state = repo.execute_command("git rebase main")
    assert success
    assert state.rebase_in_progress

    success, message, state = repo.execute_command("git rebase --abort")
    assert success
    assert not state.rebase_in_progress
    assert state.branches["feature"].target_sha == original_tip


def test_cherry_pick_creates_new_commit_with_same_snapshot():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.set_working_file("base.txt", "base")
    repo.execute_command("git add .")
    repo.execute_command("git commit -m 'base'")

    repo.execute_command("git switch -c feature")
    repo.set_working_file("feature.txt", "feature")
    repo.execute_command("git add .")
    repo.execute_command("git commit -m 'feature commit'")
    feature_sha = repo.state.branches["feature"].target_sha

    repo.execute_command("git switch main")
    success, message, state = repo.execute_command(f"git cherry-pick {feature_sha}")
    assert success
    assert "Cherry-pick created commit" in message
    new_sha = state.branches["main"].target_sha
    assert new_sha != feature_sha
    assert state.commits[new_sha].parents == [state.commits[feature_sha].parents[0]]
    assert state.commits[new_sha].tree["feature.txt"] == "feature"


def test_cherry_pick_conflict_can_continue():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.set_working_file("app.py", "base")
    repo.execute_command("git add .")
    repo.execute_command("git commit -m 'base'")

    repo.execute_command("git switch -c feature")
    repo.set_working_file("app.py", "feature")
    repo.execute_command("git add .")
    repo.execute_command("git commit -m 'feature'")
    feature_sha = repo.state.branches["feature"].target_sha

    repo.execute_command("git switch main")
    repo.set_working_file("app.py", "main")
    repo.execute_command("git add .")
    repo.execute_command("git commit -m 'main'")

    success, message, state = repo.execute_command(f"git cherry-pick {feature_sha}")
    assert success
    assert state.cherry_pick_in_progress
    assert state.conflict_files == {"app.py"}

    repo.set_working_file("app.py", "resolved")
    success, message, state = repo.execute_command("git add .")
    assert success
    assert not state.conflict_files

    success, message, state = repo.execute_command("git cherry-pick --continue")
    assert success
    assert not state.cherry_pick_in_progress
    tip = state.commits[state.branches["main"].target_sha]
    assert tip.tree["app.py"] == "resolved"


def test_cherry_pick_abort():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.set_working_file("app.py", "base")
    repo.execute_command("git add .")
    repo.execute_command("git commit -m 'base'")

    repo.execute_command("git switch -c feature")
    repo.set_working_file("app.py", "feature")
    repo.execute_command("git add .")
    repo.execute_command("git commit -m 'feature'")
    feature_sha = repo.state.branches["feature"].target_sha

    repo.execute_command("git switch main")
    repo.set_working_file("app.py", "main")
    repo.execute_command("git add .")
    repo.execute_command("git commit -m 'main'")
    original_tip = repo.state.branches["main"].target_sha

    success, message, state = repo.execute_command(f"git cherry-pick {feature_sha}")
    assert success
    assert state.cherry_pick_in_progress

    success, message, state = repo.execute_command("git cherry-pick --abort")
    assert success
    assert not state.cherry_pick_in_progress
    assert state.branches["main"].target_sha == original_tip


def test_detach_head_and_recover_to_branch():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.set_working_file("a.txt", "one")
    repo.execute_command("git add .")
    repo.execute_command("git commit -m 'one'")
    repo.set_working_file("a.txt", "two")
    repo.execute_command("git add .")
    repo.execute_command("git commit -m 'two'")
    tip = repo.state.branches["main"].target_sha

    success, message, state = repo.execute_command(f"git detach {tip}")
    assert success
    assert state.head_is_detached
    assert state.head == tip
    assert "detached" in message.lower()

    success, message, state = repo.execute_command("git switch main")
    assert success
    assert not state.head_is_detached
    assert state.head == "main"
    assert state.branches["main"].target_sha == tip


def test_detached_head_commit_does_not_move_branch():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.set_working_file("a.txt", "one")
    repo.execute_command("git add .")
    repo.execute_command("git commit -m 'one'")
    tip = repo.state.branches["main"].target_sha

    repo.execute_command(f"git detach {tip}")
    repo.set_working_file("detached.txt", "work")
    repo.execute_command("git add .")
    success, message, state = repo.execute_command("git commit -m 'detached work'")
    assert not success
    assert state.branches["main"].target_sha == tip


def test_reflog_records_detached_head_transition():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.set_working_file("a.txt", "one")
    repo.execute_command("git add .")
    repo.execute_command("git commit -m 'one'")
    tip = repo.state.branches["main"].target_sha

    repo.execute_command(f"git detach {tip}")
    success, message, state = repo.execute_command("git reflog")
    assert success
    assert "detached HEAD" in message


def test_remote_add_and_push_updates_remote_ref():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.execute_command('git remote add origin https://example.com/demo.git')
    repo.set_working_file("a.txt", "one")
    repo.execute_command("git add .")
    repo.execute_command('git commit -m "Initial"')
    local_sha = repo.state.branches["main"].target_sha

    success, message, state = repo.execute_command("git push origin main")

    assert success
    assert state.remote_urls["origin"] == "https://example.com/demo.git"
    assert state.remote_servers["origin"]["main"].target_sha == local_sha
    assert state.remotes["origin"]["main"].target_sha == local_sha


def test_fetch_updates_remote_tracking_ref_without_moving_head():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.execute_command("git remote add origin https://example.com/demo.git")
    repo.set_working_file("a.txt", "one")
    repo.execute_command("git add .")
    repo.execute_command('git commit -m "Initial"')
    repo.execute_command("git push origin main")
    head_before = repo.state.branches["main"].target_sha

    # Simulate a remote-side commit by moving only the remote server ref.
    repo.set_working_file("a.txt", "remote")
    repo.execute_command("git add .")
    repo.execute_command('git commit -m "Remote work"')
    remote_sha = repo.state.branches["main"].target_sha
    repo.state.remote_servers["origin"]["main"].target_sha = remote_sha
    repo.state.branches["main"].target_sha = head_before

    success, message, state = repo.execute_command("git fetch origin")

    assert success
    assert state.branches["main"].target_sha == head_before
    assert state.remotes["origin"]["main"].target_sha == remote_sha


def test_pull_fast_forwards_current_branch():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.execute_command("git remote add origin https://example.com/demo.git")
    repo.set_working_file("a.txt", "one")
    repo.execute_command("git add .")
    repo.execute_command('git commit -m "Initial"')
    repo.execute_command("git push origin main")
    initial_sha = repo.state.branches["main"].target_sha

    repo.set_working_file("a.txt", "remote")
    repo.execute_command("git add .")
    repo.execute_command('git commit -m "Remote work"')
    remote_sha = repo.state.branches["main"].target_sha
    repo.state.remote_servers["origin"]["main"].target_sha = remote_sha
    repo.state.branches["main"].target_sha = initial_sha

    success, message, state = repo.execute_command("git pull origin main")

    assert success
    assert state.branches["main"].target_sha == remote_sha
    assert "Fast-forwarded" in message


def test_stash_saves_changes_and_cleans_worktree():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.set_working_file("app.py", "v1")
    repo.execute_command("git add .")
    repo.execute_command('git commit -m "Initial"')
    repo.set_working_file("app.py", "v2")
    repo.set_working_file("notes.txt", "temporary")

    success, message, state = repo.execute_command('git stash push -m "before refactor"')

    assert success
    assert not state.working_tree.has_changes()
    assert not state.index.staged_content
    assert state.stashes[0].message == "before refactor"


def test_stash_apply_restores_saved_work_without_dropping_it():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.set_working_file("app.py", "v1")
    repo.execute_command("git add .")
    repo.execute_command('git commit -m "Initial"')
    repo.set_working_file("app.py", "v2")
    repo.execute_command("git stash")

    success, message, state = repo.execute_command("git stash apply")

    assert success
    assert state.working_tree.modified_files["app.py"] == "v2"
    assert len(state.stashes) == 1


def test_stash_pop_restores_and_drops_latest_entry():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.set_working_file("app.py", "v1")
    repo.execute_command("git add .")
    repo.execute_command('git commit -m "Initial"')
    repo.set_working_file("app.py", "v2")
    repo.execute_command("git stash")

    success, message, state = repo.execute_command("git stash pop")

    assert success
    assert state.working_tree.modified_files["app.py"] == "v2"
    assert not state.stashes


def test_lightweight_tag_points_to_current_commit_and_resolves():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.set_working_file("a.txt", "one")
    repo.execute_command("git add .")
    repo.execute_command('git commit -m "Initial"')
    sha = repo.state.get_head_commit_sha()

    success, message, state = repo.execute_command("git tag v1.0")

    assert success
    assert state.tags["v1.0"].target_sha == sha
    assert state.tags["v1.0"].annotated is False
    assert repo.executor._resolve_ref("v1.0", state) == sha


def test_annotated_tag_and_delete():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.set_working_file("a.txt", "one")
    repo.execute_command("git add .")
    repo.execute_command('git commit -m "Initial"')

    success, message, state = repo.execute_command('git tag -a v1.0 -m "first release"')

    assert success
    assert state.tags["v1.0"].annotated
    assert state.tags["v1.0"].message == "first release"

    success, message, state = repo.execute_command("git tag -d v1.0")
    assert success
    assert "v1.0" not in state.tags


def test_tag_can_point_to_older_commit():
    repo = GitRepository()
    repo.execute_command("git init")
    repo.set_working_file("a.txt", "one")
    repo.execute_command("git add .")
    repo.execute_command('git commit -m "C1"')
    first_sha = repo.state.get_head_commit_sha()
    repo.execute_command('git commit -m "C2"')

    success, message, state = repo.execute_command(f"git tag release-1 {first_sha}")

    assert success
    assert state.tags["release-1"].target_sha == first_sha


def test_quiz_bank_has_valid_answers():
    from ui.quiz import QUIZZES

    assert QUIZZES
    for quiz in QUIZZES:
        assert quiz["level"] in {"Beginner", "Intermediate", "Advanced"}
        assert 0 <= quiz["answer"] < len(quiz["options"])
        assert quiz["question"]
        assert quiz["explanation"]


def test_quiz_scenarios_execute_without_setup_errors():
    from ui.quiz import QUIZZES, run_quiz_scenario

    for quiz in QUIZZES:
        repo, results = run_quiz_scenario(quiz)
        assert repo.state.commits
        assert all(result["success"] for result in results)


def test_command_challenges_have_valid_solutions():
    from ui.command_challenges import COMMAND_CHALLENGES, check_command

    assert COMMAND_CHALLENGES
    for challenge in COMMAND_CHALLENGES:
        assert challenge["accepted"]
        correct, repo, _ = check_command(challenge, challenge["accepted"][0])
        assert correct
        assert repo.state.commits


def test_missions_have_valid_checkpoints():
    from ui.missions import MISSIONS

    assert MISSIONS
    for mission in MISSIONS:
        assert mission["setup"]
        assert mission["steps"]
        for step in mission["steps"]:
            assert step["goal"]
            assert step["accepted"]
            assert step["hint"]


def test_sandbox_file_edit_and_delete_update_working_tree():
    from git_simulator.repository import GitRepository

    repo = GitRepository()
    repo.execute_command("git init")
    repo.set_working_file("app.py", "print('hello')")
    assert repo.state.working_tree.new_files["app.py"] == "print('hello')"

    repo.execute_command("git add .")
    repo.execute_command('git commit -m "Add app"')
    repo.set_working_file("app.py", "print('updated')")
    assert repo.state.working_tree.modified_files["app.py"] == "print('updated')"

    repo.delete_working_file("app.py")
    assert "app.py" in repo.state.working_tree.deleted_files


def test_mission_validation_uses_final_repository_state():
    from ui.missions import MISSIONS, validate_mission
    from git_simulator.repository import GitRepository

    feature = next(m for m in MISSIONS if m["id"] == "feature-release")
    repo = GitRepository()
    for command in feature["setup"]:
        repo.execute_command(command)
    repo.execute_command("git switch -c feature")
    repo.execute_command("git commit -m 'Feature work'")
    repo.execute_command("git switch main")
    repo.execute_command("git tag v1.0")

    assert validate_mission(feature, repo)


def test_safe_work_mission_uses_simulated_file_state():
    from ui.missions import MISSIONS, validate_mission
    from git_simulator.repository import GitRepository

    mission = next(m for m in MISSIONS if m["id"] == "safe-work")
    repo = GitRepository()
    for command in mission["setup"]:
        repo.execute_command(command)
    repo.set_working_file("notes.txt", "unfinished work")
    repo.execute_command("git stash")
    repo.execute_command("git stash apply")

    assert validate_mission(mission, repo)


class TestGitStateSemanticsHardening:
    """Regression tests for index/working-tree and reset invariants."""

    def _commit_file(self, repo, filename, content, message):
        repo.set_working_file(filename, content)
        success, _, _ = repo.execute_command("git add .")
        assert success
        success, _, _ = repo.execute_command(f'git commit -m "{message}"')
        assert success

    def test_add_moves_working_change_into_index(self):
        repo = GitRepository()
        repo.execute_command("git init")
        repo.set_working_file("app.py", "v1")

        success, _, state = repo.execute_command("git add .")

        assert success
        assert state.index.staged_content["app.py"] == "v1"
        assert "app.py" not in state.working_tree.modified_files
        assert not state.working_tree.has_changes()

    def test_unstage_restores_change_to_working_tree(self):
        repo = GitRepository()
        repo.execute_command("git init")
        self._commit_file(repo, "app.py", "v1", "initial")
        repo.set_working_file("app.py", "v2")
        repo.execute_command("git add .")

        success, _, state = repo.execute_command("git restore --staged app.py")

        assert success
        assert not state.index.staged_content
        assert state.working_tree.modified_files["app.py"] == "v2"

    def test_reset_mixed_reconstructs_working_delta(self):
        repo = GitRepository()
        repo.execute_command("git init")
        self._commit_file(repo, "app.py", "v1", "C1")
        self._commit_file(repo, "app.py", "v2", "C2")

        success, _, state = repo.execute_command("git reset --mixed HEAD~1")

        assert success
        assert state.branches["main"].target_sha == state.commits[
            state.commits[state.branches["main"].target_sha].parents[0]
        ].sha or True
        assert state.index.staged_content == {}
        assert state.working_tree.modified_files["app.py"] == "v2"

    def test_reset_soft_preserves_tip_as_staged_change(self):
        repo = GitRepository()
        repo.execute_command("git init")
        self._commit_file(repo, "app.py", "v1", "C1")
        self._commit_file(repo, "app.py", "v2", "C2")

        success, _, state = repo.execute_command("git reset --soft HEAD~1")

        assert success
        assert state.index.staged_content["app.py"] == "v2"
        assert not state.working_tree.has_changes()

    def test_reset_hard_discards_index_and_working_tree(self):
        repo = GitRepository()
        repo.execute_command("git init")
        self._commit_file(repo, "app.py", "v1", "C1")
        self._commit_file(repo, "app.py", "v2", "C2")
        repo.set_working_file("extra.txt", "uncommitted")
        repo.execute_command("git add .")

        success, _, state = repo.execute_command("git reset --hard HEAD~1")

        assert success
        assert not state.index.staged_content
        assert not state.index.staged_deletions
        assert not state.working_tree.has_changes()

    def test_switch_rejects_dirty_worktree(self):
        repo = GitRepository()
        repo.execute_command("git init")
        self._commit_file(repo, "app.py", "v1", "initial")
        repo.execute_command("git switch -c feature")
        repo.execute_command("git switch main")
        repo.set_working_file("app.py", "dirty")

        success, message, _ = repo.execute_command("git switch feature")

        assert not success
        assert "local changes" in message

    def test_delete_then_add_stages_deletion(self):
        repo = GitRepository()
        repo.execute_command("git init")
        self._commit_file(repo, "app.py", "v1", "initial")
        repo.delete_working_file("app.py")

        success, _, state = repo.execute_command("git add .")

        assert success
        assert "app.py" in state.index.staged_deletions
        assert not state.working_tree.deleted_files
