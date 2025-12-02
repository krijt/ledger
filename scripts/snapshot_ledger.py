#!/usr/bin/env python3
"""
Safely snapshot a live SQLite ledger using the SQLite backup API.

Usage:
    python scripts/snapshot_ledger.py --src /path/to/live/ledger.sqlite --dst /path/to/app/ledger.sqlite
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def snapshot(src: Path, dst: Path) -> None:
    if not src.exists():
        raise SystemExit(f"Source database not found: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Use read-only URI to avoid interfering with the live DB.
    src_conn = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    dst_conn = sqlite3.connect(dst)
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Snapshot a live SQLite ledger safely.")
    parser.add_argument("--src", required=True, type=Path, help="Path to the live ledger.sqlite in the world directory")
    parser.add_argument("--dst", default=Path("ledger.sqlite"), type=Path, help="Path to write the snapshot (default: ./ledger.sqlite)")
    args = parser.parse_args()

    snapshot(args.src, args.dst)
    print(f"Snapshot complete: {args.src} -> {args.dst}")


if __name__ == "__main__":
    main()
