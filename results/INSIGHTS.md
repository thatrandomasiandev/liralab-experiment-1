# Insights from the PEBBLE results

I ran PEBBLE on Walker-walk with a Mistake teacher at ε = 0, 0.05, 0.1, and 0.2 (500k steps, one seed each). The point of the instrumentation was to tell apart two things people usually can’t separate from return alone: does the reward model itself get worse under noisy labels, or does SAC overoptimize a small, roughly constant reward error while the model is frozen between updates (Goodhart)?

## What I think is going on

The collapse at ε = 0.2 looks like the reward model failing under label noise, not SAC chasing a still-pretty-good frozen reward.

At ε ≤ 0.1, true return ends around 880–950. At ε = 0.2 it falls to about 44. At the same time, held-out and fixed-reference preference accuracy sit around 0.60 and 0.64, while Oracle (ε = 0) is around 0.87 and 0.85. Train accuracy stays around 0.98 either way, so the model is basically fitting the flipped labels instead of learning the real preference ranking. That gap is what lines up with the performance crash.

## On the Goodhart / overoptimization angle

Between reward updates the model is frozen, so if proxy return climbs while true return drops inside a window, that’s the Goodhart signature. That almost never shows up here: 0 out of 10 windows for ε ≤ 0.1, and only 1 out of 10 at ε = 0.2 (using a simple check where late-half proxy mean goes up by more than 5 and true mean goes down by more than 5). After feedback runs out at ε = 0.2, the long freeze looks more like the policy is stuck bad than like proxy is racing away from true.

## How noise behaves across ε

It doesn’t look like a gradual slope. Mild noise (0.05 and 0.1) still gets strong returns. Only 0.2 really breaks. Fixed-ref accuracy at ε = 0.2 also drifts down over updates (about 0.73 → 0.64), which fits with later noisy updates messing up a region that was fit earlier.

## Caveats

This is one seed per ε and only Walker-walk, and the Goodhart window test is a simple heuristic. So I’d treat this as a first readout that points toward reward-model quality under noise, not a multi-domain conclusion yet.
