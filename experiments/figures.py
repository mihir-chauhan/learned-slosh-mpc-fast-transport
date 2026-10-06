"""Paper figures, drawn only from results/runs.jsonl and results/raw/traj/*.npz."""
import collections
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "results", "figures")
DT = 0.03
STYLE = {   # fixed colour and marker per system
    "Learned-Ctx MPC": ("#2a78d6", "o"),
    "Pendulum MPC": ("#eb6834", "s"),
    "Two-mode spring-mass MPC": ("#1baf7a", "^"),
    "ZV input shaping": ("#eda100", "D"),
    "Learned MPC (no context)": ("#e87ba4", "v"),
    "Spring-mass MPC": ("#008300", "P"),
}
INK, MUTED = "#222222", "#777777"
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "grid.color": "#e6e6e6", "grid.linewidth": 0.6, "legend.frameon": False, "pdf.fonttype": 42})


def load():
    return [r for r in map(json.loads, open(os.path.join(ROOT, "results", "runs.jsonl")))
            if r.get("status") == "ok" and not r.get("superseded")]


def curve(runs, groups, param):
    acc = collections.defaultdict(list)
    for r in runs:
        if r["group"] in groups and r["name"] in STYLE and param in r["config"]:
            acc[(r["name"], r["config"][param])].append((r["metrics"]["transport_time_s"], r["metrics"]["spill_rate"]))
    out = collections.defaultdict(list)
    for (name, v), vals in sorted(acc.items()):
        out[name].append((v,) + tuple(np.mean(vals, axis=0)))
    return out


def tradeoff(runs):
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.6), sharey=True)
    panels = [(("sweep_margin", "sweep_apeak"), "Nominal liquid (validation episodes)"),
              (("sweep_margin_hp",), "Held-out liquid + push (test episodes)")]
    for ax, (groups, title) in zip(axes, panels):
        cur = curve(runs, groups, "margin")
        cur.update(curve(runs, groups, "a_peak"))
        for name in STYLE:
            if name not in cur:
                continue
            c, m = STYLE[name]
            pts = np.array(cur[name])
            ax.plot(pts[:, 1], 100 * pts[:, 2], color=c, marker=m, ms=4, lw=1.5, label=name,
                    markeredgecolor="white", markeredgewidth=0.6)
        ax.set_title(title, fontsize=8, color=INK)
        ax.set_xlabel("mean transport time [s]")
        ax.grid(True)
    axes[0].set_ylabel("spill rate [%]")
    axes[0].legend(fontsize=6.5, loc="center right")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "tradeoff.pdf"))
    plt.close(fig)


def trajectories():
    systems = [("learned", "Learned-Ctx MPC"), ("pendulum", "Pendulum MPC"),
               ("springmass2", "Two-mode spring-mass MPC"), ("shaping", "ZV input shaping")]
    fig, axes = plt.subplots(3, 1, figsize=(3.4, 4.4), sharex=True)
    for key, name in systems:
        d = np.load(os.path.join(ROOT, "results", "raw", "traj", f"{key}_nominal_s0.npz"))
        c, _ = STYLE[name]
        t = np.arange(d["X"].shape[0]) * DT
        axes[0].plot(t[:-1], d["U"][:, 0], color=c, lw=1.2, label=name)
        axes[1].plot(t, d["V"][:, 0], color=c, lw=1.2)
        axes[2].plot(t, d["S"][:, 0], color=c, lw=1.2)
    axes[2].axhline(1.0, color=MUTED, lw=0.8, ls="--")
    axes[2].text(3.28, 1.02, "brim", ha="right", va="bottom", fontsize=7, color=MUTED)
    axes[0].set_ylabel("cart accel. [m/s$^2$]")
    axes[1].set_ylabel("cart velocity [m/s]")
    axes[2].set_ylabel("max wall elevation\n[freeboards]")
    axes[2].set_xlabel("time [s]")
    axes[2].set_ylim(0, 1.15)
    for ax in axes:
        ax.grid(True)
    axes[0].legend(fontsize=6, ncol=2, loc="lower left", bbox_to_anchor=(0, 1.0))
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "trajectories.pdf"))
    plt.close(fig)


def push(runs):
    cur = curve(runs, ("sweep_push",), "push")
    fig, ax = plt.subplots(figsize=(3.4, 2.3))
    for name in STYLE:
        if name not in cur:
            continue
        c, m = STYLE[name]
        pts = np.array(cur[name])
        ax.plot(pts[:, 0], 100 * pts[:, 2], color=c, marker=m, ms=4, lw=1.5, label=name,
                markeredgecolor="white", markeredgewidth=0.6)
    ax.set_xlabel("push velocity change [m/s]")
    ax.set_ylabel("spill rate [%]")
    ax.set_xticks([0, 0.02, 0.04, 0.08])
    ax.grid(True)
    ax.legend(fontsize=6.5, loc="center right")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "push_sweep.pdf"))
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    runs = load()
    tradeoff(runs)
    trajectories()
    push(runs)
