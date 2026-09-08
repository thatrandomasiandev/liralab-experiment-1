# LIRALab Experiment 1 — PEBBLE reward accuracy vs overoptimization

Preference-based RL experiment on top of [B-Pref](https://github.com/rll-research/BPref) / [PEBBLE](https://arxiv.org/abs/2106.05091).

## Research question

When PEBBLE performance degrades under noisy preference labels, is it because:

1. **Reward-model accuracy actually decays**, or
2. **SAC overoptimizes** a small, roughly-constant reward-model error (Goodhart),

…while the reward model is frozen between discrete update events?

Standard B-Pref logs mostly final return, not reward-model accuracy under Mistake teachers — so those mechanisms are usually indistinguishable. This repo adds the measurements needed to separate them.

## Design (short)

PEBBLE updates the reward model only at discrete events (`num_interact`), then relabels the replay buffer. **Between updates the RM is frozen.**

Within each frozen window we track:

| Signal | Meaning |
|--------|---------|
| True return | Ground-truth env reward |
| Proxy return | Same rollouts scored by frozen `r_hat` |
| On-policy RM accuracy | Current-policy segments, **clean oracle** labels |

If **proxy climbs while true stagnates** inside a window where the RM cannot have changed → RL amplification, not RM decay.

At every RM update we also log preference accuracy on four sets:

| Set | What it measures |
|-----|------------------|
| Train prefs | Fit to labels used for training |
| Held-out prefs (`val_fraction`) | Generalization on the query distribution |
| On-policy prefs | Accuracy on states SAC is optimizing now |
| Fixed reference | Corruption of an early, frozen oracle-labeled set |

Training still uses the configured teacher (Oracle / Mistake ε). Metric labels always use a clean oracle path.

## Repo layout

```
BPref/                  Patched B-Pref (PEBBLE + causal instrumentation)
  train_PEBBLE.py       Training loop, window tracking, checkpoints
  reward_model.py       Held-out buffer, oracle labeling, accuracy APIs
  logger.py             Extra train metrics
  config/train_PEBBLE.yaml
carc/                   USC Discovery (CARC) jobs, sync, local GPU dashboard
SETUP.md                Environment / cluster pointers
third_party/            Patched gym 0.21 for modern Python packaging
```

Upstream B-Pref is vendored here (not a submodule) so experiment patches stay reproducible.

## Outputs (per Hydra run directory)

| File | Contents |
|------|----------|
| `reward_update_metrics.csv` | Accuracies + feedback counts at each RM update |
| `causal_window.csv` | Per episode: `window_id`, proxy vs true return |
| `checkpoints/` | Agent + RM snapshots at each RM update |
| `train.csv` / `eval.csv` | Standard B-Pref logs (eval proxy vs true fixed) |

## Running on CARC (primary)

Compute home: USC Discovery. See [`carc/README.md`](carc/README.md).

```bash
export CARC_NETID=<your_netid>
./carc/scripts/sync_to_carc.sh

ssh discovery
cd /project2/biyik_1165/$USER/LIRALab-Experiment-1   # adjust if needed

# short instrumented smoke (debug often starts faster than gpu)
sbatch carc/jobs/smoke_causal_pebble_debug.job

# paper-horizon causal runs
sbatch carc/jobs/causal_pebble_walker_oracle.job
sbatch carc/jobs/causal_pebble_walker_mistake_sweep.job   # array ε ∈ {0, 0.05, 0.1, 0.2}
```

Local GPU queue dashboard (VPN + `ssh discovery` required):

```bash
python3 carc/dashboard/server.py
# http://127.0.0.1:8765
```

## Key Hydra flags

```text
enable_causal_metrics=true
val_fraction=0.2
fixed_ref_size=256
onpolicy_acc_pairs=64
onpolicy_acc_episodes=3
save_rm_every_update=true
teacher_eps_mistake={0,0.05,0.1,0.2}
```

Walker paper-ish defaults used in CARC jobs: `num_train_steps=500000`, `num_interact=20000`, `max_feedback=1000`, `reward_batch=100`, Oracle/Mistake with `teacher_beta=-1`.

## Local notes

Apple Silicon was used only for early recon. Prefer CARC for real runs. Nontrivial setup details (Hydra 0.11, gym 0.21 patch, MuJoCo/`dm_control`) are in [`SETUP.md`](SETUP.md) and [`carc/README.md`](carc/README.md).

## Status

- [x] B-Pref setup (local + CARC)
- [x] Frozen-window recon (holds in this codebase)
- [x] Causal instrumentation + debug smoke
- [x] Full Oracle 500k + Mistake sweep results (completed on CARC; see `results/`)

## Results website

```bash
cd results/website && python3 -m http.server 8766
# open http://127.0.0.1:8766
```

Interactive charts live in [`results/website/`](results/website/). Written readout: [`results/POSTDOC_READOUT.md`](results/POSTDOC_READOUT.md).


## Citation / upstream

```
B-Pref:  Lee et al., NeurIPS 2021 Datasets & Benchmarks
PEBBLE:  Lee, Smith & Abbeel, ICML 2021
Code:    https://github.com/rll-research/BPref
```
