from __future__ import annotations

import gzip
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from log_stats import collect_stats  # type: ignore  # noqa: E402


def write_log(path: Path, content: str) -> None:
    if path.suffix == ".gz":
        with gzip.open(path, "wt", encoding="utf-8") as fh:
            fh.write(content)
    else:
        path.write_text(content, encoding="utf-8")


def test_collect_stats_from_logs(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    primary_log = """\
[09:00:00] [Server thread/INFO]: Alice[/1.1.1.1:12345] logged in with entity id 1 at (0, 0, 0)
[09:10:00] [Server thread/INFO]: Alice has made the advancement [Stone Age]
[09:20:00] [Server thread/INFO]: Alice fell from a high place
[09:30:00] [Server thread/INFO]: Alice lost connection: Disconnected
[09:30:00] [Server thread/INFO]: Alice left the game
[10:00:00] [Server thread/INFO]: Bob[/2.2.2.2:2000] logged in with entity id 2 at (0, 0, 0)
[10:05:00] [Server thread/INFO]: Named entity class_1646['VillagerBob'/1, l='ServerLevel[world]', x=0.0, y=0.0, z=0.0] died: VillagerBob was slain by Alice
[10:10:00] [Server thread/INFO]: Bob has made the advancement [Acquire Hardware]
[10:20:00] [Server thread/INFO]: Bob lost connection: Disconnected
[10:20:00] [Server thread/INFO]: Bob left the game
[10:25:00] [Server thread/INFO]: Bob[/2.2.2.2:2001] logged in with entity id 3 at (0, 0, 0)
[10:25:30] [Server thread/INFO]: Bob lost connection: Timed out
[10:25:30] [Server thread/INFO]: Bob left the game
"""

    gz_log = """\
[11:00:00] [Server thread/INFO]: Charlie[/3.3.3.3:123] logged in with entity id 4 at (0, 0, 0)
[11:05:00] [Server thread/INFO]: Charlie was slain by Enderman
[11:10:00] [Server thread/INFO]: Charlie lost connection: Disconnected
[11:10:00] [Server thread/INFO]: Charlie left the game
"""

    write_log(logs_dir / "2025-12-31-1.log", primary_log)
    write_log(logs_dir / "2026-01-01-1.log.gz", gz_log)

    stats = collect_stats([logs_dir], limit=5)

    playtime = {row["player"]: row for row in stats["top_playtime"]}
    assert playtime["Alice"]["seconds"] == 1800
    assert playtime["Bob"]["sessions"] == 2

    advancements = {row["name"]: row["count"] for row in stats["top_advancements"]}
    assert advancements["Alice"] == 1
    assert advancements["Bob"] == 1

    player_deaths = {row["player"]: row["deaths"] for row in stats["top_player_deaths"]}
    assert player_deaths["Alice"] == 1
    assert player_deaths["Charlie"] == 1

    villager_killers = {row["name"]: row["villagers"] for row in stats["top_villager_killers"]}
    assert villager_killers["Alice"] == 1

    churn = {row["player"]: row for row in stats["connection_churn"]}
    assert churn["Bob"]["disconnects"] == 2
    assert churn["Bob"]["short_sessions"] == 1
