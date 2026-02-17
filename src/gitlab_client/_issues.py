"""Issue client mixin."""

import logging
from typing import Any

import httpx

from gitlab_client._base import BaseClientMixin, _raise_for_status

logger = logging.getLogger(__name__)


class IssuesMixin(BaseClientMixin):
    """Mixin for issue operations."""

    def get_issues(
        self,
        project_id: str,
        state: str = "opened",
        labels: str | None = None,
        assignee_id: int | None = None,
        milestone: str | None = None,
        per_page: int = 20,
        max_pages: int = 10,
    ) -> list[dict[str, Any]]:
        encoded_id = self._encode_project_id(project_id)
        params: dict[str, Any] = {"state": state}
        if labels:
            params["labels"] = labels
        if assignee_id is not None:
            params["assignee_id"] = assignee_id
        if milestone:
            params["milestone"] = milestone
        return self.get_paginated(
            f"/projects/{encoded_id}/issues", params=params, per_page=per_page, max_pages=max_pages
        )

    def get_issue(self, project_id: str, issue_iid: int) -> dict[str, Any]:
        encoded_id = self._encode_project_id(project_id)
        return self.get(f"/projects/{encoded_id}/issues/{issue_iid}")

    def create_issue(
        self,
        project_id: str,
        title: str,
        description: str | None = None,
        labels: str | None = None,
        assignee_ids: list[int] | None = None,
        milestone_id: int | None = None,
    ) -> dict[str, Any]:
        encoded_id = self._encode_project_id(project_id)
        data: dict[str, Any] = {"title": title}
        if description:
            data["description"] = description
        if labels:
            data["labels"] = labels
        if assignee_ids:
            data["assignee_ids"] = assignee_ids
        if milestone_id is not None:
            data["milestone_id"] = milestone_id

        try:
            response = self.client.post(f"/projects/{encoded_id}/issues", json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
            return {}

    def update_issue(
        self,
        project_id: str,
        issue_iid: int,
        title: str | None = None,
        description: str | None = None,
        state_event: str | None = None,
        labels: str | None = None,
        assignee_ids: list[int] | None = None,
        milestone_id: int | None = None,
    ) -> dict[str, Any]:
        encoded_id = self._encode_project_id(project_id)
        data: dict[str, Any] = {}
        if title:
            data["title"] = title
        if description is not None:
            data["description"] = description
        if state_event:
            data["state_event"] = state_event
        if labels is not None:
            data["labels"] = labels
        if assignee_ids is not None:
            data["assignee_ids"] = assignee_ids
        if milestone_id is not None:
            data["milestone_id"] = milestone_id

        try:
            response = self.client.put(f"/projects/{encoded_id}/issues/{issue_iid}", json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
            return {}

    def close_issue(self, project_id: str, issue_iid: int) -> dict[str, Any]:
        return self.update_issue(project_id, issue_iid, state_event="close")

    def get_issue_notes(self, project_id: str, issue_iid: int) -> list[dict[str, Any]]:
        encoded_id = self._encode_project_id(project_id)
        return self.get_paginated(f"/projects/{encoded_id}/issues/{issue_iid}/notes")

    def create_issue_note(self, project_id: str, issue_iid: int, body: str) -> dict[str, Any]:
        encoded_id = self._encode_project_id(project_id)
        try:
            response = self.client.post(f"/projects/{encoded_id}/issues/{issue_iid}/notes", json={"body": body})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
            return {}
