"""actiTime API client — handles all HTTP calls to the actiTime REST API."""

import requests
import urllib3
from datetime import date, timedelta

# Synthetis uses an internal SSL certificate — disable verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ActiTimeClient:
    """Wrapper around the actiTime REST API v1."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/") + "/api/v1"
        self.auth = (username, password)
        self.user_id: int | None = None
        self.full_name: str | None = None

    # ── Authentication ────────────────────────────────────────────────

    def login(self) -> dict:
        """Verify credentials and store user info. Returns user dict."""
        resp = self._get("/users/me")
        self.user_id = resp["id"]
        self.full_name = resp.get("fullName", resp.get("username"))
        return resp

    # ── Tasks ─────────────────────────────────────────────────────────

    def get_open_tasks(self) -> list[dict]:
        """Return all open tasks accessible to the authenticated user."""
        resp = self._get(
            "/tasks",
            params={
                "status": "open",
                "limit": 1000,
                "includeReferenced": "projects,customers",
            },
        )
        items = resp.get("items", [])
        projects = resp.get("projects", {})
        customers = resp.get("customers", {})

        # Enrich each task with project/customer names from referenced data
        for task in items:
            pid = str(task.get("projectId", ""))
            cid = str(task.get("customerId", ""))
            if pid in projects:
                task["projectName"] = projects[pid].get("name", task.get("projectName", ""))
            if cid in customers:
                task["customerName"] = customers[cid].get("name", task.get("customerName", ""))
        return items

    # ── Time-Track (read) ─────────────────────────────────────────────

    def get_timetrack(self, date_from: str, date_to: str) -> list[dict]:
        """Return time-track records for the current user in a date range.

        Each item: { date, userId, records: [{ taskId, time, comment? }] }
        """
        resp = self._get(
            "/timetrack",
            params={
                "userIds": self.user_id,
                "dateFrom": date_from,
                "dateTo": date_to,
                "includeReferenced": "tasks,projects,customers",
            },
        )
        data = resp.get("data", [])
        # Attach referenced task/project/customer names for display
        tasks_ref = resp.get("tasks", {})
        projects_ref = resp.get("projects", {})
        customers_ref = resp.get("customers", {})
        for day in data:
            for rec in day.get("records", []):
                tid = str(rec.get("taskId", ""))
                if tid in tasks_ref:
                    t = tasks_ref[tid]
                    rec["taskName"] = t.get("name", "")
                    pid = str(t.get("projectId", ""))
                    cid = str(t.get("customerId", ""))
                    rec["projectName"] = projects_ref.get(pid, {}).get("name", "")
                    rec["customerName"] = customers_ref.get(cid, {}).get("name", "")
        return data

    # ── Time-Track (write) ────────────────────────────────────────────

    def patch_timetrack(self, user_id: int, date_str: str, task_id: int,
                        minutes: int, comment: str = "") -> dict:
        """Create or replace a time-track entry for a single task on a single day."""
        body = {"time": minutes}
        if comment:
            body["comment"] = comment
        return self._patch(f"/timetrack/{user_id}/{date_str}/{task_id}", json_body=body)

    def batch_patch_timetrack(self, entries: list[dict], user_id: int, date_str: str) -> list[dict]:
        """Push multiple time entries at once using the /batch endpoint.

        entries: list of { taskId, minutes, comment }
        """
        operations = []
        for e in entries:
            body = {"time": e["minutes"]}
            if e.get("comment"):
                body["comment"] = e["comment"]
            operations.append({
                "method": "PATCH",
                "relativeUrl": f"/timetrack/{user_id}/{date_str}/{e['taskId']}",
                "body": body,
            })
        resp = self._post("/batch", json_body=operations)
        return resp

    # ── User schedule ─────────────────────────────────────────────────

    def get_schedule(self, date_from: str, date_to: str) -> list[int]:
        """Return scheduled minutes per day for the current user."""
        resp = self._get(
            f"/users/{self.user_id}/schedule",
            params={"dateFrom": date_from, "dateTo": date_to},
        )
        return resp.get("schedule", [])

    # ── Internal HTTP helpers ─────────────────────────────────────────

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = self.base_url + path
        r = requests.get(url, auth=self.auth, params=params,
                         headers={"Accept": "application/json; charset=UTF-8"},
                         verify=False)
        r.raise_for_status()
        return r.json()

    def _patch(self, path: str, json_body: dict | None = None) -> dict:
        url = self.base_url + path
        r = requests.patch(url, auth=self.auth, json=json_body,
                           headers={"Accept": "application/json; charset=UTF-8",
                                    "Content-Type": "application/json; charset=UTF-8"},
                           verify=False)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, json_body=None) -> dict | list:
        url = self.base_url + path
        r = requests.post(url, auth=self.auth, json=json_body,
                          headers={"Accept": "application/json; charset=UTF-8",
                                   "Content-Type": "application/json; charset=UTF-8"},
                          verify=False)
        r.raise_for_status()
        return r.json()
