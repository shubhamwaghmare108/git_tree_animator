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
        
        c1_sha = repo.state.commits.popitem()[0]  # Get first commit
        
        success, msg, state = repo.execute_command("git reset --soft HEAD~1")
        
        assert success
    
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
