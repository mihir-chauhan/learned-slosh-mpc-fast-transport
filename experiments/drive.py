"""Experiment driver: issues one `rh run` per (system, task, seed, setting).

  python experiments/drive.py <stage>
Stages: sweep, sweep_lin1, main, reference, abl_history, abl_data, abl_sensor, abl_mpc, sweep_push, sweep_hp
"""
import json
import os
import subprocess
import sys

PY = sys.executable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMES = {
    "learned": "Learned-Ctx MPC",
    "learned_noctx": "Learned MPC (no context)",
    "pendulum": "Pendulum MPC",
    "springmass": "Spring-mass MPC",
    "springmass2": "Two-mode spring-mass MPC",
    "shaping": "ZV input shaping",
    "oracle": "Oracle MPC (privileged)",
}
MPC_SYS = ["learned", "learned_noctx", "pendulum", "springmass", "springmass2"]
SEL = os.path.join(ROOT, "experiments", "selected.json")


def rh(kind, name, group, task, seed, config, args, tag):
    out = f"results/raw/{group}_{tag}_{task}_s{seed}.json"
    cmd = ["rh", "run", "--kind", kind, "--name", name, "--group", group, "--task", task, "--seed", str(seed),
           "--config", json.dumps(config), "--metrics-file", out, "--",
           PY, "method/run.py", "--task", task, "--seed", str(seed), "--out", out] + [str(a) for a in args]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    line = [l for l in r.stdout.splitlines() if l.startswith("[")]
    print(line[-1][:260] if line else r.stdout[-400:] + r.stderr[-400:], flush=True)


def kind_of(s):
    return "method" if s == "learned" else "baseline"


def setting(sel, s, fam):
    v = sel[fam][s]
    return (["--a_peak", v], {"a_peak": v}) if s == "shaping" else (["--margin", v], {"margin": v})


def sweep(task, group, margins, apeaks, oracle_margins, seeds=(0, 1, 2), E=30):
    for seed in seeds:
        for s in MPC_SYS:
            for m in margins:
                rh(kind_of(s), NAMES[s], group, task, seed, {"margin": m, "split": "val", "episodes": E},
                   ["--system", s, "--margin", m, "--split", "val", "--episodes", E], f"{s}_m{m}")
        for a in apeaks:
            rh("baseline", NAMES["shaping"], group.replace("margin", "apeak"), task, seed,
               {"a_peak": a, "split": "val", "episodes": E},
               ["--system", "shaping", "--a_peak", a, "--split", "val", "--episodes", E], f"shaping_a{a}")
        for m in oracle_margins:
            rh("sanity", NAMES["oracle"], group, task, seed, {"margin": m, "split": "val", "episodes": E},
               ["--system", "oracle", "--margin", m, "--split", "val", "--episodes", E], f"oracle_m{m}")


def main():
    stage = sys.argv[1]
    seeds5 = [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else list(range(5))
    E = 50
    if stage == "sweep":
        sweep("nominal", "sweep_margin", [0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0],
              [0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5], [0.95, 1.0])
        return
    if stage == "sweep_lin1":
        sweep("lin1", "sweep_margin_lin1", [0.8, 0.9, 0.95, 1.0], [1.4, 1.6, 1.7, 1.8, 1.9], [])
        return
    sel = json.load(open(SEL))
    m_l = sel["full"]["learned"]
    if stage == "main":
        for seed in seeds5:
            for task in ["nominal", "heldout", "heldout_push", "lin1"]:
                fam = "lin1" if task == "lin1" else "full"
                for s in MPC_SYS + ["shaping"]:
                    a, cfg = setting(sel, s, fam)
                    extra = ["--traj", f"results/raw/traj/{s}_{task}_s{seed}.npz"] if seed == 0 else []
                    rh(kind_of(s), NAMES[s], "main", task, seed, dict(cfg, episodes=E),
                       ["--system", s, "--episodes", E] + a + extra, s)
    elif stage == "reference":
        for seed in seeds5:
            m = sel["full"]["oracle"]
            rh("sanity", NAMES["oracle"], "reference", "nominal", seed, {"margin": m, "episodes": E},
               ["--system", "oracle", "--margin", m, "--episodes", E,
                "--traj", f"results/raw/traj/oracle_nominal_s{seed}.npz"], "oracle")
    elif stage in ("abl_history", "abl_data", "abl_sensor", "abl_mpc"):
        task = "heldout_push"
        variants = {
            "abl_history": [("Learned-Ctx MPC", {"K": 30}, []),
                            ("history 10", {"K": 10}, ["--K", 10]),
                            ("history 0 (no encoder)", {"K": 0}, ["--K", 0, "--zdim", 0])],
            "abl_data": [("Learned-Ctx MPC", {"ndata": 50000}, []),
                         ("10k transitions", {"ndata": 10000}, ["--ndata", 10000]),
                         ("1k transitions", {"ndata": 1000}, ["--ndata", 1000])],
            "abl_sensor": [("Learned-Ctx MPC", {"sensor": "probe"}, []),
                           ("cart only", {"sensor": "cart"}, ["--sensor", "cart"]),
                           ("cart + force/torque", {"sensor": "ft"}, ["--sensor", "ft"]),
                           ("cart + camera proxy", {"sensor": "cam"}, ["--sensor", "cam"])],
            "abl_mpc": [("Learned-Ctx MPC", {"H": 30, "N": 64}, []),
                        ("horizon 15", {"H": 15, "N": 64}, ["--H", 15]),
                        ("horizon 45", {"H": 45, "N": 64}, ["--H", 45]),
                        ("32 samples", {"H": 30, "N": 32}, ["--N", 32]),
                        ("128 samples", {"H": 30, "N": 128}, ["--N", 128])],
        }[stage]
        for seed in range(3):
            for name, cfg, extra in variants:
                kind = "method" if name == NAMES["learned"] else "ablation"
                rh(kind, name, stage, task, seed, dict(cfg, margin=m_l, episodes=E),
                   ["--system", "learned", "--margin", m_l, "--episodes", E] + extra,
                   name.replace(" ", "_").replace("/", "").replace("(", "").replace(")", "").replace("+", "plus"))
    elif stage == "sweep_push":
        for seed in range(3):
            for s in ["learned", "pendulum", "springmass2", "shaping"]:
                a, cfg = setting(sel, s, "full")
                for push in [0.0, 0.02, 0.04, 0.08]:
                    rh(kind_of(s), NAMES[s], "sweep_push", "push", seed, dict(cfg, push=push, episodes=E),
                       ["--system", s, "--episodes", E, "--push", push] + a, f"{s}_p{push}")
    elif stage == "sweep_hp":
        for seed in range(3):
            for s in ["learned", "learned_noctx", "pendulum"]:
                for m in [0.7, 0.8, 0.9, 1.0]:
                    rh(kind_of(s), NAMES[s], "sweep_margin_hp", "heldout_push", seed, {"margin": m, "episodes": E},
                       ["--system", s, "--margin", m, "--episodes", E], f"{s}_m{m}")


if __name__ == "__main__":
    main()
