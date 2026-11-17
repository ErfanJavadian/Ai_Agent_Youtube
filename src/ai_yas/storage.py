"""Filesystem persistence for project manifests and workflow state."""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")


class ProjectStore:
    """Stores one project per directory using atomic JSON file replacement.

    Concurrent writers are not supported in this first implementation.
    The store rejects path-like project IDs and never deletes project data.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, project: dict[str, Any], workflow: dict[str, Any]) -> None:
        project_id = self._validate_id(project.get("project_id"))
        if workflow.get("project_id") != project_id:
            raise ValueError("Project and workflow IDs must match.")
        directory = self._project_dir(project_id)
        if directory.exists():
            raise FileExistsError(f"Project already exists: {project_id}")
        directory.mkdir(parents=False)
        try:
            self._atomic_write(directory / "project.json", project)
            self._atomic_write(directory / "workflow_state.json", workflow)
        except Exception:
            # Do not leave a half-created project directory.
            for child in directory.iterdir():
                child.unlink(missing_ok=True)
            directory.rmdir()
            raise

    def load(self, project_id: str) -> dict[str, Any]:
        directory = self._project_dir(project_id)
        project_path = directory / "project.json"
        workflow_path = directory / "workflow_state.json"
        if not project_path.is_file() or not workflow_path.is_file():
            raise FileNotFoundError(f"Project data not found: {project_id}")
        project = self._read_json(project_path)
        workflow = self._read_json(workflow_path)
        if project.get("project_id") != project_id or workflow.get("project_id") != project_id:
            raise ValueError("Stored project identity does not match its directory.")
        return {"project": project, "workflow": workflow}

    def save(self, project: dict[str, Any], workflow: dict[str, Any]) -> None:
        project_id = self._validate_id(project.get("project_id"))
        if workflow.get("project_id") != project_id:
            raise ValueError("Project and workflow IDs must match.")
        directory = self._project_dir(project_id)
        if not directory.is_dir():
            raise FileNotFoundError(f"Project data not found: {project_id}")
        self._atomic_write(directory / "project.json", project)
        self._atomic_write(directory / "workflow_state.json", workflow)

    def _project_dir(self, project_id: str) -> Path:
        safe_id = self._validate_id(project_id)
        path = (self.root / safe_id).resolve()
        if path.parent != self.root:
            raise ValueError("Project path escapes the configured storage root.")
        return path

    @staticmethod
    def _validate_id(project_id: Any) -> str:
        if not isinstance(project_id, str) or not PROJECT_ID_RE.fullmatch(project_id):
            raise ValueError("project_id must be 2-64 safe alphanumeric, dot, underscore, or hyphen characters.")
        if project_id in {".", ".."}:
            raise ValueError("Invalid project_id.")
        return project_id

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            raise ValueError(f"Expected a JSON object in {path.name}.")
        return value

    @staticmethod
    def _atomic_write(path: Path, value: dict[str, Any]) -> None:
        fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
        except Exception:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise
