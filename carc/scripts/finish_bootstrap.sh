#!/usr/bin/env bash
# Finish remaining deps assuming torch/gym/mujoco already present.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/carc/env.sh"
export CARC_NETID="${CARC_NETID:-$USER}"
# shellcheck source=/dev/null
source "$ROOT/carc/env.sh"

if [[ -f /etc/profile.d/modules.sh ]]; then
  # shellcheck source=/dev/null
  source /etc/profile.d/modules.sh
fi
module purge
module load gcc/11.3.0 2>/dev/null || module load gcc/13.3.0
module load cuda/11.8.0 2>/dev/null || module load cuda/12.4.0

# shellcheck source=/dev/null
source "${CARC_CONDA_DIR}/etc/profile.d/conda.sh"
conda activate "${CARC_ENV_NAME}"

# Keep mujoco pinned so dm_control does not pull a newer sdist
pip install 'numpy<2' 'mujoco==3.1.6' \
  'dm_control==1.0.20' absl-py pyparsing termcolor \
  imageio imageio-ffmpeg matplotlib glfw scikit-image tensorboard \
  pandas tqdm dm-env dm-tree scipy pyopengl pillow psutil protobuf

pip install 'git+https://github.com/facebookresearch/hydra.git@0.11_branch'

WRAPPER="$ROOT/BPref/custom_dmc2gym/dmc2gym/wrappers.py"
if [[ -f "$WRAPPER" ]] && grep -q 'np.int(' "$WRAPPER"; then
  sed -i 's/np.int(/int(/g' "$WRAPPER"
fi

cd "$ROOT/BPref/custom_dmc2gym"
pip install -e .

echo "Finish-bootstrap complete."
python - <<'PY'
import torch, gym, mujoco
print('torch', torch.__version__, 'cuda', torch.cuda.is_available())
if torch.cuda.is_available():
    print('gpu', torch.cuda.get_device_name(0))
print('gym', gym.__version__, 'mujoco', mujoco.__version__)
from dm_control import suite
import dmc2gym
env = dmc2gym.make(domain_name='walker', task_name='walk', seed=1, visualize_reward=False)
obs = env.reset()
print('dmc2gym walker-walk ok', obs.shape)
PY
