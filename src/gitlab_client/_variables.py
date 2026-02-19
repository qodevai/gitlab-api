"""CI/CD variables client mixin."""

import logging
from typing import Any
from urllib.parse import quote

import httpx

from gitlab_client._base import BaseClientMixin, _raise_for_status

logger = logging.getLogger(__name__)


class VariablesMixin(BaseClientMixin):
    """Mixin for CI/CD variable operations."""

    def get_project_variable(self, project_id: str, key: str) -> dict[str, Any] | None:
        """Get a specific CI/CD variable. Returns None if not found."""
        encoded_id = self._encode_project_id(project_id)
        encoded_key = quote(key, safe="")
        try:
            response = self.client.get(f"/projects/{encoded_id}/variables/{encoded_key}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            _raise_for_status(e)
            return None

    @staticmethod
    def _sanitize_variable(var: dict[str, Any]) -> dict[str, Any]:
        return {
            "key": var.get("key"),
            "variable_type": var.get("variable_type"),
            "protected": var.get("protected"),
            "masked": var.get("masked"),
            "raw": var.get("raw"),
            "environment_scope": var.get("environment_scope"),
            "description": var.get("description"),
        }

    def list_project_variables(
        self, project_id: str, per_page: int = 100, max_pages: int = 100
    ) -> list[dict[str, Any]]:
        """List all CI/CD variables (values stripped for security)."""
        encoded_id = self._encode_project_id(project_id)
        variables = self.get_paginated(f"/projects/{encoded_id}/variables", per_page=per_page, max_pages=max_pages)
        return [self._sanitize_variable(var) for var in variables]

    def create_project_variable(
        self,
        project_id: str,
        key: str,
        value: str,
        variable_type: str = "env_var",
        protected: bool = False,
        masked: bool = False,
        raw: bool = False,
        environment_scope: str = "*",
        description: str | None = None,
    ) -> dict[str, Any]:
        encoded_id = self._encode_project_id(project_id)
        data: dict[str, Any] = {
            "key": key,
            "value": value,
            "variable_type": variable_type,
            "protected": protected,
            "masked": masked,
            "raw": raw,
            "environment_scope": environment_scope,
        }
        if description is not None:
            data["description"] = description

        try:
            response = self.client.post(f"/projects/{encoded_id}/variables", json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
            return {}

    def update_project_variable(
        self,
        project_id: str,
        key: str,
        value: str,
        variable_type: str = "env_var",
        protected: bool = False,
        masked: bool = False,
        raw: bool = False,
        environment_scope: str = "*",
        description: str | None = None,
    ) -> dict[str, Any]:
        encoded_id = self._encode_project_id(project_id)
        encoded_key = quote(key, safe="")
        data: dict[str, Any] = {
            "value": value,
            "variable_type": variable_type,
            "protected": protected,
            "masked": masked,
            "raw": raw,
            "environment_scope": environment_scope,
        }
        if description is not None:
            data["description"] = description

        try:
            response = self.client.put(f"/projects/{encoded_id}/variables/{encoded_key}", json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
            return {}

    def set_project_variable(
        self,
        project_id: str,
        key: str,
        value: str,
        variable_type: str = "env_var",
        protected: bool = False,
        masked: bool = False,
        raw: bool = False,
        environment_scope: str = "*",
        description: str | None = None,
    ) -> tuple[dict[str, Any], str]:
        """Upsert: update if exists, create if not. Returns (variable, action)."""
        existing = self.get_project_variable(project_id, key)
        kwargs = dict(
            project_id=project_id,
            key=key,
            value=value,
            variable_type=variable_type,
            protected=protected,
            masked=masked,
            raw=raw,
            environment_scope=environment_scope,
            description=description,
        )
        if existing:
            return self.update_project_variable(**kwargs), "updated"
        return self.create_project_variable(**kwargs), "created"
