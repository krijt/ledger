#!/usr/bin/env python3
"""
Minimal Flask app to serve Minecraft ledger stats as JSON and a static page.

Usage:
    FLASK_APP=app.py FLASK_ENV=development flask run
Config:
    LEDGER_DB: path to ledger SQLite file (default: ledger.sqlite)
    STATS_LIMIT: max rows for leaderboard tables (default: 10)
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, send_from_directory

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from generate_stats import load_stats  # type: ignore  # noqa: E402
from log_stats import collect_stats  # type: ignore  # noqa: E402
import sqlite3  # noqa: E402

app = Flask(__name__, static_folder="public", static_url_path="")

_CACHE: dict[str, Any] = {}
_CACHE_TTL_SECONDS = int(os.getenv("STATS_CACHE_TTL", "1800"))  # default 30 minutes
_LOG_CACHE: dict[str, Any] = {}
_LOG_CACHE_TTL_SECONDS = int(os.getenv("LOG_STATS_CACHE_TTL", "600"))  # default 10 minutes


def get_db_path() -> Path:
    return Path(os.getenv("LEDGER_DB", "ledger.sqlite"))


def get_limit() -> int:
    try:
        return int(os.getenv("STATS_LIMIT", "10"))
    except ValueError:
        return 10


def get_logs_limit() -> int:
    try:
        return int(os.getenv("LOG_STATS_LIMIT", "5"))
    except ValueError:
        return 5


def get_logs_path() -> Path:
    return Path(os.getenv("LOGS_DIR", "logs"))


def fetch_stats() -> dict[str, Any]:
    now = time.time()
    cached = _CACHE.get("data")
    cached_at = _CACHE.get("ts", 0)
    if cached and (now - cached_at) < _CACHE_TTL_SECONDS:
        return cached

    db_path = get_db_path()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA temp_store = MEMORY;")
    try:
        stats = load_stats(conn, get_limit())
        _CACHE["data"] = stats
        _CACHE["ts"] = now
        return stats
    finally:
        conn.close()


def fetch_log_stats() -> dict[str, Any]:
    now = time.time()
    cached = _LOG_CACHE.get("data")
    cached_at = _LOG_CACHE.get("ts", 0)
    if cached and (now - cached_at) < _LOG_CACHE_TTL_SECONDS:
        return cached

    logs_path = get_logs_path()
    if not logs_path.exists():
        raise FileNotFoundError(f"Logs directory not found: {logs_path}")

    stats = collect_stats([logs_path], limit=get_logs_limit())
    _LOG_CACHE["data"] = stats
    _LOG_CACHE["ts"] = now
    return stats


@app.route("/api/stats")
def api_stats():
    stats = fetch_stats()
    return jsonify(stats)


@app.route("/api/log-stats")
def api_log_stats():
    stats = fetch_log_stats()
    return jsonify(stats)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def static_proxy(path: str):
    return send_from_directory(app.static_folder, path)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
