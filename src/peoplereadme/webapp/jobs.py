"""In-memory background job registry for pipeline stages.

Each job runs in a daemon thread, appends timestamped log lines to a bounded
buffer, and exposes a JSON-safe snapshot for polling from the UI.
"""

from __future__ import annotations

import threading
import traceback
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

MAX_LOG_LINES = 2000


class Job:
    def __init__(self, kind: str, persona_id: str):
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind
        self.persona_id = persona_id
        self.status = "running"
        self.error: str | None = None
        self.result: dict = {}
        self.started_at = datetime.now(UTC).isoformat()
        self.finished_at: str | None = None
        self._lock = threading.Lock()
        self._log: list[str] = []

    def log(self, line: str) -> None:
        stamp = datetime.now(UTC).strftime("%H:%M:%S")
        with self._lock:
            self._log.append(f"[{stamp}] {line}")
            if len(self._log) > MAX_LOG_LINES:
                del self._log[: len(self._log) - MAX_LOG_LINES]

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "id": self.id,
                "kind": self.kind,
                "persona_id": self.persona_id,
                "status": self.status,
                "error": self.error,
                "result": self.result,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "log": list(self._log),
            }


class JobRegistry:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def start(self, kind: str, persona_id: str, fn: Callable[[Job], dict]) -> Job:
        job = Job(kind, persona_id)
        with self._lock:
            self._jobs[job.id] = job

        def run() -> None:
            try:
                job.result = fn(job)
                job.status = "done"
            except Exception as exc:  # surface any stage failure to the UI
                job.status = "failed"
                job.error = f"{exc}"
                job.log(f"ERROR: {exc}")
                job.log(traceback.format_exc(limit=5))
            finally:
                job.finished_at = datetime.now(UTC).isoformat()

        threading.Thread(target=run, daemon=True).start()
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def active_for(self, persona_id: str) -> list[dict]:
        with self._lock:
            return [
                j.snapshot()
                for j in self._jobs.values()
                if j.persona_id == persona_id and j.status == "running"
            ]


registry = JobRegistry()
