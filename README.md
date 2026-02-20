[![CI](https://github.com/qodevai/gitlab-api/actions/workflows/ci.yml/badge.svg)](https://github.com/qodevai/gitlab-api/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/qodev-gitlab-api)](https://pypi.org/project/qodev-gitlab-api/)

# qodev-gitlab-api

A lightweight, typed Python client for the GitLab REST API. Built on [httpx](https://www.python-httpx.org/) with automatic pagination, structured error handling, and `.env` support, it provides a clean interface for common GitLab operations without the weight of a full-featured SDK.

## Why this library?

- **Lightweight** -- just `httpx`, no heavy ORM-like abstractions
- **Typed** -- ships with `py.typed` for full mypy/pyright support
- **Agent-friendly** -- simple method signatures, dict returns, auto-pagination
- **Built for tools** -- designed for MCP servers and CLIs, not full application frameworks
- **Focused** -- `python-gitlab` is comprehensive but heavy; this library covers the operations AI agents and developer tools actually need

## Installation

```bash
pip install qodev-gitlab-api
```

## Quick Start

```python
from qodev_gitlab_api import GitLabClient

# Reads GITLAB_TOKEN and GITLAB_URL from environment or .env file
client = GitLabClient()

# Or pass credentials explicitly
client = GitLabClient(token="glpat-xxxxxxxxxxxx", base_url="https://gitlab.example.com")

# Skip connection validation for faster startup
client = GitLabClient(validate=False)
```

```python
# List open merge requests
mrs = client.get_merge_requests("mygroup/myproject", state="opened")
for mr in mrs:
    print(f"!{mr['iid']} {mr['title']}")

# Create a merge request
client.create_merge_request("mygroup/myproject", "feature-branch", "main", "Add new feature")

# Get pipeline status
pipelines = client.get_pipelines("mygroup/myproject")
```

## Features

- **Merge requests** -- create, update, merge, close, and review with inline diff comments
- **Pipelines and jobs** -- list, inspect, wait for completion, retry, and download artifacts
- **Issues** -- create, update, close, and comment
- **Releases** -- create, update, delete, and list with asset links
- **CI/CD variables** -- get, list, create, update, and upsert (set) project variables
- **File operations** -- read repository files at any ref, upload files for markdown embedding
- **Automatic pagination** -- all list endpoints handle multi-page results transparently
- **Typed exceptions** -- `AuthenticationError`, `NotFoundError`, `APIError`, `ConfigurationError`

## Configuration

The client reads configuration from environment variables, with `.env` file support via `python-dotenv`:

| Variable | Description | Default |
|---|---|---|
| `GITLAB_TOKEN` | GitLab personal access token (required) | -- |
| `GITLAB_URL` | GitLab instance base URL | `https://gitlab.com` |

You can also use `GITLAB_BASE_URL` as an alias for `GITLAB_URL`.

Create a `.env` file in your project root:

```
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
GITLAB_URL=https://gitlab.example.com
```

## API Reference

### Projects

```python
projects = client.get_projects(owned=True)
project = client.get_project("my-group/my-project")
```

### Merge Requests

```python
# List and inspect
mrs = client.get_merge_requests("my-group/my-project", state="opened")
mr = client.get_merge_request("my-group/my-project", mr_iid=42)
changes = client.get_mr_changes("my-group/my-project", mr_iid=42)
commits = client.get_mr_commits("my-group/my-project", mr_iid=42)
approvals = client.get_mr_approvals("my-group/my-project", mr_iid=42)

# Create
mr = client.create_merge_request(
    "my-group/my-project",
    source_branch="feature/foo",
    target_branch="main",
    title="Add foo feature",
    description="Implements the foo feature.",
    assignee_ids=[123],
    reviewer_ids=[456],
    labels="enhancement",
)

# Update, merge, close
client.update_mr("my-group/my-project", mr_iid=42, title="Updated title")
client.merge_mr("my-group/my-project", mr_iid=42, squash=True)
client.close_mr("my-group/my-project", mr_iid=42)

# Discussions and comments
discussions = client.get_mr_discussions("my-group/my-project", mr_iid=42)
client.create_mr_note("my-group/my-project", mr_iid=42, body="Looks good!")
client.reply_to_discussion("my-group/my-project", mr_iid=42, discussion_id="abc123", body="Fixed.")
client.resolve_discussion("my-group/my-project", mr_iid=42, discussion_id="abc123", resolved=True)

# Inline diff comment
from qodev_gitlab_api import DiffPosition

client.create_mr_discussion(
    "my-group/my-project",
    mr_iid=42,
    body="Consider renaming this variable.",
    position=DiffPosition(file_path="src/main.py", new_line=15),
)
```

### Pipelines and Jobs

```python
pipelines = client.get_pipelines("my-group/my-project", ref="main")
pipeline = client.get_pipeline("my-group/my-project", pipeline_id=1001)
jobs = client.get_pipeline_jobs("my-group/my-project", pipeline_id=1001)

# Job details, logs, and artifacts
job = client.get_job("my-group/my-project", job_id=5001)
log = client.get_job_log("my-group/my-project", job_id=5001)
artifact = client.get_job_artifact("my-group/my-project", job_id=5001, artifact_path="report.xml")

# Retry a failed job
client.retry_job("my-group/my-project", job_id=5001)

# Wait for pipeline completion (blocks until done or timeout)
result = client.wait_for_pipeline("my-group/my-project", pipeline_id=1001, timeout_seconds=600)
print(result["final_status"])  # "success", "failed", "canceled", "skipped", or "timeout"
```

### Issues

```python
issues = client.get_issues("my-group/my-project", state="opened", labels="bug")
issue = client.get_issue("my-group/my-project", issue_iid=10)

issue = client.create_issue(
    "my-group/my-project",
    title="Fix login bug",
    description="Users cannot log in with SSO.",
    labels="bug,urgent",
    assignee_ids=[123],
)

client.update_issue("my-group/my-project", issue_iid=10, labels="bug,resolved")
client.close_issue("my-group/my-project", issue_iid=10)

# Comments
notes = client.get_issue_notes("my-group/my-project", issue_iid=10)
client.create_issue_note("my-group/my-project", issue_iid=10, body="Investigating this now.")
```

### Releases

```python
releases = client.get_releases("my-group/my-project")
release = client.get_release("my-group/my-project", tag_name="v1.0.0")

release = client.create_release(
    "my-group/my-project",
    tag_name="v1.1.0",
    name="Version 1.1.0",
    description="## What's new\n- Feature A\n- Bug fix B",
    ref="main",
)

client.update_release("my-group/my-project", tag_name="v1.1.0", description="Updated notes.")
client.delete_release("my-group/my-project", tag_name="v1.1.0")
```

### CI/CD Variables

```python
variables = client.list_project_variables("my-group/my-project")
var = client.get_project_variable("my-group/my-project", key="API_KEY")

# Create or update (upsert)
var, action = client.set_project_variable(
    "my-group/my-project",
    key="API_KEY",
    value="secret-value",
    masked=True,
    protected=True,
)
print(action)  # "created" or "updated"
```

### File Operations

```python
# Read a file from the repository
content = client.get_file_content("my-group/my-project", file_path="README.md", ref="main")

# Upload a file (for embedding in issues/MRs)
from qodev_gitlab_api import FileFromPath

result = client.upload_file("my-group/my-project", source=FileFromPath(path="/tmp/screenshot.png"))
```

## Error Handling

All API errors raise typed exceptions that inherit from `GitLabError`:

```python
from qodev_gitlab_api import GitLabClient, AuthenticationError, NotFoundError, APIError, ConfigurationError

try:
    client = GitLabClient()
    mr = client.get_merge_request("my-group/my-project", mr_iid=999)
except ConfigurationError:
    print("Missing or invalid GITLAB_TOKEN / GITLAB_URL")
except AuthenticationError:
    print("Token is invalid or expired")
except NotFoundError:
    print("Merge request not found")
except APIError as e:
    print(f"API error {e.status_code}: {e.response_body}")
```

## Requirements

- Python 3.11+
- [httpx](https://www.python-httpx.org/) >= 0.28.1
- [python-dotenv](https://github.com/theskumar/python-dotenv) >= 1.1.0

## License

MIT -- see [LICENSE](LICENSE) for details.
