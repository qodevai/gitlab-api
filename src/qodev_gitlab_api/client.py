"""GitLab API client composed from mixins."""

from qodev_gitlab_api._files import FilesMixin
from qodev_gitlab_api._issues import IssuesMixin
from qodev_gitlab_api._merge_requests import MergeRequestsMixin
from qodev_gitlab_api._pipelines import PipelinesMixin
from qodev_gitlab_api._releases import ReleasesMixin
from qodev_gitlab_api._variables import VariablesMixin


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
