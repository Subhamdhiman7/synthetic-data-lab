"""SQLite-backed metadata and safe local artifact storage."""

from __future__ import annotations

import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from uuid import UUID

from datagen.schemas import DatasetPlan


class StorageError(Exception):
    """Base class for safe storage errors."""


class NotFoundError(StorageError):
    """Requested metadata or artifact does not exist."""


class CorruptArtifactError(StorageError):
    """Stored JSON or generated artifact cannot be read safely."""


class LocalStorage:
    """Store plans, generated artifacts, and history under one application root."""

    _SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")

    def __init__(self, root: Path | str):
        self.root = Path(root).expanduser().resolve()
        self.plans_dir = self.root / "plans"
        # Keep internal paths short because Windows may enforce the legacy
        # MAX_PATH limit even when the public API uses descriptive names.
        self.generations_dir = self.root / "g"
        self.database_path = self.root / "history.sqlite3"
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.generations_dir.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _session(self):
        """Commit or roll back a transaction and always release the file handle."""
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _atomic_write_text(path: Path, content: str) -> None:
        temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
        try:
            temporary.write_text(content, encoding="utf-8")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def _initialize_database(self) -> None:
        with self._session() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS plans (
                    plan_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    name TEXT NOT NULL,
                    dataset_name TEXT NOT NULL,
                    task TEXT NOT NULL,
                    path TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS generations (
                    generation_id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    dataset_name TEXT NOT NULL,
                    task TEXT NOT NULL,
                    rows INTEGER NOT NULL,
                    feature_count INTEGER NOT NULL,
                    csv_path TEXT NOT NULL,
                    report_path TEXT NOT NULL,
                    plan_path TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_generations_created_at
                    ON generations(created_at DESC);
                """
            )

    @staticmethod
    def _uuid(value: UUID | str, label: str) -> UUID:
        try:
            return value if isinstance(value, UUID) else UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise NotFoundError(f"Unknown {label}.") from exc

    @classmethod
    def validate_dataset_name(cls, dataset_name: str) -> str:
        if not cls._SAFE_NAME.fullmatch(dataset_name):
            raise ValueError("Dataset name must contain only letters, numbers, '_' or '-'.")
        return dataset_name

    def _relative_path(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).as_posix()

    def _artifact_path(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise CorruptArtifactError("Stored artifact path is invalid.") from exc
        return candidate

    def _plan_path(self, plan_id: UUID) -> Path:
        return self.plans_dir / f"{plan_id}.json"

    def plan_path(self, plan_id: UUID | str) -> Path:
        """Return the validated internal path for a saved plan."""
        return self._plan_path(self._uuid(plan_id, "plan"))

    def save_plan(self, plan_id: UUID | str, plan: DatasetPlan) -> Dict[str, Any]:
        plan_uuid = self._uuid(plan_id, "plan")
        self.validate_dataset_name(plan.dataset_name)
        path = self._plan_path(plan_uuid)
        self._atomic_write_text(path, json.dumps(plan.model_dump(), indent=2))
        created_at = datetime.now(timezone.utc)
        with self._session() as connection:
            connection.execute(
                """INSERT OR REPLACE INTO plans
                   (plan_id, created_at, name, dataset_name, task, path)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    str(plan_uuid),
                    created_at.isoformat(),
                    plan.name,
                    plan.dataset_name,
                    plan.task,
                    self._relative_path(path),
                ),
            )
        return {"plan_id": plan_uuid, "created_at": created_at, "plan": plan}

    def load_plan(self, plan_id: UUID | str) -> DatasetPlan:
        plan_uuid = self._uuid(plan_id, "plan")
        path = self._plan_path(plan_uuid)
        if not path.is_file():
            raise NotFoundError("Saved plan was not found.")
        try:
            plan_data = json.loads(path.read_text(encoding="utf-8"))
            plan = DatasetPlan.model_validate(plan_data)
            self.validate_dataset_name(plan.dataset_name)
            return plan
        except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
            raise CorruptArtifactError("Saved plan is missing or corrupted.") from exc

    def get_plan_record(self, plan_id: UUID | str) -> Dict[str, Any]:
        plan_uuid = self._uuid(plan_id, "plan")
        with self._session() as connection:
            row = connection.execute(
                "SELECT * FROM plans WHERE plan_id = ?", (str(plan_uuid),)
            ).fetchone()
        if row is None:
            raise NotFoundError("Saved plan was not found.")
        return {
            "plan_id": plan_uuid,
            "created_at": datetime.fromisoformat(row["created_at"]),
            "plan": self.load_plan(plan_uuid),
        }

    def list_plans(self) -> list[Dict[str, Any]]:
        with self._session() as connection:
            rows = connection.execute(
                "SELECT * FROM plans ORDER BY created_at DESC"
            ).fetchall()
        return [
            {
                "plan_id": UUID(row["plan_id"]),
                "created_at": datetime.fromisoformat(row["created_at"]),
                "name": row["name"],
                "dataset_name": row["dataset_name"],
                "task": row["task"],
            }
            for row in rows
        ]

    def create_generation_directory(self, generation_id: UUID | str) -> Path:
        generation_uuid = self._uuid(generation_id, "generation")
        path = self.generations_dir / generation_uuid.hex[:12]
        if path.exists():
            path = self.generations_dir / generation_uuid.hex
        path.mkdir(parents=True, exist_ok=False)
        return path

    def record_generation(
        self,
        *,
        generation_id: UUID,
        plan_id: UUID,
        created_at: datetime,
        dataset_name: str,
        task: str,
        rows: int,
        feature_count: int,
        csv_path: Path,
        report_path: Path,
        plan_path: Path,
    ) -> Dict[str, Any]:
        record = {
            "generation_id": generation_id,
            "plan_id": plan_id,
            "created_at": created_at,
            "dataset_name": dataset_name,
            "task": task,
            "rows": rows,
            "feature_count": feature_count,
            "csv_path": self._relative_path(csv_path),
            "report_path": self._relative_path(report_path),
            "plan_path": self._relative_path(plan_path),
        }
        with self._session() as connection:
            connection.execute(
                """INSERT INTO generations
                   (generation_id, plan_id, created_at, dataset_name, task,
                    rows, feature_count, csv_path, report_path, plan_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(generation_id),
                    str(plan_id),
                    created_at.isoformat(),
                    dataset_name,
                    task,
                    rows,
                    feature_count,
                    record["csv_path"],
                    record["report_path"],
                    record["plan_path"],
                ),
            )
        return record

    @staticmethod
    def _generation_record(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "generation_id": UUID(row["generation_id"]),
            "plan_id": UUID(row["plan_id"]),
            "created_at": datetime.fromisoformat(row["created_at"]),
            "dataset_name": row["dataset_name"],
            "task": row["task"],
            "rows": row["rows"],
            "feature_count": row["feature_count"],
            "csv_path": row["csv_path"],
            "report_path": row["report_path"],
            "plan_path": row["plan_path"],
        }

    def get_generation(self, generation_id: UUID | str) -> Dict[str, Any]:
        generation_uuid = self._uuid(generation_id, "generation")
        with self._session() as connection:
            row = connection.execute(
                "SELECT * FROM generations WHERE generation_id = ?",
                (str(generation_uuid),),
            ).fetchone()
        if row is None:
            raise NotFoundError("Dataset generation was not found.")
        return self._generation_record(row)

    def list_generations(self, limit: int, offset: int) -> tuple[list[Dict[str, Any]], int]:
        with self._session() as connection:
            total = connection.execute("SELECT COUNT(*) FROM generations").fetchone()[0]
            rows = connection.execute(
                """SELECT * FROM generations ORDER BY created_at DESC
                   LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()
        return [self._generation_record(row) for row in rows], total

    def artifact_path_for(self, record: Dict[str, Any], key: str) -> Path:
        path = self._artifact_path(record[key])
        if not path.is_file():
            raise NotFoundError("Requested dataset artifact was not found.")
        return path
