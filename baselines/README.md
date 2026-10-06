# Baselines

One directory per baseline: `baselines/<slug>/{baseline.yaml, run.sh, adapter.py, repo/}`.
Scaffold with `rh baseline "<Name>" --repo <url> --paper <arxiv id> --year <yyyy>`.

Rules
- `repo/` is a git clone pinned to the commit recorded in baseline.yaml. Never edit upstream code
  in place; put patches in `patches/` and apply them in `setup` so the change is auditable.
- Each baseline gets its own env (`uv venv .venv` inside the baseline dir) so dependency
  conflicts between baselines never block each other.
- `adapter.py` maps the baseline's native output to the metric names in research.yaml.
  Same metric, same definition, same evaluation protocol as our method or the comparison is void.
- Record `reported_numbers` from the paper and compare against what you reproduce. A gap > 5%
  relative needs an explanation in `notes` before the baseline is used.
- Log every run via `rh run --kind baseline --name "<Name>" --task <t> --seed <s> --metrics-file ... -- bash run.sh ...`
