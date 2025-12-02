from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from generate_stats import load_stats  # type: ignore  # noqa: E402


def build_test_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "ledger.sqlite"
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.executescript(
        """
        CREATE TABLE ActionIdentifiers (id INTEGER PRIMARY KEY, action_identifier TEXT NOT NULL);
        CREATE TABLE ObjectIdentifiers (id INTEGER PRIMARY KEY, identifier TEXT NOT NULL);
        CREATE TABLE worlds (id INTEGER PRIMARY KEY, identifier TEXT NOT NULL);
        CREATE TABLE players (id INTEGER PRIMARY KEY, player_id BLOB NOT NULL, player_name TEXT NOT NULL, first_join TEXT NOT NULL, last_join TEXT NOT NULL);
        CREATE TABLE sources (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE actions (
            id INTEGER PRIMARY KEY,
            action_id INT NOT NULL,
            time TEXT NOT NULL,
            x INT NOT NULL,
            y INT NOT NULL,
            z INT NOT NULL,
            world_id INT NOT NULL,
            object_id INT NOT NULL,
            old_object_id INT NOT NULL,
            block_state TEXT NULL,
            old_block_state TEXT NULL,
            source INT NOT NULL,
            player_id INT NULL,
            extra_data TEXT NULL,
            rolled_back BOOLEAN NOT NULL,
            FOREIGN KEY (action_id) REFERENCES ActionIdentifiers(id),
            FOREIGN KEY (world_id) REFERENCES worlds(id),
            FOREIGN KEY (object_id) REFERENCES ObjectIdentifiers(id),
            FOREIGN KEY (old_object_id) REFERENCES ObjectIdentifiers(id),
            FOREIGN KEY (source) REFERENCES sources(id),
            FOREIGN KEY (player_id) REFERENCES players(id)
        );
        """
    )

    # Lookup data
    cur.executemany(
        "INSERT INTO ActionIdentifiers (id, action_identifier) VALUES (?, ?);",
        [(1, "block-break"), (3, "block-place"), (8, "entity-kill")],
    )
    cur.executemany(
        "INSERT INTO ObjectIdentifiers (id, identifier) VALUES (?, ?);",
        [(10, "minecraft:air"), (11, "minecraft:dirt"), (12, "minecraft:stone"), (20, "minecraft:zombie")],
    )
    cur.execute("INSERT INTO worlds (id, identifier) VALUES (1, 'minecraft:overworld');")
    cur.execute(
        "INSERT INTO players (id, player_id, player_name, first_join, last_join) VALUES (1, X'00', 'Steve', '2025-01-01', '2025-01-02');"
    )
    cur.executemany(
        "INSERT INTO sources (id, name) VALUES (?, ?);",
        [(1, "player"), (2, "gravity")],
    )

    # Actions:
    # 1) Steve places dirt
    cur.execute(
        """
        INSERT INTO actions (id, action_id, time, x, y, z, world_id, object_id, old_object_id, block_state, old_block_state, source, player_id, extra_data, rolled_back)
        VALUES (1, 3, '2025-01-01 10:00:00', 0, 64, 0, 1, 11, 10, NULL, NULL, 1, 1, NULL, 0);
        """
    )
    # 2) Steve breaks stone
    cur.execute(
        """
        INSERT INTO actions (id, action_id, time, x, y, z, world_id, object_id, old_object_id, block_state, old_block_state, source, player_id, extra_data, rolled_back)
        VALUES (2, 1, '2025-01-01 10:05:00', 1, 64, 1, 1, 12, 11, NULL, NULL, 1, 1, NULL, 0);
        """
    )
    # 3) Steve kills a zombie
    cur.execute(
        """
        INSERT INTO actions (id, action_id, time, x, y, z, world_id, object_id, old_object_id, block_state, old_block_state, source, player_id, extra_data, rolled_back)
        VALUES (3, 8, '2025-01-01 10:10:00', 2, 64, 2, 1, 20, 20, NULL, NULL, 1, 1, NULL, 0);
        """
    )
    # 4) Environmental gravity event (no player)
    cur.execute(
        """
        INSERT INTO actions (id, action_id, time, x, y, z, world_id, object_id, old_object_id, block_state, old_block_state, source, player_id, extra_data, rolled_back)
        VALUES (4, 1, '2025-01-01 10:15:00', 3, 63, 3, 1, 12, 11, NULL, NULL, 2, NULL, NULL, 0);
        """
    )

    con.commit()
    con.close()
    return db_path


@pytest.fixture()
def stats(tmp_path: Path):
    db_path = build_test_db(tmp_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA temp_store = MEMORY;")
    yield load_stats(conn, limit=10)
    conn.close()


def test_totals(stats):
    assert stats["total_actions"] == 4
    mix = {entry["action"]: entry["actions"] for entry in stats["action_mix"]}
    assert mix == {"block-break": 2, "block-place": 1, "entity-kill": 1}


def test_players_and_building(stats):
    top = stats["top_players"]
    assert top[0]["player"] == "Steve"
    assert top[0]["actions"] == 3

    builders = stats["builders_vs_breakers"][0]
    assert builders["blocks_placed"] == 1
    assert builders["blocks_broken"] == 1


def test_blocks_and_mobs(stats):
    fav_blocks = {row["block"]: row["placed"] for row in stats["favorite_blocks_placed"]}
    assert fav_blocks.get("minecraft:dirt") == 1
    mobs = {row["mob"]: row["kills"] for row in stats["mob_kills"]}
    assert mobs.get("minecraft:zombie") == 1


def test_environment_and_hotspots(stats):
    causes = {row["cause"]: row["events"] for row in stats["environmental_causes"]}
    assert causes.get("gravity") == 1
    # All actions in same world/chunk
    hotspot = stats["hotspots"][0]
    assert hotspot["world"] == "minecraft:overworld"
    assert hotspot["actions"] == 4


def test_hourly(stats):
    hours = {row["hour"]: row["actions"] for row in stats["hourly_activity"]}
    assert hours.get("10") == 4
