#!/usr/bin/env bash
# Sync this experiment to CARC via the transfer node.
# Usage (local):
#   export CARC_NETID=your_netid
#   ./carc/scripts/sync_to_carc.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/carc/env.sh"

if [[ -z "${CARC_NETID}" ]]; then
  echo "Set CARC_NETID (USC NetID) first, e.g.:"
  echo "  export CARC_NETID=jterra"
  exit 1
fi

# Prefer Discovery SSH (key auth). Transfer node often demands Duo interactively.
REMOTE_HOST="discovery"
REMOTE_DIR="${CARC_REPO_DIR}"
echo "Syncing -> ${REMOTE_HOST}:${REMOTE_DIR}"

ssh "$REMOTE_HOST" "mkdir -p '${REMOTE_DIR}'"
rsync -rltvh \
  --exclude '.venv/' \
  --exclude '.uv-cache/' \
  --exclude 'BPref/exp/' \
  --exclude '**/__pycache__/' \
  --exclude '.git/' \
  --exclude '*.pt' \
  "$ROOT/" \
  "${REMOTE_HOST}:${REMOTE_DIR}/"

echo "Done. On discovery:"
echo "  cd ${REMOTE_DIR}"
