"""Derived numbers: per-setting means over seeds of the sweep groups, read from
results/runs.jsonl and written as a flat metrics JSON."""
import collections
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHORT = {"Learned-Ctx MPC": "learned", "Learned MPC (no context)": "noctx", "Pendulum MPC": "pendulum",
         "Two-mode spring-mass MPC": "sm2", "ZV input shaping": "zv"}


def main():
    rows = collections.defaultdict(list)
    for line in open(os.path.join(ROOT, "results", "runs.jsonl")):
        r = json.loads(line)
        if r.get("status") != "ok" or r.get("superseded") or r["name"] not in SHORT:
            continue
        c = r["config"]
        if r["group"] == "sweep_margin_hp":
            key = f"hp_m{int(round(100 * c['margin'])):03d}_{SHORT[r['name']]}"
        elif r["group"] == "sweep_push":
            key = f"push{int(round(100 * c['push'])):03d}_{SHORT[r['name']]}"
        else:
            continue
        rows[key].append(r["metrics"])
    out = {}
    for key, ms in sorted(rows.items()):
        out[key + "_time"] = float(np.mean([m["transport_time_s"] for m in ms]))
        out[key + "_spill"] = float(np.mean([m["spill_rate"] for m in ms]))
    json.dump(out, open(sys.argv[1], "w"), indent=1)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
