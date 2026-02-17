"""Pipeline and job client mixin."""

import logging
import time
from typing import Any

import httpx

from gitlab_client._base import BaseClientMixin, _raise_for_status

logger = logging.getLogger(__name__)


class PipelinesMixin(BaseClientMixin):
    """Mixin for pipeline and job operations."""

    def get_pipelines(
        self,
        project_id: str,
        ref: str | None = None,
        per_page: int = 3,
        max_pages: int = 1,
    ) -> list[dict[str, Any]]:
        encoded_id = self._encode_project_id(project_id)
        params = {"ref": ref} if ref else {}
        return self.get_paginated(
            f"/projects/{encoded_id}/pipelines", params=params, per_page=per_page, max_pages=max_pages
        )

    def get_pipeline(self, project_id: str, pipeline_id: int) -> dict[str, Any]:
        encoded_id = self._encode_project_id(project_id)
        return self.get(f"/projects/{encoded_id}/pipelines/{pipeline_id}")

    def get_pipeline_jobs(self, project_id: str, pipeline_id: int) -> list[dict[str, Any]]:
        encoded_id = self._encode_project_id(project_id)
        return self.get_paginated(f"/projects/{encoded_id}/pipelines/{pipeline_id}/jobs")

    def get_job_log(self, project_id: str, job_id: int) -> str:
        """Get logs for a specific job (plain text)."""
        encoded_id = self._encode_project_id(project_id)
        try:
            response = self.client.get(f"/projects/{encoded_id}/jobs/{job_id}/trace")
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
            return ""

    def get_job(self, project_id: str, job_id: int) -> dict[str, Any]:
        """Get job details."""
        encoded_id = self._encode_project_id(project_id)
        try:
            response = self.client.get(f"/projects/{encoded_id}/jobs/{job_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
            return {}

    def retry_job(self, project_id: str, job_id: int) -> dict[str, Any]:
        """Retry a job (creates a new job)."""
        encoded_id = self._encode_project_id(project_id)
        try:
            response = self.client.post(f"/projects/{encoded_id}/jobs/{job_id}/retry")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
            return {}

    def get_job_artifact(self, project_id: str, job_id: int, artifact_path: str) -> bytes:
        """Download a specific artifact file from a job."""
        encoded_id = self._encode_project_id(project_id)
        try:
            response = self.client.get(f"/projects/{encoded_id}/jobs/{job_id}/artifacts/{artifact_path}")
            response.raise_for_status()
            return response.content
        except httpx.HTTPStatusError as e:
            _raise_for_status(e)
            return b""

    def enrich_jobs_with_failure_logs(self, project_id: str, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Add last 10 lines of logs to failed jobs."""
        enriched_jobs = []
        for job in jobs:
            job_copy = job.copy()
            if job.get("status") == "failed":
                try:
                    full_log = self.get_job_log(project_id, job["id"])
                    log_lines = full_log.split("\n")
                    last_lines = [line for line in log_lines if line.strip()][-10:]
                    job_copy["failure_log_tail"] = "\n".join(last_lines)
                except Exception as e:
                    logger.warning(f"Failed to fetch log for job {job['id']}: {e}")
            enriched_jobs.append(job_copy)
        return enriched_jobs

    def wait_for_pipeline(
        self,
        project_id: str,
        pipeline_id: int,
        timeout_seconds: int = 3600,
        check_interval: int = 10,
        include_failed_logs: bool = True,
    ) -> dict[str, Any]:
        """Wait for a pipeline to complete (success or failure)."""
        start_time = time.time()
        checks = 0
        final_status = None
        pipeline = None

        while True:
            checks += 1
            elapsed = time.time() - start_time

            pipeline = self.get_pipeline(project_id, pipeline_id)
            status = pipeline.get("status")

            if status in ("success", "failed", "canceled", "skipped"):
                final_status = status
                break

            if elapsed > timeout_seconds:
                final_status = "timeout"
                break

            time.sleep(check_interval)

        total_duration = time.time() - start_time
        result: dict[str, Any] = {
            "final_status": final_status,
            "pipeline_id": pipeline_id,
            "pipeline_url": pipeline.get("web_url") if pipeline else None,
            "total_duration": round(total_duration, 2),
            "checks_performed": checks,
        }

        if pipeline and final_status != "timeout":
            try:
                jobs = self.get_pipeline_jobs(project_id, pipeline_id)
                result["job_summary"] = {
                    "total": len(jobs),
                    "success": len([j for j in jobs if j.get("status") == "success"]),
                    "failed": len([j for j in jobs if j.get("status") == "failed"]),
                }

                if include_failed_logs and final_status == "failed":
                    failed_jobs = [j for j in jobs if j.get("status") == "failed"]
                    failed_job_details = []
                    for job in failed_jobs[:5]:
                        job_detail: dict[str, Any] = {
                            "id": job.get("id"),
                            "name": job.get("name"),
                            "status": job.get("status"),
                            "web_url": job.get("web_url"),
                        }
                        try:
                            log = self.get_job_log(project_id, job["id"])
                            lines = log.strip().split("\n")
                            job_detail["last_log_lines"] = "\n".join(lines[-10:])
                        except Exception:
                            job_detail["last_log_lines"] = "(log unavailable)"
                        failed_job_details.append(job_detail)
                    result["failed_jobs"] = failed_job_details
            except Exception as e:
                logger.warning(f"Could not fetch job details: {e}")

        return result
