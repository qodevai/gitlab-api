"""Unit tests for the gitlab-client library."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from qodev_gitlab_api import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    GitLabClient,
    GitLabError,
    NotFoundError,
)


class TestClientInit:
    """Tests for GitLabClient initialization."""

    def test_init_requires_token(self) -> None:
        """Missing token raises ConfigurationError."""
        with (
            patch.dict("os.environ", {"GITLAB_TOKEN": ""}, clear=False),
            pytest.raises(ConfigurationError, match="GITLAB_TOKEN"),
        ):
            GitLabClient(token=None, validate=False)

    def test_init_with_env_token(self, mock_env_vars: dict, mock_httpx_client: MagicMock) -> None:
        """Token is read from env when not provided."""
        client = GitLabClient(validate=False)
        assert client.token == mock_env_vars["GITLAB_TOKEN"]
        assert client.base_url == mock_env_vars["GITLAB_URL"]

    def test_init_with_explicit_token(self, mock_env_vars: dict, mock_httpx_client: MagicMock) -> None:
        """Explicit token overrides env."""
        client = GitLabClient(token="explicit-token", validate=False)
        assert client.token == "explicit-token"

    def test_init_invalid_url(self) -> None:
        """Invalid URL raises ConfigurationError."""
        with (
            patch.dict("os.environ", {"GITLAB_TOKEN": "test", "GITLAB_URL": "invalid-url"}, clear=True),
            pytest.raises(ConfigurationError, match="must start with http"),
        ):
            GitLabClient(validate=False)

    def test_init_strips_trailing_slash(self, mock_httpx_client: MagicMock) -> None:
        """Trailing slash is stripped from base URL."""
        with patch.dict("os.environ", {"GITLAB_TOKEN": "test", "GITLAB_URL": "https://gitlab.com/"}, clear=True):
            client = GitLabClient(validate=False)
            assert client.base_url == "https://gitlab.com"

    def test_default_url_is_gitlab_com(self, mock_httpx_client: MagicMock) -> None:
        """Default URL is https://gitlab.com when not set."""
        with patch.dict("os.environ", {"GITLAB_TOKEN": "test"}, clear=True):
            client = GitLabClient(validate=False)
            assert client.base_url == "https://gitlab.com"


class TestExceptionHierarchy:
    """Tests for the exception hierarchy."""

    def test_api_error_is_gitlab_error(self) -> None:
        assert issubclass(APIError, GitLabError)

    def test_not_found_error_is_gitlab_error(self) -> None:
        assert issubclass(NotFoundError, GitLabError)

    def test_auth_error_is_gitlab_error(self) -> None:
        assert issubclass(AuthenticationError, GitLabError)

    def test_config_error_is_gitlab_error(self) -> None:
        assert issubclass(ConfigurationError, GitLabError)

    def test_api_error_has_status_code(self) -> None:
        e = APIError("msg", status_code=500, response_body="body")
        assert e.status_code == 500
        assert e.response_body == "body"
        assert str(e) == "msg"

    def test_not_found_error_has_status_code(self) -> None:
        e = NotFoundError("gone", status_code=404)
        assert e.status_code == 404
        assert str(e) == "gone"


class TestHTTPMethods:
    """Tests for HTTP request methods."""

    def test_get_success(self, mock_env_vars: dict, mock_httpx_client: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"version": "16.0.0"}
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        client = GitLabClient(validate=False)
        result = client.get("/version")

        assert result == {"version": "16.0.0"}
        mock_httpx_client.get.assert_called_once_with("/version", params=None)

    def test_get_404_raises_not_found(self, mock_env_vars: dict, mock_httpx_client: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found", request=MagicMock(), response=mock_response
        )
        mock_httpx_client.get.return_value = mock_response

        client = GitLabClient(validate=False)
        with pytest.raises(NotFoundError):
            client.get("/nonexistent")

    def test_get_401_raises_auth_error(self, mock_env_vars: dict, mock_httpx_client: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )
        mock_httpx_client.get.return_value = mock_response

        client = GitLabClient(validate=False)
        with pytest.raises(AuthenticationError):
            client.get("/protected")

    def test_get_500_raises_api_error(self, mock_env_vars: dict, mock_httpx_client: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )
        mock_httpx_client.get.return_value = mock_response

        client = GitLabClient(validate=False)
        with pytest.raises(APIError) as exc_info:
            client.get("/error")
        assert exc_info.value.status_code == 500


class TestURLEncoding:
    """Tests for project ID encoding."""

    def test_encode_simple_id(self) -> None:
        assert GitLabClient._encode_project_id("123") == "123"

    def test_encode_path(self) -> None:
        assert GitLabClient._encode_project_id("group/project") == "group%2Fproject"

    def test_encode_nested_path(self) -> None:
        assert GitLabClient._encode_project_id("org/group/project") == "org%2Fgroup%2Fproject"


class TestPagination:
    """Tests for paginated requests."""

    def test_single_page(self, mock_env_vars: dict, mock_httpx_client: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": 1}, {"id": 2}]
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {}
        mock_httpx_client.get.return_value = mock_response

        client = GitLabClient(validate=False)
        results = client.get_paginated("/projects")

        assert len(results) == 2

    def test_multiple_pages(self, mock_env_vars: dict, mock_httpx_client: MagicMock) -> None:
        resp1 = MagicMock()
        resp1.json.return_value = [{"id": 1}]
        resp1.raise_for_status = MagicMock()
        resp1.headers = {"x-next-page": "2"}

        resp2 = MagicMock()
        resp2.json.return_value = [{"id": 2}]
        resp2.raise_for_status = MagicMock()
        resp2.headers = {}

        mock_httpx_client.get.side_effect = [resp1, resp2]

        client = GitLabClient(validate=False)
        results = client.get_paginated("/projects")

        assert len(results) == 2
        assert mock_httpx_client.get.call_count == 2

    def test_respects_max_pages(self, mock_env_vars: dict, mock_httpx_client: MagicMock) -> None:
        def make_resp():
            r = MagicMock()
            r.json.return_value = [{"id": 1}]
            r.raise_for_status = MagicMock()
            r.headers = {"x-next-page": "999"}
            return r

        mock_httpx_client.get.side_effect = [make_resp() for _ in range(10)]

        client = GitLabClient(validate=False)
        results = client.get_paginated("/projects", max_pages=3)

        assert len(results) == 3
        assert mock_httpx_client.get.call_count == 3

    def test_empty_results(self, mock_env_vars: dict, mock_httpx_client: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {}
        mock_httpx_client.get.return_value = mock_response

        client = GitLabClient(validate=False)
        assert client.get_paginated("/projects") == []


class TestProjectMethods:
    """Tests for project-related methods."""

    def test_get_project(self, mock_env_vars: dict, mock_httpx_client: MagicMock, sample_project: dict) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = sample_project
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        client = GitLabClient(validate=False)
        result = client.get_project("group/test-project")

        assert result["name"] == "test-project"
        call_args = mock_httpx_client.get.call_args
        assert "group%2Ftest-project" in call_args[0][0]


class TestMergeRequestMethods:
    """Tests for MR operations."""

    def test_get_merge_request(
        self, mock_env_vars: dict, mock_httpx_client: MagicMock, sample_merge_request: dict
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = sample_merge_request
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        client = GitLabClient(validate=False)
        result = client.get_merge_request("123", 1)

        assert result["title"] == "Add new feature"
        assert result["iid"] == 1

    def test_close_mr(self, mock_env_vars: dict, mock_httpx_client: MagicMock, sample_merge_request: dict) -> None:
        closed_mr = {**sample_merge_request, "state": "closed"}
        mock_response = MagicMock()
        mock_response.json.return_value = closed_mr
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.put.return_value = mock_response

        client = GitLabClient(validate=False)
        result = client.close_mr("123", 1)

        assert result["state"] == "closed"
        call_args = mock_httpx_client.put.call_args
        assert "123/merge_requests/1" in call_args[0][0]
        assert call_args[1]["json"]["state_event"] == "close"

    def test_create_mr_note(self, mock_env_vars: dict, mock_httpx_client: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1, "body": "LGTM"}
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        client = GitLabClient(validate=False)
        result = client.create_mr_note("123", 1, "LGTM")

        assert result["body"] == "LGTM"
        call_args = mock_httpx_client.post.call_args
        assert "123/merge_requests/1/notes" in call_args[0][0]


class TestJobMethods:
    """Tests for job operations."""

    def test_retry_job(self, mock_env_vars: dict, mock_httpx_client: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1002, "status": "pending"}
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        client = GitLabClient(validate=False)
        result = client.retry_job("123", 1001)

        assert result["id"] == 1002
        assert result["status"] == "pending"
        call_args = mock_httpx_client.post.call_args
        assert "123/jobs/1001/retry" in call_args[0][0]

    def test_retry_job_not_found(self, mock_env_vars: dict, mock_httpx_client: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found", request=MagicMock(), response=mock_response
        )
        mock_httpx_client.post.return_value = mock_response

        client = GitLabClient(validate=False)
        with pytest.raises(NotFoundError):
            client.retry_job("123", 99999)


class TestFileUpload:
    """Tests for file upload operations."""

    def test_upload_from_path(self, mock_env_vars: dict, mock_httpx_client: MagicMock, tmp_path) -> None:
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"fake image content")

        upload_response = {
            "alt": "test",
            "url": "/uploads/abc/test.png",
            "markdown": "![test](/uploads/abc/test.png)",
        }

        with patch("qodev_gitlab_api._files.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = upload_response
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            client = GitLabClient(validate=False)
            result = client.upload_file("123", {"path": str(test_file)})

            assert result["url"] == "/uploads/abc/test.png"
            mock_post.assert_called_once()

    def test_upload_from_base64(self, mock_env_vars: dict, mock_httpx_client: MagicMock) -> None:
        import base64

        upload_response = {"alt": "img", "url": "/uploads/def/img.png", "markdown": "![img](...)"}

        with patch("qodev_gitlab_api._files.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = upload_response
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            client = GitLabClient(validate=False)
            b64 = base64.b64encode(b"data").decode()
            result = client.upload_file("123", {"base64": b64, "filename": "img.png"})

            assert result["url"] == "/uploads/def/img.png"

    def test_upload_invalid_base64_raises(self, mock_env_vars: dict, mock_httpx_client: MagicMock) -> None:
        client = GitLabClient(validate=False)
        with pytest.raises(ValueError, match="Invalid base64"):
            client.upload_file("123", {"base64": "not-valid!!!", "filename": "test.png"})

    def test_upload_file_not_found_raises(self, mock_env_vars: dict, mock_httpx_client: MagicMock) -> None:
        client = GitLabClient(validate=False)
        with pytest.raises(FileNotFoundError):
            client.upload_file("123", {"path": "/nonexistent/file.png"})


class TestVariableMethods:
    """Tests for CI/CD variable operations."""

    def test_list_project_variables(self, mock_env_vars: dict, mock_httpx_client: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"key": "VAR1", "variable_type": "env_var", "protected": False, "masked": False},
            {"key": "VAR2", "variable_type": "env_var", "protected": True, "masked": True},
        ]
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {}
        mock_httpx_client.get.return_value = mock_response

        client = GitLabClient(validate=False)
        result = client.list_project_variables("123")

        assert len(result) == 2
        # Values should be sanitized (removed)
        assert "value" not in result[0]

    def test_get_project_variable(self, mock_env_vars: dict, mock_httpx_client: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "key": "API_KEY",
            "value": "secret",
            "variable_type": "env_var",
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        client = GitLabClient(validate=False)
        result = client.get_project_variable("123", "API_KEY")

        assert result["key"] == "API_KEY"
        # get_project_variable returns raw response (sanitization is in list_project_variables)
        assert result["value"] == "secret"
