# CARC (USC) — compute home for this experiment

Local Apple Silicon is **not** the run target anymore. All training goes through USC CARC.

## What the lab guide says (Notion)

Login:
```bash
ssh <NET_ID>@discovery.usc.edu
```

Interactive debug GPU (from lab Notion):
```bash
salloc --time=4:00:00 --ntasks=1 --partition=debug \
  --gpus-per-task=k40:1 --cpus-per-task=4 --mem=8G \
  --account=biyik_1165
```

Batch GPU template (from lab Notion):
```bash
#SBATCH --account=biyik_1165
#SBATCH --partition=gpu
#SBATCH --gpus-per-task=v100:1   # A100 / A40 / V100 / P100 / K40
```

File transfer:
```bash
rsync -rltvh /local/path <NET_ID>@hpc-transfer1.usc.edu:/remote/path
```

Storage:
- `/home1/<NET_ID>` — 100 GB
- `/project/biyik_1165` or `/project2/biyik_1165` — shared project (confirm with `ls /project*`)
- `/scratch1/<NET_ID>` — scratch

**Do not use VS Code Remote SSH** on CARC login nodes (account hold risk). Use terminal SSH + optional SSH-FS.

## Account vs partition naming (important)

Colleague message listed `biyik_1173` and `biyik_1165` as **partition** names.
Lab Notion guide uses `biyik_1165` as **`--account`** with `--partition=gpu|debug`.

On first login, resolve this with:
```bash
myaccount
```
Then set `CARC_ACCOUNT` / `CARC_PARTITION` in `carc/env.sh` accordingly.

## One-time setup (after you can SSH)

1. Copy this repo to project storage (see `scripts/sync_to_carc.sh`).
2. On a compute node (`salloc` debug), install Miniconda + env (`scripts/bootstrap_env.sh`).
3. Submit smoke job: `sbatch carc/jobs/smoke_pebble_walker_oracle.job`
4. Track: `myqueue` / `squeue -u $USER` and `less slurm-<jobid>.out`

## Files in this folder

| Path | Purpose |
|------|---------|
| `env.sh` | NetID, account, partition, paths (edit once) |
| `scripts/sync_to_carc.sh` | rsync local → CARC |
| `scripts/bootstrap_env.sh` | Miniconda + BPref deps on a compute node |
| `jobs/smoke_pebble_walker_oracle.job` | Short end-to-end PEBBLE smoke |
| `jobs/smoke_causal_pebble.job` | Short smoke with causal metrics |
| `jobs/smoke_causal_pebble_debug.job` | Same smoke on `debug` (faster queue) |
| `jobs/baseline_pebble_walker_oracle.job` | Paper-default Walker Oracle run |
| `jobs/causal_pebble_walker_oracle.job` | 500k Oracle + causal instrumentation |
| `jobs/causal_pebble_walker_mistake_sweep.job` | Array: ε∈{0,0.05,0.1,0.2} + causal metrics |

### Causal experiment outputs (per Hydra run dir)

- `causal_window.csv` — per train episode: `window_id`, proxy vs true return
- `reward_update_metrics.csv` — at each RM update: train / held-out / on-policy / fixed-ref accuracy
- `checkpoints/` — agent + RM snapshots at each RM update
