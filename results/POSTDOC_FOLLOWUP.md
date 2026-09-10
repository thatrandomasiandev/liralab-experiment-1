# Postdoc follow-up — Question 1 & 2

Response to feedback on the first Walker-walk Mistake sweep (1 seed × 4 ε).

## Question 1 — Make accuracy → performance more direct

### What you asked for
- Plot reward-model accuracy against downstream RL performance across seeds / checkpoints / settings
- Quantify correlation
- Find cases where higher accuracy does **not** mean higher downstream performance

### What we can do already (1 seed × 4 ε, 10 RM updates each)

Each point pairs an RM-update accuracy with **mean true return in the frozen window after that update**.

| Slice | Best predictors of window true return | Notes |
|-------|----------------------------------------|-------|
| All checkpoints (n=40) | on-policy r≈0.61, fixed-ref r≈0.46, held-out r≈0.29 | Train acc ≈ 0 (useless) |
| Late only, step ≥ 100k (n=20) | on-policy / fixed-ref / held-out all r≈0.56–0.62; train−heldout gap r≈−0.55 | Cleaner once learning has started |
| End-of-run (n=4) | held-out r≈0.83 (unstable with n=4) | Too few runs for a serious claim |

Figures:
- `results/figures/acc_vs_return_correlation.png`
- `results/figures/acc_metrics_vs_return_late.png`
- `results/figures/final_heldout_vs_return.png`
- Numbers: `results/q1_correlation_summary.json`

### Counterexamples (already visible)

Higher held-out accuracy does **not** always mean higher final return among successful runs:

| ε | Final held-out | Final true return |
|---|----------------|-------------------|
| 0 | 0.865 | ~880 |
| 0.05 | 0.755 | ~953 |
| 0.1 | 0.740 | ~934 |
| 0.2 | 0.597 | ~44 |

So ε=0 has the best held-out accuracy but not the best return. Mild noise can still beat Oracle on return while looking worse on held-out. Accuracy is related to the **collapse** (ε=0.2), but it is not a monotone predictor of return among non-collapsed runs.

Among late checkpoints we did **not** find the extreme pattern “held-out ≥ 0.74 and window return < 400” or “held-out ≤ 0.65 and window return > 600”. The interesting mismatches are mostly in the successful band, not in the collapse band.

### Still needed for Q1
More seeds (and preferably more ε or domains) so the scatter is not 4 end-of-run dots. Multi-seed jobs below feed this.

---

## Question 2 — Narrow: is ε=0.2 collapse real, and what explains success vs failure?

### Plan (narrow)
1. Re-run **ε=0.2** with **3 seeds** (incl. original 12348)
2. Re-run **ε=0** with **3 seeds** as control
3. Call a run “failed” if final true return (last 20 episodes) **< 200**, else “successful”
4. Compare measurable factors between success vs fail:
   - final held-out / fixed-ref / on-policy / train
   - train − held-out gap
   - held-out trajectory min / last
   - Goodhart-like window count
   - fixed-ref drift (first → last update)

Ask: which single factor best separates success from failure (largest gap / best ranking)?

### Job
```bash
sbatch carc/jobs/causal_pebble_walker_multiseed.job
```
Array 0–5 → (ε, seed) ∈  
`(0,12345), (0,20001), (0,20002), (0.2,12348), (0.2,20011), (0.2,20012)`

---

## Short reply you can send

For Q1 I’m moving from ε-bar comparisons to checkpoint-level scatters of RM accuracy vs next-window true return, with Pearson/Spearman. Even with the current 4 runs, held-out is not monotone with return among successes (ε=0 has higher held-out than 0.05/0.1 but lower return). Train accuracy does not track performance; late held-out / fixed-ref / on-policy do better. I’m expanding this with multi-seed runs.

For Q2 I’m keeping scope narrow: 3 seeds at ε=0.2 and 3 at ε=0 to check whether the collapse replicates, then comparing measurable factors (held-out, fixed-ref, train−heldout gap, Goodhart window counts, etc.) between successful and failed runs.
