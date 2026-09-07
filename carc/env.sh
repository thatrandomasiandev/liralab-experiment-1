# shellcheck shell=bash
# Source this on CARC (or from local sync scripts).
# Fill in NET_ID after first successful login checklist.

# --- edit these ---
export CARC_NETID="${CARC_NETID:-jjt_373}"
export CARC_HOST="${CARC_HOST:-discovery.usc.edu}"
export CARC_TRANSFER_HOST="${CARC_TRANSFER_HOST:-hpc-transfer1.usc.edu}"

# Lab Notion uses biyik_1165 as --account and gpu/debug as --partition.
# Colleague listed biyik_1165 / biyik_1173 as partitions — confirm with `myaccount`.
export CARC_ACCOUNT="${CARC_ACCOUNT:-biyik_1165}"
export CARC_PARTITION="${CARC_PARTITION:-gpu}"
export CARC_DEBUG_PARTITION="${CARC_DEBUG_PARTITION:-debug}"

# Prefer project storage for code+exps (home is only 100GB).
# After login, confirm which exists: /project/biyik_1165 vs /project2/biyik_1165
export CARC_PROJECT_ROOT="${CARC_PROJECT_ROOT:-/project2/biyik_1165}"
export CARC_REPO_DIR="${CARC_REPO_DIR:-${CARC_PROJECT_ROOT}/${CARC_NETID}/LIRALab-Experiment-1}"
export CARC_CONDA_DIR="${CARC_CONDA_DIR:-${CARC_PROJECT_ROOT}/${CARC_NETID}/miniconda3}"
export CARC_ENV_NAME="${CARC_ENV_NAME:-bpref}"

# Default GPU request for real runs
export CARC_GPU="${CARC_GPU:-v100:1}"
export CARC_CPUS="${CARC_CPUS:-8}"
export CARC_MEM="${CARC_MEM:-32G}"
export CARC_TIME="${CARC_TIME:-24:00:00}"
