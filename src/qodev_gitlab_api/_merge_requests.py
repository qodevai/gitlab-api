"""Merge request client mixin."""

import json
import logging
from typing import Any

import httpx

from qodev_gitlab_api._base import BaseClientMixin, _raise_for_status
from qodev_gitlab_api.models import DiffPosition

logger = logging.getLogger(__name__)


class MergeRequestsMixin(BaseClientMixin):
    """Mixin for merge request operations."""

    def get_merge_requests(self, project_id: str, state: str = "opened") -> list[dict[str, Any]]:
        encoded_id = self._encode_project_id(project_id)
        params = {"state": state}
        return self.get_paginated(f"/projects/{encoded_id}/merge_requests", params=params)

    def get_merge_request(self, project_id: str, mr_iid: int) -> dict[str, Any]:
        encoded_id = self._encode_project_id(project_id)
        return self.get(f"/projects/{encoded_id}/merge_requests/{mr_iid}")

    def get_mr_discussions(self, project_id: str, mr_iid: int) -> list[dict[str, Any]]:
        encoded_id = self._encode_project_id(project_id)
        return self.get_paginated(f"/projects/{encoded_id}/merge_requests/{mr_iid}/discussions")

    def get_mr_changes(self, project_id: str, mr_iid: int) -> dict[str, Any]:
        encoded_id = self._encode_project_id(project_id)
        return self.get(f"/projects/{encoded_id}/merge_requests/{mr_iid}/changes")

    def get_mr_commits(self, project_id: str, mr_iid: int) -> list[dict[str, Any]]:
        encoded_id = self._encode_project_id(project_id)
        return self.get_paginated(f"/projects/{encoded_id}/merge_requests/{mr_iid}/commits")

    def get_mr_approvals(self, project_id: str, mr_iid: int) -> dict[str, Any]:
        encoded_id = self._encode_project_id(project_id)
        return self.get(f"/projects/{encoded_id}/merge_requests/{mr_iid}/approvals")

    def get_mr_pipelines(self, project_id: str, mr_iid: int) -> list[dict[str, Any]]:
        encoded_id = self._encode_project_id(project_id)
        return self.get(f"/projects/{encoded_id}/merge_requests/{mr_iid}/pipelines")

    def create_mr_note(self, project_id: str, mr_iid: int, body: str) -> dict[str, Any]:
        """Create a comment/note on a merge request."""
        encoded_id = self._encode_project_id(project_id)
        try:
            response = self.client.post(
                f"/projects/{encoded_id}/merge_requests/{mr_iid}/notes",
                json={"body": body},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
            return {}  # unreachable

    def reply_to_discussion(self, project_id: str, mr_iid: int, discussion_id: str, body: str) -> dict[str, Any]:
        """Reply to an existing discussion thread."""
        encoded_id = self._encode_project_id(project_id)
        try:
            response = self.client.post(
                f"/projects/{encoded_id}/merge_requests/{mr_iid}/discussions/{discussion_id}/notes",
                json={"body": body},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
            return {}

    def create_mr_discussion(
        self,
        project_id: str,
        mr_iid: int,
        body: str,
        position: DiffPosition | None = None,
    ) -> dict[str, Any]:
        """Create a discussion, optionally inline on a specific diff line."""
        encoded_id = self._encode_project_id(project_id)

        data: dict[str, Any] = {"body": body}

        if position:
            gitlab_position: dict[str, Any] = {
                "position_type": "text",
                "new_path": position["file_path"],
                "old_path": position["file_path"],
            }
            for key in ("new_line", "old_line", "base_sha", "head_sha", "start_sha"):
                if key in position:
                    gitlab_position[key] = position[key]
            data["position"] = gitlab_position

        try:
            response = self.client.post(
                f"/projects/{encoded_id}/merge_requests/{mr_iid}/discussions",
                json=data,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
            return {}

    def resolve_discussion(self, project_id: str, mr_iid: int, discussion_id: str, resolved: bool) -> dict[str, Any]:
        """Resolve or unresolve a discussion thread."""
        encoded_id = self._encode_project_id(project_id)
        try:
            response = self.client.put(
                f"/projects/{encoded_id}/merge_requests/{mr_iid}/discussions/{discussion_id}",
                json={"resolved": resolved},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
            return {}

    def create_merge_request(
        self,
        project_id: str,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str | None = None,
        assignee_ids: list[int] | None = None,
        reviewer_ids: list[int] | None = None,
        labels: str | None = None,
        remove_source_branch: bool = True,
        squash: bool | None = None,
        allow_collaboration: bool = False,
    ) -> dict[str, Any]:
        """Create a new merge request."""
        encoded_id = self._encode_project_id(project_id)

        data: dict[str, Any] = {
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": title,
            "remove_source_branch": remove_source_branch,
            "allow_collaboration": allow_collaboration,
        }

        if description is not None:
            data["description"] = description
        if assignee_ids is not None:
            data["assignee_ids"] = assignee_ids
        if reviewer_ids is not None:
            data["reviewer_ids"] = reviewer_ids
        if labels is not None:
            data["labels"] = labels
        if squash is not None:
            data["squash"] = squash

        try:
            response = self.client.post(f"/projects/{encoded_id}/merge_requests", json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
            return {}

    def merge_mr(
        self,
        project_id: str,
        mr_iid: int,
        merge_commit_message: str | None = None,
        squash_commit_message: str | None = None,
        should_remove_source_branch: bool = True,
        merge_when_pipeline_succeeds: bool = False,
        squash: bool | None = None,
    ) -> dict[str, Any]:
        """Merge a merge request."""
        encoded_id = self._encode_project_id(project_id)

        data: dict[str, Any] = {
            "should_remove_source_branch": should_remove_source_branch,
            "merge_when_pipeline_succeeds": merge_when_pipeline_succeeds,
        }

        if merge_commit_message:
            data["merge_commit_message"] = merge_commit_message
        if squash_commit_message:
            data["squash_commit_message"] = squash_commit_message
        if squash is not None:
            data["squash"] = squash

        try:
            response = self.client.put(f"/projects/{encoded_id}/merge_requests/{mr_iid}/merge", json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # Try to extract better error message from GitLab response
            try:
                error_json = json.loads(e.response.text)
                msg = error_json.get("message", str(e))
            except (json.JSONDecodeError, AttributeError):
                msg = str(e)
            from qodev_gitlab_api.exceptions import APIError as _APIError

            raise _APIError(msg, status_code=e.response.status_code, response_body=e.response.text[:500]) from e

    def close_mr(self, project_id: str, mr_iid: int) -> dict[str, Any]:
        """Close a merge request."""
        encoded_id = self._encode_project_id(project_id)
        try:
            response = self.client.put(
                f"/projects/{encoded_id}/merge_requests/{mr_iid}",
                json={"state_event": "close"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
            return {}

    def update_mr(
        self,
        project_id: str,
        mr_iid: int,
        title: str | None = None,
        description: str | None = None,
        target_branch: str | None = None,
        state_event: str | None = None,
        assignee_ids: list[int] | None = None,
        reviewer_ids: list[int] | None = None,
        labels: str | None = None,
    ) -> dict[str, Any]:
        """Update a merge request."""
        encoded_id = self._encode_project_id(project_id)

        data: dict[str, Any] = {}
        if title is not None:
            data["title"] = title
        if description is not None:
            data["description"] = description
        if target_branch is not None:
            data["target_branch"] = target_branch
        if state_event is not None:
            data["state_event"] = state_event
        if assignee_ids is not None:
            data["assignee_ids"] = assignee_ids
        if reviewer_ids is not None:
            data["reviewer_ids"] = reviewer_ids
        if labels is not None:
            data["labels"] = labels

        try:
            response = self.client.put(f"/projects/{encoded_id}/merge_requests/{mr_iid}", json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
            return {}
