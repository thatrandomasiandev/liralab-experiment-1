# Setup

**Primary compute: USC CARC (Discovery).** See [`carc/README.md`](carc/README.md).

Local Apple Silicon was used only for phase-1 code recon; do not rely on it for experiment runs.

## Quick start (once NetID works)

```bash
# local
export CARC_NETID=<your_usc_netid>
./carc/scripts/sync_to_carc.sh

# on discovery.usc.edu
ssh ${CARC_NETID}@discovery.usc.edu
myaccount   # confirm account + allowed partitions
salloc --time=4:00:00 --ntasks=1 --partition=debug \
  --gpus-per-task=k40:1 --cpus-per-task=4 --mem=8G \
  --account=biyik_1165
# on the allocated node:
cd /project2/biyik_1165/$USER/LIRALab-Experiment-1   # path may be /project/...
bash carc/scripts/bootstrap_env.sh
# back on login node:
sbatch carc/jobs/smoke_pebble_walker_oracle.job
myqueue
```

Lab Notion guide: https://rectangular-open-db3.notion.site/CARC-cluster-guide-33685f329bfd4f1a8987b48c23a72601
