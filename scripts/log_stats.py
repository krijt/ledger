#!/usr/bin/env python3
"""
Parse Minecraft server logs and emit top stats (playtime, deaths, advancements, etc.).

Usage:
    python scripts/log_stats.py logs/ --limit 5 --format json
Supports plain `.log` and `.log.gz` files; dates are inferred from file names like `YYYY-MM-DD-*.log.gz`.
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator

LOGIN_RE = re.compile(
    r"\[(?P<time>\d{2}:\d{2}:\d{2})] \[Server thread/INFO\]: (?P<player>[A-Za-z0-9_]+)\[/.*\] logged in"
)
LEAVE_RE = re.compile(
    r"\[(?P<time>\d{2}:\d{2}:\d{2})] \[Server thread/INFO\]: (?P<player>[A-Za-z0-9_]+) (left the game|lost connection: .*)"
)
ADVANCEMENT_RE = re.compile(
    r"\[(?P<time>\d{2}:\d{2}:\d{2})] \[Server thread/INFO\]: (?P<player>[A-Za-z0-9_]+) has made the advancement \[(?P<adv>.+?)\]"
)
PLAYER_DEATH_RE = re.compile(
    r"\[(?P<time>\d{2}:\d{2}:\d{2})] \[Server thread/INFO\]: (?P<player>[A-Za-z0-9_]+) (?P<cause>("
    r"fell from a high place|fell off a ladder|fell out of the world|hit the ground too hard|"
    r"was slain by .+|was shot by .+|was blown up by .+|was doomed to fall by .+|was killed by .+|"
    r"burned to death|tried to swim in lava|drowned|experienced kinetic energy|blew up|"
    r"withered away|starved to death|died"
    r"))"
)
VILLAGER_DEATH_RE = re.compile(
    r"\[(?P<time>\d{2}:\d{2}:\d{2})] \[Server thread/INFO\]: (?:Named entity|Villager) .* died[:,] (?:message:\s*)?'?(?P<msg>.+?)'?$"
)


def _parse_date_from_path(path: Path) -> datetime.date | None:
    match = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    if not match:
        return None
    return datetime.strptime(match.group(1), "%Y-%m-%d").date()


def _iter_lines(path: Path) -> Iterator[str]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as fh:
            yield from fh
    else:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            yield from fh


def _iter_log_files(paths: Iterable[Path]) -> Iterator[Path]:
    for p in paths:
        if p.is_dir():
            for child in sorted(p.iterdir()):
                if child.suffix in {".log", ".gz"}:
                    yield child
        elif p.is_file():
            yield p


def _combine_timestamp(log_date: datetime.date | None, time_str: str) -> datetime:
    if log_date is None:
        today = datetime.today().date()
        log_date = today
    return datetime.strptime(f"{log_date} {time_str}", "%Y-%m-%d %H:%M:%S")


def collect_stats(paths: Iterable[Path], limit: int = 5) -> dict[str, object]:
    playtime = Counter()
    sessions = Counter()
    session_start: dict[str, datetime] = {}
    advancements = Counter()
    player_deaths = Counter()
    death_causes = Counter()
    villager_killers = Counter()
    disconnects = Counter()
    short_sessions = Counter()

    for log_path in _iter_log_files(paths):
        log_date = _parse_date_from_path(log_path)
        for line in _iter_lines(log_path):
            login_match = LOGIN_RE.search(line)
            if login_match:
                ts = _combine_timestamp(log_date, login_match.group("time"))
                player = login_match.group("player")
                session_start[player] = ts
                continue

            leave_match = LEAVE_RE.search(line)
            if leave_match:
                ts = _combine_timestamp(log_date, leave_match.group("time"))
                player = leave_match.group("player")
                disconnects[player] += 1
                start = session_start.pop(player, None)
                if start and ts >= start:
                    duration = (ts - start).total_seconds()
                    playtime[player] += duration
                    sessions[player] += 1
                    if duration <= 60:
                        short_sessions[player] += 1
                continue

            adv_match = ADVANCEMENT_RE.search(line)
            if adv_match:
                player = adv_match.group("player")
                advancements[player] += 1
                continue

            death_match = PLAYER_DEATH_RE.search(line)
            if death_match:
                player = death_match.group("player")
                cause = death_match.group("cause")
                player_deaths[player] += 1
                death_causes[cause] += 1
                continue

            villager_match = VILLAGER_DEATH_RE.search(line)
            if villager_match:
                msg = villager_match.group("msg")
                killer_match = re.search(r" by ([A-Za-z0-9_]+)$", msg)
                if killer_match:
                    killer = killer_match.group(1)
                    villager_killers[killer] += 1
                cause_match = re.search(r"(?P<victim>.+?) (was .+)", msg)
                cause = cause_match.group(2) if cause_match else msg
                death_causes[cause] += 1
                continue

    # Close any dangling sessions without an end marker (ignore to avoid guessing end time)

    def top_playtime() -> list[dict[str, object]]:
        rows = sorted(playtime.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        return [
            {"player": player, "seconds": seconds, "sessions": sessions.get(player, 0)}
            for player, seconds in rows
        ]

    def top_counter(counter: Counter) -> list[dict[str, object]]:
        return [{"name": name, "count": count} for name, count in counter.most_common(limit)]

    def connection_churn() -> list[dict[str, object]]:
        rows = sorted(disconnects.items(), key=lambda kv: (kv[1], short_sessions.get(kv[0], 0)), reverse=True)[
            :limit
        ]
        return [
            {
                "player": player,
                "disconnects": disconnect_count,
                "short_sessions": short_sessions.get(player, 0),
            }
            for player, disconnect_count in rows
        ]

    return {
        "top_playtime": top_playtime(),
        "top_advancements": top_counter(advancements),
        "top_player_deaths": [{"player": p, "deaths": c} for p, c in player_deaths.most_common(limit)],
        "top_death_causes": [{"cause": name, "events": count} for name, count in death_causes.most_common(limit)],
        "top_villager_killers": [{"name": name, "villagers": count} for name, count in villager_killers.most_common(limit)],
        "connection_churn": connection_churn(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate top stats from Minecraft server logs.")
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Log files or directories containing .log / .log.gz files.",
    )
    parser.add_argument("--limit", type=int, default=5, help="Row limit for each leaderboard.")
    parser.add_argument(
        "--format",
        choices=("json",),
        default="json",
        help="Output format (currently only json).",
    )
    args = parser.parse_args()

    stats = collect_stats(args.paths, limit=args.limit)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
