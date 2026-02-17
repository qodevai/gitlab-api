"""Type definitions for the GitLab client."""

from typing import NotRequired

from typing_extensions import TypedDict


class FileFromPath(TypedDict):
    """File input from local filesystem path."""

    path: str


class FileFromBase64(TypedDict):
    """File input from base64-encoded data."""

    base64: str
    filename: str


FileSource = FileFromPath | FileFromBase64


class DiffPosition(TypedDict):
    """Position in a merge request diff for inline comments."""

    file_path: str
    new_line: NotRequired[int]
    old_line: NotRequired[int]
    new_line_content: NotRequired[str]
    old_line_content: NotRequired[str]
    base_sha: NotRequired[str]
    head_sha: NotRequired[str]
    start_sha: NotRequired[str]
