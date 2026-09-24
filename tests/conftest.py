"""
Pytest configuration and fixtures.
"""

import pytest
from git_simulator.repository import GitRepository


@pytest.fixture
def fresh_repo():
    """Provide a fresh, uninitialized repository for testing."""
    return GitRepository()


@pytest.fixture
def initialized_repo():
    """Provide an initialized repository with one initial commit."""
    repo = GitRepository()
    repo.execute_command("git init")
    repo.execute_command('git commit -m "Initial commit"')
    return repo


@pytest.fixture
def branched_repo():
    """Provide a repository with main and feature branches."""
    repo = GitRepository()
    repo.execute_command("git init")
    repo.execute_command('git commit -m "Initial"')
    repo.execute_command("git switch -c feature")
    repo.execute_command('git commit -m "Feature work"')
    repo.execute_command("git switch main")
    return repo
