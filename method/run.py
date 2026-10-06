"""Single entrypoint: one system on one task with one seed -> flat metrics JSON.

  python method/run.py --system learned --task nominal --seed 0 --margin 0.8 --out m.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import models
import mpc

TASKS = {   # task -> (liquid parameters, ground truth, push velocity change [m/s])
    "nominal": ("nominal", "full", 0.0),
    "heldout": ("heldout", "full", 0.0),
    "push": ("nominal", "full", 0.04),
    "heldout_push": ("heldout", "full", 0.04),
    "lin1": ("nominal", "lin1", 0.0),
    "lin2": ("nominal", "lin2", 0.0),
}
STREAM = {"val": 100, "test": 200}


def build_model(a):
    truth = TASKS[a.task][1]
    if a.system == "learned":
        return models.train_learned(a.seed, truth, a.sensor, a.K, a.zdim, a.ndata)
    if a.system == "learned_noctx":
        return models.train_learned(a.seed, truth, a.sensor, a.K, 0, a.ndata)
    if a.system in ("pendulum", "springmass", "springmass2"):
        return models.fit_parametric(a.system, a.seed, truth)
    if a.system == "oracle":
        return models.Oracle()
    raise ValueError(a.system)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--system", required=True)
    p.add_argument("--task", required=True, choices=list(TASKS))
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--split", default="test", choices=["val", "test"])
    p.add_argument("--episodes", type=int, default=100)
    p.add_argument("--margin", type=float, default=0.8, help="spill margin of the MPC constraint")
    p.add_argument("--a_peak", type=float, default=1.2, help="peak acceleration of the shaped profile")
    p.add_argument("--push", type=float, default=None, help="override the push velocity change")
    p.add_argument("--sensor", default="probe", choices=["cart", "probe", "ft", "cam"])
    p.add_argument("--K", type=int, default=30, help="history length of the encoder")
    p.add_argument("--zdim", type=int, default=4)
    p.add_argument("--ndata", type=int, default=50000, help="training transitions")
    p.add_argument("--N", type=int, default=64, help="MPPI samples")
    p.add_argument("--H", type=int, default=30, help="MPPI horizon (steps)")
    p.add_argument("--traj", default="", help="optional .npz to store example trajectories")
    a = p.parse_args()

    pmode, truth, push = TASKS[a.task]
    if a.push is not None:
        push = a.push
    metrics = {}
    if a.system == "shaping":
        sm = models.fit_parametric("springmass", a.seed, truth)
        ctrl = mpc.InputShaping(sm.theta[0], sm.theta[1], a.a_peak)
        model = None
    else:
        model = build_model(a)
        ctrl = mpc.MPPI(model, a.margin, N=a.N, H=a.H)
        metrics.update(mpc.prediction_rmse(model, a.seed, 300, pmode, truth, a.sensor))
    res = mpc.run_episodes(ctrl, model, a.seed, STREAM[a.split], a.episodes, pmode, truth, a.sensor, push)
    metrics.update(mpc.summarise(res))
    if a.traj:
        os.makedirs(os.path.dirname(a.traj), exist_ok=True)
        np.savez(a.traj, X=res["X"][:, :3], V=res["V"][:, :3], U=res["U"][:, :3], S=res["S"][:, :3])
    with open(a.out, "w") as f:
        json.dump(metrics, f, indent=1)
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
