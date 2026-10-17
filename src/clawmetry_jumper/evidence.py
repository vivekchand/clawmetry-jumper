"""Bounded local evidence for the Jumper simulation.

The simulator and Flask should share one EvidenceStore object. DuckDB does not
support a writer in one process with a reader in another process. A completed
database can instead be opened with ``read_only=True``.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
import threading

import duckdb

KINDS = frozenset({"request", "decision", "controller", "outcome", "observation", "reminder", "alert", "notification"})
MAX_LIMIT = 1000
MAX_PAYLOAD_BYTES = 65536
_RUN_ID = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_LOCK = threading.Lock()


def validate_run_id(value: str) -> str:
    if not isinstance(value, str) or not _RUN_ID.fullmatch(value):
        raise ValueError("Run ID must contain 1 to 128 letters, digits, dots, colons, underscores or hyphens")
    return value


def validate_limit(value: int) -> int:
    if type(value) is not int or not 1 <= value <= MAX_LIMIT:
        raise ValueError(f"Limit must be an integer from 1 to {MAX_LIMIT}")
    return value


class EvidenceStore:
    """One locked connection, persisted locally, with explicit read-only mode."""

    def __init__(self, path: str | Path, *, read_only: bool = False):
        if type(read_only) is not bool:
            raise ValueError("Read-only mode must be an explicit boolean")
        self.path = str(path) if str(path) == ":memory:" else str(Path(path).expanduser().resolve())
        self.read_only = read_only
        with _LOCKS_LOCK:
            self._lock = _LOCKS.setdefault(self.path, threading.RLock())
        self._db = None
        with self._lock:
            if not read_only and self.path != ":memory:":
                Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            db = duckdb.connect(self.path, read_only=read_only, config={"threads": 1})
            try:
                if not read_only:
                    db.execute("CREATE SEQUENCE IF NOT EXISTS jumper_event_id START 1")
                    db.execute("""CREATE TABLE IF NOT EXISTS jumper_evidence (
                        event_id BIGINT PRIMARY KEY DEFAULT nextval('jumper_event_id'),
                        run_id VARCHAR NOT NULL, sim_time_s DOUBLE NOT NULL,
                        kind VARCHAR NOT NULL, payload VARCHAR NOT NULL
                    )""")
                    db.execute("CREATE INDEX IF NOT EXISTS jumper_run ON jumper_evidence (run_id, event_id)")
                else:
                    db.execute("SELECT event_id, run_id, sim_time_s, kind, payload FROM jumper_evidence LIMIT 0")
            except BaseException:
                db.close()
                raise
            self._db = db

    def _connection(self):
        if self._db is None:
            raise RuntimeError("Evidence store is closed")
        return self._db

    def append(self, run_id: str, sim_time_s: float, kind: str, payload: dict) -> int:
        validate_run_id(run_id)
        if isinstance(sim_time_s, bool) or not isinstance(sim_time_s, (int, float)):
            raise ValueError("Simulation time must be a finite nonnegative number")
        try:
            valid_time = math.isfinite(sim_time_s) and 0 <= sim_time_s <= 1e12
        except OverflowError:
            valid_time = False
        if not valid_time:
            raise ValueError("Simulation time must be a finite nonnegative number")
        if not isinstance(kind, str) or kind not in KINDS:
            raise ValueError("Unsupported evidence kind")
        if not isinstance(payload, dict):
            raise ValueError("Evidence payload must be an object")
        try:
            encoded = json.dumps(payload, allow_nan=False, ensure_ascii=False, separators=(",", ":"))
            if len(encoded.encode("utf-8")) > MAX_PAYLOAD_BYTES:
                raise ValueError("Evidence payload exceeds 64 KiB")
        except (TypeError, OverflowError, RecursionError, UnicodeError) as error:
            raise ValueError("Evidence payload must contain finite JSON values") from error
        with self._lock:
            db = self._connection()
            if self.read_only:
                raise PermissionError("Completed evidence is open read only")
            row = db.execute(
                "INSERT INTO jumper_evidence (run_id, sim_time_s, kind, payload) VALUES (?, ?, ?, ?) RETURNING event_id",
                [run_id, float(sim_time_s), kind, encoded],
            ).fetchone()
            return row[0]

    def events(self, run_id: str | None = None, limit: int = 200) -> list[dict]:
        validate_limit(limit)
        if run_id is not None:
            validate_run_id(run_id)
        where, args = ("WHERE run_id = ?", [run_id]) if run_id is not None else ("", [])
        with self._lock:
            rows = self._connection().execute(
                f"SELECT event_id, run_id, sim_time_s, kind, payload FROM jumper_evidence {where} ORDER BY event_id DESC LIMIT ?",
                [*args, limit],
            ).fetchall()
        return [dict(event_id=row[0], run_id=row[1], sim_time_s=row[2], kind=row[3], payload=json.loads(row[4]))
                for row in reversed(rows)]

    def runs(self) -> list[dict]:
        """At most 100 recent runs, ordered by their last persisted event."""
        with self._lock:
            rows = self._connection().execute("""
                SELECT run_id, count(*), min(sim_time_s), max(sim_time_s), max(event_id)
                FROM jumper_evidence GROUP BY run_id ORDER BY max(event_id) DESC LIMIT 100
            """).fetchall()
        return [dict(run_id=row[0], event_count=row[1], started_sim_time_s=row[2],
                     latest_sim_time_s=row[3], last_event_id=row[4]) for row in rows]

    def close(self) -> None:
        with self._lock:
            if self._db is not None:
                self._db.close()
                self._db = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
