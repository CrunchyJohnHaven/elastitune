from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.contracts import RunSnapshot
from ..models.report import ReportPayload


class PersistenceService:
    """SQLite-backed storage for completed search runs and reports."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or str(
            Path(__file__).resolve().parent.parent / "data" / "elastitune.db"
        )
        self._lock = asyncio.Lock()
        self._conn: Optional[sqlite3.Connection] = None

    async def init(self) -> None:
        await asyncio.to_thread(self._init_sync)

    async def close(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self._close_sync)

    async def save_connection(self, payload: Dict[str, Any]) -> None:
        async with self._lock:
            await asyncio.to_thread(self._save_connection_sync, payload)

    async def save_snapshot(self, snapshot: RunSnapshot) -> None:
        async with self._lock:
            await asyncio.to_thread(self._save_snapshot_sync, snapshot)

    async def save_report(self, report: ReportPayload) -> None:
        async with self._lock:
            await asyncio.to_thread(self._save_report_sync, report)

    async def load_snapshot(self, run_id: str) -> Optional[RunSnapshot]:
        row = await asyncio.to_thread(self._load_snapshot_row_sync, run_id)
        if not row:
            return None
        return RunSnapshot.model_validate(json.loads(row["snapshot_json"]))

    async def load_connection(self, connection_id: str) -> Optional[Dict[str, Any]]:
        row = await asyncio.to_thread(self._load_connection_row_sync, connection_id)
        if not row:
            return None
        return json.loads(row["payload_json"])

    async def load_report(self, run_id: str) -> Optional[ReportPayload]:
        row = await asyncio.to_thread(self._load_report_row_sync, run_id)
        if not row:
            return None
        return ReportPayload.model_validate(json.loads(row["report_json"]))

    async def list_runs(
        self,
        limit: int = 50,
        index_name: Optional[str] = None,
        completed_only: bool = False,
    ) -> List[Dict[str, Any]]:
        rows = await asyncio.to_thread(
            self._list_runs_sync, limit, index_name, completed_only
        )
        return [dict(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _close_sync(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _init_sync(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS search_connections (
                    connection_id TEXT PRIMARY KEY,
                    mode TEXT NOT NULL,
                    es_url TEXT,
                    api_key TEXT,
                    index_name TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS search_runs (
                    run_id TEXT PRIMARY KEY,
                    mode TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    index_name TEXT,
                    cluster_name TEXT,
                    baseline_score REAL,
                    best_score REAL,
                    improvement_pct REAL,
                    experiments_run INTEGER,
                    started_at TEXT,
                    completed_at TEXT,
                    snapshot_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS search_reports (
                    run_id TEXT PRIMARY KEY,
                    report_json TEXT NOT NULL,
                    generated_at TEXT NOT NULL
                );
                """
            )
            conn.commit()

    def _save_connection_sync(self, payload: Dict[str, Any]) -> None:
        sanitized_payload = self._sanitize_connection_payload(payload)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO search_connections (
                    connection_id, mode, es_url, api_key, index_name, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(connection_id) DO UPDATE SET
                    mode=excluded.mode,
                    es_url=excluded.es_url,
                    api_key=excluded.api_key,
                    index_name=excluded.index_name,
                    payload_json=excluded.payload_json,
                    created_at=excluded.created_at
                """,
                (
                    sanitized_payload["connection_id"],
                    sanitized_payload["mode"],
                    sanitized_payload.get("es_url"),
                    None,
                    sanitized_payload.get("index_name"),
                    json.dumps(sanitized_payload),
                    sanitized_payload["created_at"],
                ),
            )
            conn.commit()

    def _save_snapshot_sync(self, snapshot: RunSnapshot) -> None:
        payload = snapshot.model_dump()
        metrics = payload.get("metrics", {})
        summary = payload.get("summary", {})
        conn = self._connect()
        with conn:
            conn.execute(
                """
                INSERT INTO search_runs (
                    run_id, mode, stage, index_name, cluster_name,
                    baseline_score, best_score, improvement_pct, experiments_run,
                    started_at, completed_at, snapshot_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(run_id) DO UPDATE SET
                    mode=excluded.mode,
                    stage=excluded.stage,
                    index_name=excluded.index_name,
                    cluster_name=excluded.cluster_name,
                    baseline_score=excluded.baseline_score,
                    best_score=excluded.best_score,
                    improvement_pct=excluded.improvement_pct,
                    experiments_run=excluded.experiments_run,
                    started_at=excluded.started_at,
                    completed_at=excluded.completed_at,
                    snapshot_json=excluded.snapshot_json,
                    updated_at=datetime('now')
                """,
                (
                    snapshot.runId,
                    snapshot.mode,
                    snapshot.stage,
                    summary.get("indexName"),
                    summary.get("clusterName"),
                    metrics.get("baselineScore", 0.0),
                    metrics.get("bestScore", 0.0),
                    metrics.get("improvementPct", 0.0),
                    metrics.get("experimentsRun", 0),
                    snapshot.startedAt,
                    snapshot.completedAt,
                    json.dumps(payload),
                ),
            )

    def _save_report_sync(self, report: ReportPayload) -> None:
        sanitized_report = report.sanitize_for_client()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO search_reports (run_id, report_json, generated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    report_json=excluded.report_json,
                    generated_at=excluded.generated_at
                """,
                (
                    sanitized_report.runId,
                    sanitized_report.model_dump_json(),
                    sanitized_report.generatedAt,
                ),
            )
            conn.commit()

    def _load_snapshot_row_sync(self, run_id: str) -> Optional[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT snapshot_json FROM search_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()

    def _load_report_row_sync(self, run_id: str) -> Optional[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT report_json FROM search_reports WHERE run_id = ?",
                (run_id,),
            ).fetchone()

    def _load_connection_row_sync(self, connection_id: str) -> Optional[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT payload_json FROM search_connections WHERE connection_id = ?",
                (connection_id,),
            ).fetchone()

    def _list_runs_sync(
        self,
        limit: int,
        index_name: Optional[str],
        completed_only: bool,
    ) -> List[sqlite3.Row]:
        filters = []
        params: List[Any] = []
        if index_name:
            filters.append("index_name = ?")
            params.append(index_name)
        if completed_only:
            filters.append("stage = 'completed'")
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        with self._connect() as conn:
            return conn.execute(
                f"""
                SELECT
                    run_id,
                    mode,
                    stage,
                    index_name,
                    cluster_name,
                    baseline_score,
                    best_score,
                    improvement_pct,
                    experiments_run,
                    started_at,
                    completed_at,
                    updated_at
                FROM search_runs
                {where_clause}
                ORDER BY COALESCE(completed_at, updated_at) DESC
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()

    def _sanitize_connection_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = dict(payload)
        sanitized["api_key"] = None
        llm_config = sanitized.get("llm_config")
        if isinstance(llm_config, dict):
            llm_copy = dict(llm_config)
            llm_copy["apiKey"] = None
            sanitized["llm_config"] = llm_copy
        return sanitized
