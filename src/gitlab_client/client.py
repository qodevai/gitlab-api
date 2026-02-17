"""GitLab API client composed from mixins."""

from gitlab_client._files import FilesMixin
from gitlab_client._issues import IssuesMixin
from gitlab_client._merge_requests import MergeRequestsMixin
from gitlab_client._pipelines import PipelinesMixin
from gitlab_client._releases import ReleasesMixin
from gitlab_client._variables import VariablesMixin


class GitLabClient(
    MergeRequestsMixin,
    PipelinesMixin,
    IssuesMixin,
    ReleasesMixin,
    VariablesMixin,
    FilesMixin,
):
    """GitLab API client composed from mixins.

    Provides methods for interacting with GitLab's API including:
    - Projects
    - Merge requests and discussions
    - Pipelines and jobs
    - Issues
    - Releases
    - CI/CD variables
    - File uploads
    """
