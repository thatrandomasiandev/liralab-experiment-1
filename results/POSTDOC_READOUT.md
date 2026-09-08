# Postdoc readout — PEBBLE causal instrumentation (Walker-walk)

**Date:** 2026-09-07  
**Env:** Walker-walk · PEBBLE · Mistake teacher ε ∈ {0, 0.05, 0.1, 0.2}  
**Horizon:** 500k steps · `max_feedback=1000` · `num_interact=20000` · single seed per ε  
**Compute:** USC CARC (`biyik_1165`)

## One-line takeaway

Under ε=0.2, **true return collapses** and **held-out / fixed-ref reward accuracy are substantially worse** than Oracle — so this first sweep looks more like **reward-model quality failure under label noise** than a clean Goodhart case where accuracy stays high while behavior diverges. Mid-training windows show only weak / occasional proxy↑ true↓ signatures.

## What we measured

At every reward-model update:

| Preference set | Role |
|----------------|------|
| Train | Fit to labels used for training |
| Held-out (20% of each batch) | Generalization on the query distribution |
| On-policy (clean oracle labels) | Accuracy on current-policy states |
| Fixed reference (oracle, frozen once) | Corruption of an early region |

Within each frozen window (`window_id`): **proxy return** (`r_hat`) vs **true return** (GT).

## Results snapshot (end of training)

Last ~20 train episodes · last RM update (~190k, when feedback budget hits 1000):

| ε | True return | Proxy return | Train acc | Held-out | On-policy | Fixed-ref |
|---|-------------|--------------|-----------|----------|-----------|-----------|
| 0 | ~880 | ~615 | 0.98 | **0.87** | 0.77 | **0.85** |
| 0.05 | ~953 | ~492 | 0.98 | 0.76 | 0.76 | 0.80 |
| 0.10 | ~934 | ~474 | 0.98 | 0.74 | 0.88 | 0.72 |
| 0.20 | **~44** | ~150 | 0.98 | **0.60** | 0.66 | **0.64** |

Train-fit accuracy stays high even at ε=0.2 (model fits noisy labels). **Held-out and fixed-ref do not** — they sit ~15–25 points below Oracle throughout.

## Accuracy trajectories (held-out @ RM updates)

- **ε=0:** held-out stays ~0.82–0.90  
- **ε=0.05 / 0.1:** held-out ~0.74–0.82 (stable but lower)  
- **ε=0.2:** held-out starts ~0.63, dips to ~0.51 early, ends ~0.60 — never recovers  

Fixed-ref at ε=0.2 slowly drifts down (0.73 → 0.64), consistent with later updates harming an early region under noisy supervision.

## Within-window (frozen RM) proxy vs true

Heuristic “Goodhart-like” window: late-half proxy mean rises by >5 while true mean falls by >5.

| ε | Goodhart-like windows |
|---|------------------------|
| 0 / 0.05 / 0.1 | 0 / 10 |
| 0.2 | 1 / 10 (window 2 mild) |

After `max_feedback`, the RM is frozen for a **long** final window (~190k→500k). At ε=0.2 that window’s mean true return is ~76; proxy still edges up slightly while true is roughly flat/slightly down — not a dramatic Goodhart divergence, more “stuck bad.”

At ε≤0.1, late windows usually show **both** proxy and true rising.

## How to read this against the research question

| Hypothesis | Supported here? |
|------------|-----------------|
| Collapse from **RM accuracy decay / poor generalization under noise** | **Yes (primary):** held-out & fixed-ref much worse at ε=0.2; train acc stays high (overfit to noisy labels) |
| Collapse from **SAC overoptimization with roughly-constant RM error** | **Weak:** only rare within-window proxy↑/true↓; final freeze doesn’t show classic Goodhart separation |

**Caveats:** one seed per ε; Walker only; on-policy acc is noisy (few pairs); “Goodhart” window test is a simple early/late split, not a formal test.

## Artifacts

```
results/figures/overview_sweep.png      # returns + held-out/on-policy over training
results/figures/final_accuracies.png    # bar: four accuracy sets × ε
results/figures/within_window_last.png  # last frozen window, ε=0 vs 0.2
results/figures/heldout_vs_return.png   # held-out acc vs true return @ updates
results/raw/...                         # full CSVs pulled from CARC
```

Repo: https://github.com/thatrandomasiandev/liralab-experiment-1

## Suggested next steps

1. **Multi-seed** at ε∈{0, 0.2} (n≥3) to check stability of the collapse + accuracy gap  
2. Plot **on-policy accuracy with more pairs** (reduce variance)  
3. Optional control: freeze RM earlier under Oracle to stress-test Goodhart without label noise  
4. Add a second domain (e.g. Cheetah / Quadruped) if Walker result holds
