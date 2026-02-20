"""Base GitLab client mixin with HTTP primitives."""

import logging
import os
from typing import Any
from urllib.parse import quote

import httpx
from dotenv import load_dotenv

from qodev_gitlab_api.exceptions import APIError, AuthenticationError, ConfigurationError, NotFoundError

load_dotenv()

logger = logging.getLogger(__name__)


def _raise_for_status(e: httpx.HTTPStatusError) -> None:
    """Convert httpx HTTP errors into typed exceptions."""
    status = e.response.status_code
    body = e.response.text[:500] if e.response.text else ""
    if status == 401:
        raise AuthenticationError(f"Authentication failed: {body}") from e
    if status == 404:
        raise NotFoundError(f"Not found: {body}", status_code=status) from e
    raise APIError(f"API error {status}: {body}", status_code=status, response_body=body) from e


class BaseClientMixin:
    """Base mixin providing HTTP primitives and initialization."""

    token: str | None
    base_url: str
    api_url: str
    client: httpx.Client

    def __init__(
        self, token: str | None = None, base_url: str | None = None, validate: bool = True, lazy: bool = False
    ):
        self.token = token or os.getenv("GITLAB_TOKEN")
        self.base_url = (
            base_url or os.getenv("GITLAB_BASE_URL") or os.getenv("GITLAB_URL") or "https://gitlab.com"
        ).rstrip("/")

        if not lazy:
            self._validate_configuration()

        self.api_url = f"{self.base_url}/api/v4"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.token:
            headers["PRIVATE-TOKEN"] = self.token
        self.client = httpx.Client(
            base_url=self.api_url,
            headers=headers,
            timeout=30.0,
        )

        if validate and not lazy:
            self._test_connectivity()
        else:
            logger.info(f"GitLab client initialized for {self.base_url} (validation skipped)")

    def _validate_configuration(self) -> None:
        if not self.token:
            raise ConfigurationError(
                "GITLAB_TOKEN environment variable is required. Set it in your .env file or environment."
            )
        if not self.base_url.startswith(("http://", "https://")):
            raise ConfigurationError(f"GITLAB_URL must start with http:// or https://, got: {self.base_url}")

    def _test_connectivity(self) -> None:
        try:
            version_info = self.get("/version")
            logger.info(f"Connected to GitLab {version_info.get('version', 'unknown')} at {self.base_url}")
        except (AuthenticationError, APIError, NotFoundError):
            raise
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
        except httpx.RequestError as e:
            raise ConfigurationError(f"Cannot connect to GitLab at {self.base_url}. Check your GITLAB_URL.") from e

    @staticmethod
    def _encode_project_id(project_id: str) -> str:
        return quote(project_id, safe="")

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """GET request to GitLab API."""
        try:
            logger.debug(f"GET {endpoint} with params={params}")
            response = self.client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"GitLab API error for GET {endpoint}: {e.response.status_code}")
            _raise_for_status(e)
        except httpx.RequestError as e:
            logger.error(f"Network error for GET {endpoint}: {e}")
            raise

    def get_paginated(
        self, endpoint: str, params: dict[str, Any] | None = None, per_page: int = 100, max_pages: int = 100
    ) -> list[Any]:
        """GET request with pagination support."""
        params = params or {}
        params["per_page"] = min(per_page, 100)
        params["page"] = 1

        all_results: list[Any] = []
        pages_fetched = 0

        try:
            while pages_fetched < max_pages:
                logger.debug(f"GET {endpoint} page {params['page']} (per_page={params['per_page']})")
                response = self.client.get(endpoint, params=params)
                response.raise_for_status()
                results = response.json()

                if not results:
                    break

                all_results.extend(results)
                pages_fetched += 1

                if "x-next-page" not in response.headers or not response.headers["x-next-page"]:
                    break

                params["page"] += 1

            if pages_fetched >= max_pages:
                logger.warning(f"Hit max_pages limit ({max_pages}) for {endpoint}. Results may be incomplete.")

            logger.debug(f"Fetched {len(all_results)} results from {pages_fetched} pages for {endpoint}")
            return all_results

        except httpx.HTTPStatusError as e:
            logger.error(f"GitLab API error during pagination of {endpoint}: {e.response.status_code}")
            _raise_for_status(e)
            return []  # unreachable, for type checker

    def get_projects(self, owned: bool = False, membership: bool = True) -> list[dict[str, Any]]:
        """Get all projects."""
        params: dict[str, Any] = {"membership": membership, "owned": owned}
        return self.get_paginated("/projects", params=params)

    def get_project(self, project_id: str) -> dict[str, Any]:
        """Get a specific project by ID or path."""
        encoded_id = self._encode_project_id(project_id)
        return self.get(f"/projects/{encoded_id}")
