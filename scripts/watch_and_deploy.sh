#!/usr/bin/env bash
# Pull the latest image and restart the container only if the image changed.
set -euo pipefail

IMAGE="${IMAGE:-mc-ledger-stats:latest}"
CONTAINER_NAME="${CONTAINER_NAME:-mc-ledger-stats}"
LEDGER_DB="${LEDGER_DB:-$(pwd)/ledger.sqlite}"
PORT="${PORT:-5000}"

old_id="$(docker image inspect --format '{{.Id}}' "$IMAGE" 2>/dev/null || true)"

echo "Pulling $IMAGE ..."
docker pull "$IMAGE" >/dev/null

new_id="$(docker image inspect --format '{{.Id}}' "$IMAGE")"

if [[ "$old_id" == "$new_id" && -n "$old_id" ]]; then
  echo "Image unchanged ($new_id); nothing to deploy."
  exit 0
fi

echo "Image updated to $new_id. Restarting container $CONTAINER_NAME ..."

if docker ps -a --format '{{.Names}}' | grep -w "$CONTAINER_NAME" >/dev/null; then
  docker stop "$CONTAINER_NAME" >/dev/null || true
  docker rm "$CONTAINER_NAME" >/dev/null || true
fi

docker run -d \
  --name "$CONTAINER_NAME" \
  -p "$PORT:$PORT" \
  -e LEDGER_DB=/app/ledger.sqlite \
  -e PORT="$PORT" \
  -v "$LEDGER_DB":/app/ledger.sqlite:ro \
  "$IMAGE"

echo "Deployed $CONTAINER_NAME from $IMAGE on port $PORT (ledger: $LEDGER_DB)"
