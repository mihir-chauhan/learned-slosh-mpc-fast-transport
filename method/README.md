# Method

Implementation of our method. Contract with the harness:

- Entry point takes `--task`, `--seed`, and writes a flat JSON of metrics to `$RH_METRICS_FILE`
  (also passed as `--out`). Metric names must match `research.yaml: metrics`.
- Deterministic given the seed (set numpy/torch/random seeds; note any nondeterministic kernels).
- Optional: write a training curve to `<out_dir>/curve.csv` with columns `step,value,seed,name`
  so `rh fig curves` can plot it.
- Every ablation is a config flag, never a code fork.
