"""Release client mixin."""

import logging
from typing import Any
from urllib.parse import quote

import httpx

from qodev_gitlab_api._base import BaseClientMixin, _raise_for_status

logger = logging.getLogger(__name__)


class ReleasesMixin(BaseClientMixin):
    """Mixin for release operations."""

    def get_releases(self, project_id: str, order_by: str = "released_at", sort: str = "desc") -> list[dict[str, Any]]:
        encoded_id = self._encode_project_id(project_id)
        params = {"order_by": order_by, "sort": sort}
        return self.get_paginated(f"/projects/{encoded_id}/releases", params=params)

    def get_release(self, project_id: str, tag_name: str) -> dict[str, Any]:
        encoded_id = self._encode_project_id(project_id)
        encoded_tag = quote(tag_name, safe="")
        return self.get(f"/projects/{encoded_id}/releases/{encoded_tag}")

    def create_release(
        self,
        project_id: str,
        tag_name: str,
        name: str | None = None,
        description: str | None = None,
        ref: str | None = None,
        milestones: list[str] | None = None,
        released_at: str | None = None,
        assets_links: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        encoded_id = self._encode_project_id(project_id)
        data: dict[str, Any] = {"tag_name": tag_name}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if ref is not None:
            data["ref"] = ref
        if milestones is not None:
            data["milestones"] = milestones
        if released_at is not None:
            data["released_at"] = released_at
        if assets_links is not None:
            data["assets"] = {"links": assets_links}

        try:
            response = self.client.post(f"/projects/{encoded_id}/releases", json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
            return {}

    def update_release(
        self,
        project_id: str,
        tag_name: str,
        name: str | None = None,
        description: str | None = None,
        milestones: list[str] | None = None,
        released_at: str | None = None,
    ) -> dict[str, Any]:
        encoded_id = self._encode_project_id(project_id)
        encoded_tag = quote(tag_name, safe="")
        data: dict[str, Any] = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if milestones is not None:
            data["milestones"] = milestones
        if released_at is not None:
            data["released_at"] = released_at

        try:
            response = self.client.put(f"/projects/{encoded_id}/releases/{encoded_tag}", json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
            return {}

    def delete_release(self, project_id: str, tag_name: str) -> None:
        encoded_id = self._encode_project_id(project_id)
        encoded_tag = quote(tag_name, safe="")
        try:
            response = self.client.delete(f"/projects/{encoded_id}/releases/{encoded_tag}")
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
