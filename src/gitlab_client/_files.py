"""File operations client mixin."""

import base64
import binascii
import logging
import os
from typing import Any, cast
from urllib.parse import quote

import httpx

from gitlab_client._base import BaseClientMixin, _raise_for_status
from gitlab_client.models import FileFromPath, FileSource

logger = logging.getLogger(__name__)


class FilesMixin(BaseClientMixin):
    """Mixin for file operations."""

    def get_file_content(self, project_id: str, file_path: str, ref: str) -> str:
        """Get raw file content at a specific ref."""
        encoded_id = self._encode_project_id(project_id)
        encoded_path = quote(file_path, safe="")
        try:
            response = self.client.get(
                f"/projects/{encoded_id}/repository/files/{encoded_path}/raw",
                params={"ref": ref},
            )
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
            return ""

    def upload_file(self, project_id: str, source: FileSource) -> dict[str, Any]:
        """Upload a file to GitLab for use in markdown."""
        encoded_id = self._encode_project_id(project_id)

        if "path" in source:
            file_path = cast(FileFromPath, source)["path"]
            with open(file_path, "rb") as f:
                file_content = f.read()
            filename = os.path.basename(file_path)
        else:
            try:
                file_content = base64.b64decode(source["base64"], validate=True)
            except binascii.Error as e:
                raise ValueError(f"Invalid base64 data: {e}") from e
            filename = source["filename"]

        files = {"file": (filename, file_content)}
        try:
            response = httpx.post(
                f"{self.api_url}/projects/{encoded_id}/uploads",
                files=files,
                headers={"PRIVATE-TOKEN": str(self.token)},
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
            return {}
