"""SQLite 持久化：保存每次运行与报告路径。

表结构（也是 PPT "数据结构"那一页的素材）：

runs
  id            INTEGER PK
  created_at    TEXT     运行时间（ISO 8601）
  template_id   TEXT     实验模板 id
  model         TEXT     linear / power / exponential
  n_points      INTEGER  数据点数
  params_json   TEXT     参数估计 {"a": ..., "b": ...}
  cov_json      TEXT     参数协方差矩阵
  summary_json  TEXT     目标量、各项不确定度、置信水平

reports
  id            INTEGER PK
  run_id        INTEGER FK -> runs.id
  created_at    TEXT
  file_path     TEXT     本地报告路径
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "lab.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at   TEXT    NOT NULL,
    template_id  TEXT    NOT NULL,
    model        TEXT    NOT NULL,
    n_points     INTEGER NOT NULL,
    params_json  TEXT    NOT NULL,
    cov_json     TEXT    NOT NULL,
    summary_json TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    created_at TEXT    NOT NULL,
    file_path  TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_template ON runs(template_id);
CREATE INDEX IF NOT EXISTS idx_reports_run ON reports(run_id);
"""


def _connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def _session(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    connection = _connect(db_path)
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db(db_path: str | Path = DEFAULT_DB) -> None:
    with _session(db_path) as connection:
        connection.executescript(_SCHEMA)


def save_run(
    *,
    template_id: str,
    model: str,
    n_points: int,
    params: dict[str, float],
    cov,
    summary: dict[str, float],
    db_path: str | Path = DEFAULT_DB,
) -> int:
    """保存一次运行，返回 run_id。"""
    init_db(db_path)
    params_json = json.dumps({k: float(v) for k, v in params.items()}, ensure_ascii=False)
    cov_json = json.dumps(np.asarray(cov, dtype=float).tolist())
    summary_json = json.dumps({k: float(v) for k, v in summary.items()}, ensure_ascii=False)

    with _session(db_path) as connection:
        cursor = connection.execute(
            "INSERT INTO runs(created_at, template_id, model, n_points, "
            "params_json, cov_json, summary_json) VALUES(?,?,?,?,?,?,?)",
            (
                datetime.now().isoformat(timespec="seconds"),
                template_id,
                model,
                int(n_points),
                params_json,
                cov_json,
                summary_json,
            ),
        )
        return int(cursor.lastrowid)


def save_report(
    run_id: int,
    file_path: str | Path,
    db_path: str | Path = DEFAULT_DB,
) -> int:
    """记录一次报告导出，返回 report_id。"""
    init_db(db_path)
    with _session(db_path) as connection:
        cursor = connection.execute(
            "INSERT INTO reports(run_id, created_at, file_path) VALUES(?,?,?)",
            (int(run_id), datetime.now().isoformat(timespec="seconds"), str(file_path)),
        )
        return int(cursor.lastrowid)


def list_runs(limit: int = 20, db_path: str | Path = DEFAULT_DB) -> list[dict]:
    """按时间倒序列出最近的运行，用于以后做"历史记录"页面。"""
    init_db(db_path)
    with _session(db_path) as connection:
        rows = connection.execute(
            "SELECT id, created_at, template_id, model, n_points, summary_json "
            "FROM runs ORDER BY id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "created_at": row["created_at"],
            "template_id": row["template_id"],
            "model": row["model"],
            "n_points": row["n_points"],
            "summary": json.loads(row["summary_json"]),
        }
        for row in rows
    ]
