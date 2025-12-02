# Minecraft Ledger Stats

Fun stats dashboard for a Minecraft world backed by a Ledger SQLite database. Provides a web UI (Flask) and JSON API, plus CLI generators for Markdown/JSON snapshots.

## Quick Start (Local)
```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
LEDGER_DB=ledger.sqlite FLASK_APP=app.py FLASK_ENV=development flask run  # http://localhost:5000
```
- Env vars: `LEDGER_DB` (path to ledger file), `STATS_LIMIT` (leaderboard rows, default 10), `PORT` (default 5000).

## Docker
```bash
docker build -t mc-ledger-stats .
docker run --rm -p 5000:5000 \
  -v $(pwd)/ledger.sqlite:/app/ledger.sqlite:ro \
  -e LEDGER_DB=/app/ledger.sqlite \
  -e STATS_LIMIT=10 \
  mc-ledger-stats:latest
```
Visit `http://localhost:5000` for the UI, `/api/stats` for JSON. Change port with `-e PORT=8080 -p 8080:8080`.

### Deployment image & auto-redeploy script
- Production Dockerfile: `Dockerfile.deploy` (build the same way as the main Dockerfile).
- Auto-pull/redeploy helper:
  ```bash
  IMAGE=mc-ledger-stats:latest \
  CONTAINER_NAME=mc-ledger-stats \
  LEDGER_DB=/path/to/ledger.sqlite \
  PORT=5000 \
  ./scripts/watch_and_deploy.sh
  ```
  The script pulls the image, compares digests, and restarts the container only when the image changes.

## Snapshots & Cron (for live Minecraft worlds)
- Safe snapshot of the live ledger DB (uses SQLite backup API, read-only source):
  ```bash
  python scripts/snapshot_ledger.py --src /path/to/world/ledger.sqlite --dst /path/to/app/ledger.sqlite
  ```
- Suggested cron (every 30 minutes) to refresh the snapshot and warm the API cache:
  ```
  */30 * * * * python /path/to/repo/scripts/snapshot_ledger.py --src /path/to/world/ledger.sqlite --dst /path/to/app/ledger.sqlite && curl -fsS http://localhost:5000/api/stats > /dev/null
  ```
  - `--src` points at the live world DB; `--dst` is the copy the app reads.
  - The `curl` hit populates the in-app cache (TTL controlled by `STATS_CACHE_TTL`, default 30 minutes).

## Docker Compose
Bring up the stack with your ledger mounted:
```bash
LEDGER_DB_PATH=/absolute/path/to/ledger.sqlite \
PORT=5000 \
docker-compose up -d
```
Environment defaults: `STATS_LIMIT=10`, `STATS_CACHE_TTL=1800`, `PORT=5000`. For Swarm (`docker stack deploy`), pre-build/push `mc-ledger-stats:latest` and ensure the ledger path is available on the node (or use a shared volume).

Swarm example (single node, prebuilt image):
```bash
LEDGER_DB_PATH=/absolute/path/to/ledger.sqlite \
PORT=5000 \
docker stack deploy -c docker-compose.yml siemcraft
```

## Endpoints
- `/` serves the React-free static page from `public/index.html`.
- `/api/stats` returns cached JSON computed from the SQLite DB. Cache TTL defaults to 30 minutes; override with `STATS_CACHE_TTL` (seconds).

## Scripts
- `python scripts/generate_stats.py --db ledger.sqlite --limit 10 --format markdown|json`  
  Generate stats to stdout.
- `./scripts/refresh_stats.sh`  
  Writes `public/stats.json` and `public/stats.md` (uses `DB_PATH`/`OUT_DIR` envs).

## Testing
- Install dev deps: `python -m pip install -r requirements-dev.txt`
- Run tests: `python -m pytest`

## Tooling
- `make install` – create venv + install dev deps
- `make test` – run pytest suite
- Pre-commit hooks: install with `pre-commit install` (formatters: black, isort, prettier; linter: ruff)

## Project Layout
- `app.py` – Flask app + API.
- `public/` – static site assets (HTML/JS) consuming `/api/stats`.
- `scripts/` – stats generators and refresh helper.
- `Dockerfile`, `.dockerignore`, `requirements.txt` – container/runtime setup.
