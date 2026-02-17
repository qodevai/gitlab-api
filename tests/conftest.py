"""Shared test fixtures for gitlab-client tests."""

import os
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_env_vars() -> Generator[dict[str, str], None, None]:
    """Set up test environment variables."""
    env = {
        "GITLAB_TOKEN": "test-token-12345",
        "GITLAB_URL": "https://gitlab.example.com",
    }
    with patch.dict(os.environ, env, clear=False):
        yield env


@pytest.fixture
def mock_httpx_client() -> Generator[MagicMock, None, None]:
    """Mock httpx.Client at the module level where it's instantiated."""
    with patch("gitlab_client._base.httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_project() -> dict:
    """Sample GitLab project response."""
    return {
        "id": 123,
        "name": "test-project",
        "path_with_namespace": "group/test-project",
        "web_url": "https://gitlab.example.com/group/test-project",
        "default_branch": "main",
    }


@pytest.fixture
def sample_merge_request() -> dict:
    """Sample GitLab merge request response."""
    return {
        "id": 456,
        "iid": 1,
        "title": "Add new feature",
        "state": "opened",
        "source_branch": "feature-branch",
        "target_branch": "main",
        "author": {"id": 1, "username": "testuser", "name": "Test User"},
        "web_url": "https://gitlab.example.com/group/test-project/-/merge_requests/1",
    }
