#!/usr/bin/env bash
# Run on a CARC *compute* node (salloc/sbatch), not the login node.
# Installs Miniconda (if needed) + BPref/PEBBLE deps for CUDA.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/carc/env.sh"

if [[ -z "${CARC_NETID}" ]]; then
  export CARC_NETID="${USER}"
  # shellcheck source=/dev/null
  source "$ROOT/carc/env.sh"
fi

# sbatch / non-login shells need Lmod explicitly
if [[ -f /etc/profile.d/modules.sh ]]; then
  # shellcheck source=/dev/null
  source /etc/profile.d/modules.sh
fi

module purge
module load gcc/11.3.0 2>/dev/null || module load gcc/13.3.0
module load cuda/11.8.0 2>/dev/null || module load cuda/12.4.0

mkdir -p "$(dirname "$CARC_CONDA_DIR")"
if [[ ! -x "${CARC_CONDA_DIR}/bin/conda" ]]; then
  echo "Installing Miniconda to ${CARC_CONDA_DIR}"
  cd /tmp
  wget -q https://repo.anaconda.com/miniconda/Miniconda3-py39_24.7.1-0-Linux-x86_64.sh -O miniconda.sh
  bash miniconda.sh -b -p "$CARC_CONDA_DIR"
fi

# shellcheck source=/dev/null
source "${CARC_CONDA_DIR}/etc/profile.d/conda.sh"

if ! conda env list | grep -qE "^${CARC_ENV_NAME}\\s"; then
  conda create -y -n "$CARC_ENV_NAME" python=3.9
fi
conda activate "$CARC_ENV_NAME"

pip install -U pip 'setuptools<70' wheel

# CUDA torch
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Gym 0.21 needs old packaging; use the patched tree we ship if present
if [[ -d "$ROOT/third_party/gym-0.21.0" ]]; then
  pip install "$ROOT/third_party/gym-0.21.0"
else
  pip install 'setuptools<66' && pip install gym==0.21.0 || true
fi

# Pin mujoco to a release with prebuilt cp39 manylinux wheels (latest often
# tries to build from source and requires MUJOCO_PATH).
pip install 'numpy<2' 'mujoco==3.1.6' --only-binary=:all: || \
  pip install 'numpy<2' 'mujoco==3.1.6'

pip install dm_control absl-py pyparsing termcolor \
  imageio imageio-ffmpeg matplotlib glfw scikit-image tensorboard \
  pandas tqdm dm-env dm-tree scipy pyopengl pillow psutil protobuf

pip install 'git+https://github.com/facebookresearch/hydra.git@0.11_branch'

# Fix np.int in wrapper if still present
WRAPPER="$ROOT/BPref/custom_dmc2gym/dmc2gym/wrappers.py"
if [[ -f "$WRAPPER" ]] && grep -q 'np.int(' "$WRAPPER"; then
  sed -i 's/np.int(/int(/g' "$WRAPPER"
fi

cd "$ROOT/BPref/custom_dmc2gym"
pip install -e .

echo "Bootstrap complete."
python - <<'PY'
import torch, gym
print('torch', torch.__version__, 'cuda', torch.cuda.is_available())
if torch.cuda.is_available():
    print('gpu', torch.cuda.get_device_name(0))
print('gym', gym.__version__)
import mujoco
print('mujoco', mujoco.__version__)
from dm_control import suite
env = suite.load('walker', 'walk')
print('dm_control walker-walk ok', env.action_spec())
PY
