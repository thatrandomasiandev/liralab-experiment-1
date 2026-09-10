# CARC GPU dashboard (local)

Live web UI for Discovery `gpu` / `debug` queue depth, node types, your jobs, and priority.

## Run

1. USC VPN on
2. `ssh discovery` works from this Mac
3. From the repo root:

```bash
python3 carc/dashboard/server.py
```

4. Open **http://127.0.0.1:8765**

Optional remote mirror (password-protected): while this server is running it pushes snapshots to
**https://liralab-pebble-results.vercel.app/queue** (site password required). Configure
`carc/dashboard/.env` with `CARC_INGEST_SECRET` matching the Vercel `INGEST_SECRET`.

Auto-refreshes every 30s. Click **Refresh** for a forced pull.

## What you’ll see

| Section | Source | Notes |
|---------|--------|-------|
| Your jobs | `squeue` | Only **currently queued/running** jobs |
| Recently finished | `sacct` (48h) | Completed / failed / cancelled — so jobs don’t look like they “vanished” |
| Queue counts | `squeue -p gpu/debug` | Cluster-wide depth |

## Stability notes

- Pipe-delimited Slurm output (no column-width truncation glitches).
- One SSH collect at a time; failed refreshes keep the last good snapshot.
- UI does not clear tables while fetching.
