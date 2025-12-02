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
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, send_from_directory

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from generate_stats import load_stats  # type: ignore  # noqa: E402
import sqlite3  # noqa: E402

app = Flask(__name__, static_folder="public", static_url_path="")


def get_db_path() -> Path:
    return Path(os.getenv("LEDGER_DB", "ledger.sqlite"))


def get_limit() -> int:
    try:
        return int(os.getenv("STATS_LIMIT", "10"))
    except ValueError:
        return 10


def fetch_stats() -> dict[str, Any]:
    db_path = get_db_path()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA temp_store = MEMORY;")
    try:
        return load_stats(conn, get_limit())
    finally:
        conn.close()


@app.route("/api/stats")
def api_stats():
    stats = fetch_stats()
    return jsonify(stats)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def static_proxy(path: str):
    return send_from_directory(app.static_folder, path)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
