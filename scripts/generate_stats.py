#!/usr/bin/env python3
"""
Generate fun Minecraft ledger stats from a Ledger SQLite file.

Usage:
    python scripts/generate_stats.py --db ledger.sqlite [--format markdown|json]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable, List, Sequence


def _rows(conn: sqlite3.Connection, query: str, params: Sequence[Any] = ()) -> List[sqlite3.Row]:
    cur = conn.execute(query, params)
    return cur.fetchall()


def load_stats(conn: sqlite3.Connection, limit: int) -> dict[str, Any]:
    stats: dict[str, Any] = {}

    stats["total_actions"] = conn.execute("SELECT COUNT(*) FROM actions").fetchone()[0]

    stats["world_counts"] = [
        dict(row)
        for row in _rows(
            conn,
            """
            SELECT w.identifier AS world, COUNT(*) AS actions
            FROM actions a
            JOIN worlds w ON w.id = a.world_id
            GROUP BY w.identifier
            ORDER BY actions DESC
            """,
        )
    ]

    stats["action_mix"] = [
        dict(row)
        for row in _rows(
            conn,
            """
            SELECT ai.action_identifier AS action, COUNT(*) AS actions
            FROM actions a
            JOIN ActionIdentifiers ai ON ai.id = a.action_id
            GROUP BY ai.action_identifier
            ORDER BY actions DESC
            """,
        )
    ]

    stats["top_players"] = [
        dict(row)
        for row in _rows(
            conn,
            """
            SELECT p.player_name AS player, COUNT(*) AS actions
            FROM actions a
            JOIN players p ON p.id = a.player_id
            GROUP BY p.player_name
            ORDER BY actions DESC
            LIMIT ?
            """,
            (limit,),
        )
    ]

    stats["builders_vs_breakers"] = [
        dict(row)
        for row in _rows(
            conn,
            """
            SELECT
                p.player_name AS player,
                SUM(a.action_id = 3) AS blocks_placed,
                SUM(a.action_id = 1) AS blocks_broken
            FROM actions a
            JOIN players p ON p.id = a.player_id
            GROUP BY p.player_name
            ORDER BY blocks_placed DESC
            LIMIT ?
            """,
            (limit,),
        )
    ]

    stats["favorite_blocks_placed"] = [
        dict(row)
        for row in _rows(
            conn,
            """
            SELECT o.identifier AS block, COUNT(*) AS placed
            FROM actions a
            JOIN ObjectIdentifiers o ON o.id = a.object_id
            WHERE a.action_id = 3
            GROUP BY o.identifier
            ORDER BY placed DESC
            LIMIT ?
            """,
            (limit,),
        )
    ]

    stats["deadliest_players"] = [
        dict(row)
        for row in _rows(
            conn,
            """
            SELECT p.player_name AS player, COUNT(*) AS kills
            FROM actions a
            JOIN players p ON p.id = a.player_id
            WHERE a.action_id = 8
            GROUP BY p.player_name
            ORDER BY kills DESC
            LIMIT ?
            """,
            (limit,),
        )
    ]

    stats["mob_kills"] = [
        dict(row)
        for row in _rows(
            conn,
            """
            SELECT o.identifier AS mob, COUNT(*) AS kills
            FROM actions a
            JOIN ObjectIdentifiers o ON o.id = a.object_id
            WHERE a.action_id = 8
            GROUP BY o.identifier
            ORDER BY kills DESC
            LIMIT ?
            """,
            (limit,),
        )
    ]

    stats["environmental_causes"] = [
        dict(row)
        for row in _rows(
            conn,
            """
            SELECT s.name AS cause, COUNT(*) AS events
            FROM actions a
            JOIN sources s ON s.id = a.source
            WHERE a.player_id IS NULL
            GROUP BY s.name
            ORDER BY events DESC
            LIMIT ?
            """,
            (limit,),
        )
    ]

    stats["hotspots"] = [
        dict(row)
        for row in _rows(
            conn,
            """
            SELECT
                w.identifier AS world,
                CAST(a.x / 16 AS INT) AS chunk_x,
                CAST(a.z / 16 AS INT) AS chunk_z,
                COUNT(*) AS actions
            FROM actions a
            JOIN worlds w ON w.id = a.world_id
            GROUP BY w.identifier, chunk_x, chunk_z
            ORDER BY actions DESC
            LIMIT ?
            """,
            (limit,),
        )
    ]

    stats["hourly_activity"] = [
        dict(row)
        for row in _rows(
            conn,
            """
            SELECT strftime('%H', time) AS hour, COUNT(*) AS actions
            FROM actions
            GROUP BY hour
            ORDER BY actions DESC
            """,
        )
    ]

    return stats


def table(headers: Iterable[str], rows: Iterable[Iterable[Any]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    body = "\n".join("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)
    return "\n".join([head, sep, body]) if body else "\n".join([head, sep, "| (none) |"])


def format_markdown(stats: dict[str, Any]) -> str:
    lines = []
    lines.append("# Minecraft World Stats")
    lines.append("")
    lines.append(f"- Total actions recorded: **{stats['total_actions']}**")
    lines.append(
        "- World split: "
        + ", ".join(f"{row['world']} ({row['actions']})" for row in stats["world_counts"])
    )
    lines.append("")

    lines.append("## Action Mix")
    lines.append(table(["Action", "Count"], ((r["action"], r["actions"]) for r in stats["action_mix"])))
    lines.append("")

    lines.append("## Top Players (by actions)")
    lines.append(table(["Player", "Actions"], ((r["player"], r["actions"]) for r in stats["top_players"])))
    lines.append("")

    lines.append("## Builders vs Breakers")
    lines.append(
        table(
            ["Player", "Blocks Placed", "Blocks Broken"],
            ((r["player"], r["blocks_placed"], r["blocks_broken"]) for r in stats["builders_vs_breakers"]),
        )
    )
    lines.append("")

    lines.append("## Favorite Blocks Placed")
    lines.append(table(["Block", "Placed"], ((r["block"], r["placed"]) for r in stats["favorite_blocks_placed"])))
    lines.append("")

    lines.append("## Deadliest Players")
    lines.append(table(["Player", "Kills"], ((r["player"], r["kills"]) for r in stats["deadliest_players"])))
    lines.append("")

    lines.append("## Most Killed Mobs")
    lines.append(table(["Mob", "Kills"], ((r["mob"], r["kills"]) for r in stats["mob_kills"])))
    lines.append("")

    lines.append("## Top Environmental Causes (no player)")
    lines.append(table(["Cause", "Events"], ((r["cause"], r["events"]) for r in stats["environmental_causes"])))
    lines.append("")

    lines.append("## Hottest Chunks")
    lines.append(
        table(
            ["World", "Chunk X", "Chunk Z", "Actions"],
            ((r["world"], r["chunk_x"], r["chunk_z"], r["actions"]) for r in stats["hotspots"]),
        )
    )
    lines.append("")

    lines.append("## Hourly Activity (server time)")
    lines.append(table(["Hour", "Actions"], ((r["hour"], r["actions"]) for r in stats["hourly_activity"])))

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate fun Minecraft ledger stats.")
    parser.add_argument("--db", default="ledger.sqlite", type=Path, help="Path to ledger SQLite file")
    parser.add_argument("--limit", default=10, type=int, help="Row limit for leaderboards")
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format (markdown for human-readable, json for programmatic use)",
    )
    args = parser.parse_args()

    if not args.db.exists():
        raise SystemExit(f"Database file not found: {args.db}")

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA temp_store = MEMORY;")

    stats = load_stats(conn, args.limit)
    if args.format == "markdown":
        print(format_markdown(stats))
    else:
        print(json.dumps(stats, indent=2))

    conn.close()


if __name__ == "__main__":
    main()
