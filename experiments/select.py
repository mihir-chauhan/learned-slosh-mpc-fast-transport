"""Pick each system's tuned setting from the validation sweeps in results/runs.jsonl.

Rule: the largest grid value such that it and every smaller grid value has zero
spills and full arrival on every validation run. Writes experiments/selected.json
and a flat metrics JSON (so the chosen values are logged results)."""
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = {"Learned-Ctx MPC": "learned", "Learned MPC (no context)": "learned_noctx", "Pendulum MPC": "pendulum",
       "Spring-mass MPC": "springmass", "Two-mode spring-mass MPC": "springmass2", "ZV input shaping": "shaping",
       "Oracle MPC (privileged)": "oracle"}
GROUPS = {"sweep_margin": "full", "sweep_apeak": "full", "sweep_margin_lin1": "lin1", "sweep_apeak_lin1": "lin1"}


def main():
    fam = sys.argv[1]
    out = sys.argv[2]
    ok = collections.defaultdict(lambda: collections.defaultdict(list))
    for line in open(os.path.join(ROOT, "results", "runs.jsonl")):
        r = json.loads(line)
        if r.get("status") != "ok" or GROUPS.get(r.get("group")) != fam or r.get("superseded"):
            continue
        cfg = r["config"]
        v = cfg.get("margin", cfg.get("a_peak"))
        m = r["metrics"]
        ok[KEY[r["name"]]][v].append(m["spill_rate"] == 0.0 and m["arrive_rate"] == 1.0)
    sel = {}
    for s, grid in ok.items():
        best = None
        for v in sorted(grid):
            if not all(grid[v]):
                break
            best = v
        if best is None:
            best = min(grid)
        sel[s] = best
    path = os.path.join(ROOT, "experiments", "selected.json")
    allsel = json.load(open(path)) if os.path.exists(path) else {}
    allsel[fam] = sel
    json.dump(allsel, open(path, "w"), indent=1, sort_keys=True)
    json.dump({f"tuned_{s}": v for s, v in sorted(sel.items())}, open(out, "w"), indent=1)
    print(sel)


if __name__ == "__main__":
    main()
