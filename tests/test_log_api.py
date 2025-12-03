from __future__ import annotations

import gzip
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def write_log(path: Path, content: str) -> None:
    if path.suffix == ".gz":
        with gzip.open(path, "wt", encoding="utf-8") as fh:
            fh.write(content)
    else:
        path.write_text(content, encoding="utf-8")


@pytest.fixture()
def log_dir(tmp_path: Path) -> Path:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    sample = """\
[07:00:00] [Server thread/INFO]: Alice[/1.1.1.1:12345] logged in with entity id 1 at (0, 0, 0)
[07:10:00] [Server thread/INFO]: Alice has made the advancement [Stone Age]
[07:20:00] [Server thread/INFO]: Alice lost connection: Disconnected
[07:20:00] [Server thread/INFO]: Alice left the game
"""
    write_log(logs_dir / "2025-01-01-1.log.gz", sample)
    return logs_dir


def test_api_log_stats(monkeypatch: pytest.MonkeyPatch, log_dir: Path) -> None:
    monkeypatch.setenv("LOGS_DIR", str(log_dir))
    monkeypatch.setenv("LOG_STATS_LIMIT", "3")

    import importlib

    app_module = importlib.import_module("app")
    client = app_module.app.test_client()

    resp = client.get("/api/log-stats")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["top_advancements"][0]["name"] == "Alice"
    assert data["top_playtime"][0]["player"] == "Alice"
