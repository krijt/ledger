#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${DB_PATH:-ledger.sqlite}"
OUT_DIR="${OUT_DIR:-public}"

mkdir -p "$OUT_DIR"

python "$(dirname "$0")/generate_stats.py" --db "$DB_PATH" --format json > "$OUT_DIR/stats.json"
python "$(dirname "$0")/generate_stats.py" --db "$DB_PATH" --format markdown > "$OUT_DIR/stats.md"

echo "Stats refreshed -> $OUT_DIR (db: $DB_PATH)"
