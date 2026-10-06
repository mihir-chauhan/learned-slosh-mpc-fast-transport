"""Time-minimising sampling-based MPC (MPPI) with a spill-margin constraint,
the input-shaping baseline, and the batched episode runner."""
import time
import numpy as np

import plant
from plant import DT, U_MAX, GOAL, Liquid

T_CAP = 3.3                 # episode length [s]
STEPS = int(round(T_CAP / DT))
TOL_X, TOL_V = 0.01, 0.03   # arrival tolerance [m], [m/s]
A_QS = 2.0                  # acceleration whose quasi-static surface rise equals the freeboard


def time_to_go(e, v, a):
    """Minimum time of a double integrator with |accel| <= a to reach e=0, v=0."""
    s = np.sign(e + v * np.abs(v) / (2 * a))
    s = np.where(s == 0, np.sign(v), s)
    return (s * v + 2 * np.sqrt(np.maximum(0.5 * v * v + a * s * e, 0.0))) / a


class MPPI:
    def __init__(self, model, margin, N=64, H=30, sigma=0.6, lam=0.01, w_c=50.0, a_ref_gain=1.0, iters=2, knot=5, structured=True, smooth=True, w_j=0.01):
        self.smooth, self.w_j = smooth, w_j
        self.structured = structured
        self.knot = knot
        self.model, self.margin = model, margin
        self.N, self.H, self.sigma, self.lam, self.w_c, self.iters = N, H, sigma, lam, w_c, iters
        self.a_ref = a_ref_gain * margin * A_QS

    def reset(self, E, rng):
        self.rng = rng
        self.U = np.zeros((E, self.H))
        self.first = True
        self.u_last = np.zeros(E)

    def _noise(self, E, scale):
        """Piecewise-constant perturbations on a knot grid with a random phase;
        even samples are coarse, odd samples fine; sample 0 is the nominal."""
        nk = self.H // self.knot + 3
        k = self.rng.normal(0, 1, (E, self.N, nk))
        if self.smooth:
            frac = (np.arange(self.knot) / self.knot)[None, None, None, :]
            eps = (k[..., :-1, None] * (1 - frac) + k[..., 1:, None] * frac).reshape(E, self.N, -1)
        else:
            eps = np.repeat(k, self.knot, axis=2)
        off = int(self.rng.integers(self.knot))
        eps = eps[:, :, off:off + self.H]
        level = self.sigma * np.where(np.arange(self.N) % 2 == 0, 1.0, 0.3)
        eps = eps * level[None, :, None] * scale[:, None, None]
        eps[:, 0] = 0.0
        return eps

    def act(self, x, v):
        E = x.shape[0]
        n_it = 6 if self.first else self.iters
        self.first = False
        # shrink the exploration noise as the cart settles at the goal
        scale = np.clip(time_to_go(x - GOAL, v, self.a_ref) / 0.4, 0.05, 1.0)
        for _ in range(n_it):
            Uc = self.U[:, None, :] + self._noise(E, scale)
            if self.structured:
                # structured candidates: the nominal sequence retimed (delayed / advanced)
                # and rescaled, which moves switch times and levels coherently
                Uc[:, 1, 1:] = self.U[:, :-1]; Uc[:, 1, 0] = self.U[:, 0]
                Uc[:, 2, :-1] = self.U[:, 1:]; Uc[:, 2, -1] = self.U[:, -1]
                Uc[:, 3, 2:] = self.U[:, :-2]; Uc[:, 3, :2] = self.U[:, :1]
                Uc[:, 4, :-2] = self.U[:, 2:]; Uc[:, 4, -2:] = self.U[:, -1:]
                for j, g in zip(range(5, 11), (0.8, 0.9, 0.95, 1.05, 1.1, 1.25)):
                    Uc[:, j] = self.U * g
                ramp = np.linspace(1.0, 0.0, self.H)[None, :]
                for j, g in zip(range(11, 17), (-1.0, -0.5, -0.2, 0.2, 0.5, 1.0)):
                    Uc[:, j] = self.U + g * ramp * scale[:, None]
            Uc = np.clip(Uc, -U_MAX, U_MAX)
            # cart: exact double integrator
            vv = v[:, None, None] + np.cumsum(Uc, axis=2) * DT
            vprev = vv - Uc * DT
            xx = x[:, None, None] + np.cumsum(vprev * DT + 0.5 * Uc * DT * DT, axis=2)
            sR, sL = self.model.rollout(Uc)
            viol = np.maximum(np.maximum(sR, sL) - self.margin, 0.0)
            e = xx - GOAL
            away = 1.0 - np.exp(-((e / 0.02) ** 2 + (vv / 0.06) ** 2))
            J = (DT * away.sum(axis=2) + time_to_go(e[:, :, -1], vv[:, :, -1], self.a_ref)
                 + self.w_c * (viol ** 2).sum(axis=2) + 5.0 * viol.max(axis=2)
                 + 1e-4 * (Uc ** 2).sum(axis=2)
                 + self.w_j * (np.diff(Uc, axis=2, prepend=np.broadcast_to(self.u_last[:, None, None], (E, self.N, 1))) ** 2).sum(axis=2))
            Jm = J - J.min(axis=1, keepdims=True)
            wgt = np.exp(-Jm / self.lam)
            wgt /= wgt.sum(axis=1, keepdims=True)
            self.U = (wgt[:, :, None] * Uc).sum(axis=1)
        u = self.U[:, 0].copy()
        self.u_last = u
        self.U = np.concatenate([self.U[:, 1:], np.zeros((E, 1))], axis=1)
        return u


class InputShaping:
    """Open-loop bang-bang acceleration profile convolved with a zero-vibration
    (ZV) shaper tuned to the fitted first-mode frequency and damping, tracked by
    a PD loop on the cart (so that pushes are rejected)."""

    def __init__(self, k, c, a_peak, kp=100.0, kd=20.0):
        wn = np.sqrt(k); zeta = c / (2 * wn)
        wd = wn * np.sqrt(1 - zeta ** 2)
        Kz = np.exp(-zeta * np.pi / np.sqrt(1 - zeta ** 2))
        amp = np.array([1.0, Kz]) / (1 + Kz)
        delay = np.array([0.0, np.pi / wd])
        fine = 20
        tf = (np.arange(STEPS * fine) + 0.5) * DT / fine
        t1 = np.sqrt(GOAL / a_peak)
        bang = lambda t: np.where((t >= 0) & (t < t1), a_peak, 0.0) - np.where((t >= t1) & (t < 2 * t1), a_peak, 0.0)
        af = sum(a * bang(tf - d) for a, d in zip(amp, delay))
        self.a = af.reshape(STEPS, fine).mean(axis=1)
        self.v = np.concatenate([[0.0], np.cumsum(self.a) * DT])
        self.x = np.concatenate([[0.0], np.cumsum(self.v[:-1] * DT + 0.5 * self.a * DT * DT)])
        self.a[-1] = 0.0
        self.kp, self.kd = kp, kd

    def reset(self, E, rng):
        self.t = 0

    def act(self, x, v):
        t = self.t
        self.t += 1
        return np.clip(self.a[t] + self.kp * (self.x[t] - x) + self.kd * (self.v[t] - v), -U_MAX, U_MAX)


def run_episodes(controller, model, seed, stream, E, pmode, truth, sensor="probe", push=0.0):
    """E closed-loop transport episodes on the true plant. Returns per-episode
    arrays and the mean controller time per step."""
    rng = np.random.default_rng([seed, stream])
    zeta, h = plant.sample_params(rng, E, pmode)
    liq = Liquid(zeta, h, truth)
    s = liq.zero_state(E)
    x = np.zeros(E); v = np.zeros(E)
    spec = plant.SENSORS[sensor]
    # push: a lateral impulse of velocity change `push` spread over 2 control periods
    push_t = rng.integers(8, 45, E)
    push_sign = rng.choice([-1.0, 1.0], E)
    if model is not None:
        model.reset(E, rng)
    controller.reset(E, rng)
    delay = spec.get("delay", 0)
    tilt_hist = [np.zeros(E) for _ in range(delay + 1)]
    peak = np.zeros(E)
    X = np.zeros((STEPS + 1, E)); V = np.zeros((STEPS + 1, E)); S = np.zeros((STEPS + 1, E)); Ulog = np.zeros((STEPS, E))
    a_prev = None
    force = np.zeros(E)
    solve = 0.0
    for t in range(STEPS):
        sR, sL = liq.walls(s)
        if model is not None:
            if sensor == "probe":
                y = np.stack([sR, sL], axis=1) + rng.normal(0, spec["noise"], (E, 2))
            elif sensor == "ft":
                y = (force + rng.normal(0, spec["noise"], E))[:, None]
            elif sensor == "cam":
                tilt_hist.append(0.5 * (sR - sL)); tilt_hist.pop(0)
                y = (tilt_hist[0] + rng.normal(0, spec["noise"], E))[:, None]
            else:
                y = np.zeros((E, 0))
            if hasattr(model, "set_truth"):
                model.set_truth(liq, s)
            model.observe(y, a_prev)
        t0 = time.perf_counter()
        u = np.clip(controller.act(x, v), -U_MAX, U_MAX)
        solve += time.perf_counter() - t0
        d = np.where((t >= push_t) & (t < push_t + 2), push_sign * push / (2 * DT), 0.0)
        a = u + d
        s = liq.step(s, a)
        force = liq.force(s, a)
        x = x + v * DT + 0.5 * a * DT * DT
        v = v + a * DT
        a_prev = a
        sR, sL = liq.walls(s)
        S[t + 1] = np.maximum(sR, sL)
        X[t + 1], V[t + 1], Ulog[t] = x, v, u
    ok = (np.abs(X - GOAL) < TOL_X) & (np.abs(V) < TOL_V)
    # arrival: first step from which the cart stays inside the tolerance until the end
    bad_after = np.cumsum(~ok[::-1], axis=0)[::-1] > 0
    arrived = ~bad_after[-1]
    t_arr = np.where(arrived, bad_after.sum(axis=0) * DT, T_CAP)
    peak = S.max(axis=0)
    return dict(time=t_arr, arrived=arrived, spilled=peak > 1.0, peak=peak, X=X, V=V, S=S, U=Ulog,
                solve_ms=1000 * solve / STEPS)


def summarise(res):
    spill = res["spilled"]
    fail = spill | ~res["arrived"]
    return {
        "transport_time_s": float(res["time"].mean()),
        "spill_rate": float(spill.mean()),
        "peak_disp": float(res["peak"].mean()),
        "arrive_rate": float(res["arrived"].mean()),
        "penalised_time_s": float(np.where(fail, T_CAP, res["time"]).mean()),
        "solve_ms": float(res["solve_ms"]),
    }


def prediction_rmse(model, seed, stream, pmode, truth, sensor="probe", n_traj=100, T=100, horizon=20):
    """Open-loop prediction error on fresh excitation trajectories: RMSE of the
    predicted wall elevations 1 and `horizon` steps ahead (freeboard units)."""
    d = plant.make_dataset(seed, stream, n_traj, T, pmode, truth)
    rng = np.random.default_rng([seed, stream + 1])
    Y = plant.read_sensors(rng, sensor, d["O"], d["F"])
    model.reset(n_traj, rng)
    if hasattr(model, "set_truth"):
        return {}
    e1, eh = [], []
    for t in range(T - horizon + 1):
        model.observe(Y[:, t], d["A"][:, t - 1] if t > 0 else None)
        if t >= 10 and t % 5 == 0:
            sR, sL = model.rollout(d["A"][:, None, t:t + horizon])
            pred = np.stack([sR[:, 0], sL[:, 0]], axis=-1)          # (n, horizon, 2)
            err = pred - d["O"][:, t + 1:t + horizon + 1]
            e1.append(err[:, 0]); eh.append(err[:, -1])
    return {"pred_rmse_1": float(np.sqrt(np.mean(np.square(e1)))),
            "pred_rmse_20": float(np.sqrt(np.mean(np.square(eh))))}
