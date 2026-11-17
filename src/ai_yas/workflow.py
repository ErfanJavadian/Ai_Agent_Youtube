"""Deterministic workflow state machine for a single video project.

This module performs no network or AI API calls. State changes are explicit,
validated, and persisted through ProjectStore.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .storage import ProjectStore


class WorkflowError(Exception):
    """Base exception for invalid workflow operations."""


class InvalidTransitionError(WorkflowError):
    """Raised when a requested state transition is not allowed."""


class ProjectNotFoundError(WorkflowError):
    """Raised when the requested project does not exist."""


class Stage(str, Enum):
    INTAKE = "intake"
    RESEARCH = "research"
    STRATEGY = "strategy"
    SCRIPT = "script"
    STORYBOARD = "storyboard"
    ASSETS = "assets"
    AUDIO = "audio"
    EDIT = "edit"
    QUALITY_CONTROL = "quality_control"
    PUBLISHING_PACKAGE = "publishing_package"
    APPROVAL = "approval"
    COMPLETE = "complete"


class WorkflowStatus(str, Enum):
    READY = "ready"
    RUNNING = "running"
    WAITING_FOR_HUMAN = "waiting_for_human"
    BLOCKED = "blocked"
    FAILED = "failed"
    COMPLETED = "completed"


STAGES = tuple(stage.value for stage in Stage if stage is not Stage.COMPLETE)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class WorkflowEngine:
    """Coordinates legal workflow transitions and persists each mutation."""

    def __init__(self, store: ProjectStore):
        self.store = store

    def create_project(
        self,
        project_id: str,
        title: str,
        target_audience: str,
        topic: str = "",
        language: str = "en",
        video_format: str = "cinematic_documentary",
        target_duration_seconds: int = 600,
    ) -> dict[str, Any]:
        now = _now()
        project = {
            "schema_version": "1.0.0",
            "project_id": project_id,
            "title": title,
            "topic": topic,
            "language": language,
            "target_audience": target_audience,
            "format": video_format,
            "target_duration_seconds": target_duration_seconds,
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "approval_required": True,
        }
        state = {
            "schema_version": "1.0.0",
            "project_id": project_id,
            "current_stage": Stage.INTAKE.value,
            "status": WorkflowStatus.READY.value,
            "updated_at": now,
            "completed_stages": [],
            "attempt": 0,
            "checkpoint_ref": None,
            "human_approval": "not_requested",
        }
        self.store.create(project, state)
        return {"project": project, "workflow": state}

    def snapshot(self, project_id: str) -> dict[str, Any]:
        return self.store.load(project_id)

    def start(self, project_id: str) -> dict[str, Any]:
        data = self._load(project_id)
        state = data["workflow"]
        self._require_status(state, WorkflowStatus.READY)
        state["status"] = WorkflowStatus.RUNNING.value
        state["attempt"] = state.get("attempt", 0) + 1
        state.pop("blocked_reason", None)
        state.pop("last_error", None)
        return self._save(data)

    def complete_current_stage(self, project_id: str, checkpoint_ref: str | None = None) -> dict[str, Any]:
        data = self._load(project_id)
        state = data["workflow"]
        self._require_status(state, WorkflowStatus.RUNNING)
        current = state["current_stage"]
        if current == Stage.APPROVAL.value and state.get("human_approval") != "approved":
            raise InvalidTransitionError("Publication approval is mandatory before completing the approval stage.")
        if current == Stage.COMPLETE.value:
            raise InvalidTransitionError("The workflow is already complete.")
        completed = state["completed_stages"]
        if current not in completed:
            completed.append(current)
        index = STAGES.index(current)
        next_stage = Stage.COMPLETE.value if index == len(STAGES) - 1 else STAGES[index + 1]
        state["current_stage"] = next_stage
        state["checkpoint_ref"] = checkpoint_ref
        state["status"] = (
            WorkflowStatus.COMPLETED.value if next_stage == Stage.COMPLETE.value
            else WorkflowStatus.READY.value
        )
        if next_stage == Stage.COMPLETE.value:
            data["project"]["status"] = "completed"
            data["project"]["updated_at"] = _now()
        return self._save(data)

    def request_approval(self, project_id: str) -> dict[str, Any]:
        data = self._load(project_id)
        state = data["workflow"]
        if state["current_stage"] != Stage.APPROVAL.value:
            raise InvalidTransitionError("Human approval can only be requested at the approval stage.")
        self._require_status(state, WorkflowStatus.READY)
        state["human_approval"] = "pending"
        state["status"] = WorkflowStatus.WAITING_FOR_HUMAN.value
        return self._save(data)

    def resolve_approval(self, project_id: str, approved: bool, note: str = "") -> dict[str, Any]:
        data = self._load(project_id)
        state = data["workflow"]
        self._require_status(state, WorkflowStatus.WAITING_FOR_HUMAN)
        if state.get("human_approval") != "pending":
            raise InvalidTransitionError("There is no pending approval request.")
        if approved:
            state["human_approval"] = "approved"
            state["status"] = WorkflowStatus.RUNNING.value
            state.pop("blocked_reason", None)
        else:
            state["human_approval"] = "rejected"
            state["status"] = WorkflowStatus.BLOCKED.value
            state["blocked_reason"] = note.strip() or "Human approval was rejected."
        return self._save(data)

    def block(self, project_id: str, reason: str) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("A non-empty block reason is required.")
        data = self._load(project_id)
        state = data["workflow"]
        self._require_status(state, WorkflowStatus.RUNNING)
        state["status"] = WorkflowStatus.BLOCKED.value
        state["blocked_reason"] = reason.strip()[:2000]
        return self._save(data)

    def fail(self, project_id: str, error: str) -> dict[str, Any]:
        if not error.strip():
            raise ValueError("A non-empty error description is required.")
        data = self._load(project_id)
        state = data["workflow"]
        self._require_status(state, WorkflowStatus.RUNNING)
        state["status"] = WorkflowStatus.FAILED.value
        state["last_error"] = error.strip()[:4000]
        return self._save(data)

    def retry(self, project_id: str) -> dict[str, Any]:
        data = self._load(project_id)
        state = data["workflow"]
        if state["status"] not in {WorkflowStatus.BLOCKED.value, WorkflowStatus.FAILED.value}:
            raise InvalidTransitionError("Only blocked or failed workflows can be retried.")
        if state.get("human_approval") == "rejected":
            state["human_approval"] = "not_requested"
        state["status"] = WorkflowStatus.READY.value
        state.pop("blocked_reason", None)
        state.pop("last_error", None)
        return self._save(data)

    def _load(self, project_id: str) -> dict[str, Any]:
        try:
            return self.store.load(project_id)
        except FileNotFoundError as exc:
            raise ProjectNotFoundError(project_id) from exc

    @staticmethod
    def _require_status(state: dict[str, Any], expected: WorkflowStatus) -> None:
        if state["status"] != expected.value:
            raise InvalidTransitionError(
                f"Operation requires status '{expected.value}', current status is '{state['status']}'."
            )

    def _save(self, data: dict[str, Any]) -> dict[str, Any]:
        data["workflow"]["updated_at"] = _now()
        self.store.save(data["project"], data["workflow"])
        return data
