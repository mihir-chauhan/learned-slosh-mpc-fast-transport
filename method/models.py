"""Slosh predictors that plug into the MPC.

Common interface (batched over E episodes):
    reset(E, rng)          start from rest
    observe(y, a_prev)     new sensor reading y (E, ny); a_prev (E,) is the measured
                           cart acceleration over the last period (None at t=0)
    rollout(U)             U (E, N, H) candidate accelerations ->
                           predicted wall elevations (sR, sL), each (E, N, H)
"""
import os
import numpy as np
from scipy.linalg import expm, solve_discrete_are
from scipy.optimize import least_squares

import plant
from plant import DT, G, W, FREE, SENSORS

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "raw", "models")


# ----------------------------------------------------------------------------
# parametric baselines
# ----------------------------------------------------------------------------
def _sm_matrices(theta):
    """ZOH discretisation of n decoupled spring-mass-damper modes.
    theta = [k_1, c_1, b_1, ...]:  p'' = -k p - c p' - b u,  output sum(p)."""
    n = len(theta) // 3
    A = np.zeros((2 * n, 2 * n)); B = np.zeros((2 * n, 1)); C = np.zeros((1, 2 * n))
    for i in range(n):
        k, c, b = theta[3 * i:3 * i + 3]
        A[2 * i, 2 * i + 1] = 1.0
        A[2 * i + 1, 2 * i] = -k
        A[2 * i + 1, 2 * i + 1] = -c
        B[2 * i + 1, 0] = -b
        C[0, 2 * i] = 1.0
    M = np.zeros((2 * n + 1, 2 * n + 1))
    M[:2 * n, :2 * n] = A; M[:2 * n, 2 * n:] = B
    Md = expm(M * DT)
    return Md[:2 * n, :2 * n], Md[:2 * n, 2 * n:], C


def _kalman_gain(Ad, Bd, C, r, q):
    """Steady-state Kalman gain (filter form) for process noise q*Bd Bd^T + small
    diagonal and measurement noise variance r."""
    n = Ad.shape[0]
    Q = q * (Bd @ Bd.T) + 1e-6 * np.eye(n)
    P = solve_discrete_are(Ad.T, C.T, Q, np.array([[r]]))
    return (P @ C.T / (C @ P @ C.T + r)).ravel()


OBS_R = SENSORS["probe"]["noise"] ** 2 / 2   # variance of (yR - yL)/2
OBS_Q = 0.5 ** 2                              # assumed acceleration disturbance variance


class SpringMass:
    """Linear spring-mass-damper slosh model with n modes and a Kalman observer
    on the antisymmetric probe signal (yR - yL)/2."""

    def __init__(self, theta):
        self.theta = np.asarray(theta, float)
        self.Ad, self.Bd, self.C = _sm_matrices(self.theta)
        self.L = _kalman_gain(self.Ad, self.Bd, self.C, OBS_R, OBS_Q)
        self.nx = self.Ad.shape[0]

    def reset(self, E, rng):
        self.x = np.zeros((E, self.nx))

    def observe(self, y, a_prev):
        if a_prev is not None:
            self.x = self.x @ self.Ad.T + a_prev[:, None] * self.Bd.T
        ya = 0.5 * (y[:, 0] - y[:, 1])
        self.x = self.x + (ya - self.x @ self.C.ravel())[:, None] * self.L[None, :]

    def rollout(self, U):
        E, N, H = U.shape
        x = np.broadcast_to(self.x[:, None, :], (E, N, self.nx)).copy()
        out = np.zeros((E, N, H))
        AT, b, c = self.Ad.T, self.Bd.ravel(), self.C.ravel()
        for h in range(H):
            x = x @ AT + U[:, :, h, None] * b
            out[:, :, h] = x @ c
        return out, -out

    def simulate(self, A):
        """Open-loop output for accelerations A (n, T) from rest: (n, T+1)."""
        n, T = A.shape
        x = np.zeros((n, self.nx)); out = np.zeros((n, T + 1))
        for t in range(T):
            x = x @ self.Ad.T + A[:, t, None] * self.Bd.T
            out[:, t + 1] = x @ self.C.ravel()
        return out


class Pendulum:
    """Single equivalent pendulum whose normal follows the (flat) liquid surface:
    th'' = -(g/L) sin th - c th' - (u/L) cos th,  wall elevation = kap * tan th.
    theta = [L, c, kap]."""

    SUBSTEPS = 2

    def __init__(self, theta):
        self.theta = np.asarray(theta, float)
        self.Lp, self.c, self.kap = self.theta
        # observer gain from the linearisation (state th, th'; output th)
        Ad, Bd, C = _sm_matrices([G / self.Lp, self.c, 1.0 / self.Lp])
        self.L = _kalman_gain(Ad, Bd, C, OBS_R / self.kap ** 2, OBS_Q)

    def _f(self, th, om, u):
        return om, -(G / self.Lp) * np.sin(th) - self.c * om - (u / self.Lp) * np.cos(th)

    def _step(self, th, om, u):
        dt = DT / self.SUBSTEPS
        for _ in range(self.SUBSTEPS):
            a1, b1 = self._f(th, om, u)
            a2, b2 = self._f(th + 0.5 * dt * a1, om + 0.5 * dt * b1, u)
            a3, b3 = self._f(th + 0.5 * dt * a2, om + 0.5 * dt * b2, u)
            a4, b4 = self._f(th + dt * a3, om + dt * b3, u)
            th = th + dt / 6 * (a1 + 2 * a2 + 2 * a3 + a4)
            om = om + dt / 6 * (b1 + 2 * b2 + 2 * b3 + b4)
        return th, om

    def reset(self, E, rng):
        self.th = np.zeros(E); self.om = np.zeros(E)

    def observe(self, y, a_prev):
        if a_prev is not None:
            self.th, self.om = self._step(self.th, self.om, a_prev)
        ya = 0.5 * (y[:, 0] - y[:, 1])
        innov = np.arctan(ya / self.kap) - self.th
        self.th = self.th + self.L[0] * innov
        self.om = self.om + self.L[1] * innov

    def rollout(self, U):
        E, N, H = U.shape
        th = np.broadcast_to(self.th[:, None], (E, N)).copy()
        om = np.broadcast_to(self.om[:, None], (E, N)).copy()
        out = np.zeros((E, N, H))
        for h in range(H):
            th, om = self._step(th, om, U[:, :, h])
            out[:, :, h] = self.kap * np.tan(th)
        return out, -out

    def simulate(self, A):
        n, T = A.shape
        th = np.zeros(n); om = np.zeros(n); out = np.zeros((n, T + 1))
        for t in range(T):
            th, om = self._step(th, om, A[:, t])
            out[:, t + 1] = self.kap * np.tan(th)
        return out


def sysid_data(seed, truth, n_traj=40, T=100):
    """System-identification experiment on the nominal liquid: excitation
    trajectories and the noisy antisymmetric probe signal."""
    d = plant.make_dataset(seed, 10, n_traj, T, "nominal", truth)
    rng = np.random.default_rng([seed, 11])
    Y = plant.read_sensors(rng, "probe", d["O"], d["F"])
    return d["A"], 0.5 * (Y[..., 0] - Y[..., 1])


def fit_parametric(kind, seed, truth):
    """Output-error least-squares fit. kind in {pendulum, springmass, springmass2}."""
    path = os.path.join(MODEL_DIR, f"{kind}_{truth}_s{seed}.npy")
    if os.path.exists(path):
        theta = np.load(path)
    else:
        A, ya = sysid_data(seed, truth)
        w1sq = G * np.pi / W * np.tanh(np.pi * 0.03 / W)   # rough initial guess only
        if kind == "pendulum":
            x0 = np.array([G / w1sq, 1.0, W / (2 * FREE)])
            res = lambda th: (Pendulum(th).simulate(A) - ya).ravel()
            lb, ub = [0.005, 0.0, 0.5], [1.0, 50.0, 50.0]
        else:
            n = 2 if kind == "springmass2" else 1
            x0 = np.array([w1sq, 1.0, 0.5 * w1sq, 4.5 * w1sq, 2.0, 0.05 * 4.5 * w1sq][:3 * n])
            res = lambda th: (SpringMass(th).simulate(A) - ya).ravel()
            lb, ub = [1.0, 0.0, -1e4] * n, [1e4, 100.0, 1e4] * n
        theta = least_squares(res, x0, bounds=(lb, ub), x_scale=np.abs(x0) + 1e-3).x
        os.makedirs(MODEL_DIR, exist_ok=True)
        np.save(path, theta)
    return Pendulum(theta) if kind == "pendulum" else SpringMass(theta)


class Oracle:
    """The true plant model with the true state and parameters (privileged)."""

    def reset(self, E, rng):
        pass

    def set_truth(self, liq, s):
        self.liq = liq.expand()
        self.s = s

    def observe(self, y, a_prev):
        pass

    def rollout(self, U):
        E, N, H = U.shape
        s = tuple(np.broadcast_to(a[:, None], (E, N)).copy() for a in self.s)
        sR = np.zeros((E, N, H)); sL = np.zeros((E, N, H))
        for h in range(H):
            s = self.liq.step(s, U[:, :, h])
            sR[:, :, h], sL[:, :, h] = self.liq.walls(s)
        return sR, sL


# ----------------------------------------------------------------------------
# learned predictor with a history encoder
# ----------------------------------------------------------------------------
A_SCALE = 0.5      # accelerations are multiplied by this before entering a network
NFRAME = 3         # wall-elevation frames forming the dynamics state
ENC_H, DYN_H = 128, 96
UNROLL = 15


def _np_mlp(layers, X):
    for i, (Wt, b) in enumerate(layers):
        X = X @ Wt + b
        if i < len(layers) - 1:
            np.maximum(X, 0, out=X)
    return X


class Learned:
    """Encoder: window of K sensor readings and K cart accelerations -> latent
    liquid context z and an estimate of the last NFRAME wall-elevation frames.
    Dynamics: (frames, last 2 accelerations, next acceleration, z) -> next frame.
    K=0 disables the encoder: frames are the raw probe readings, no z."""

    def __init__(self, weights, K, zdim, sensor):
        self.K, self.zdim, self.sensor = K, zdim, sensor
        self.ny = SENSORS[sensor]["dim"]
        self.enc = weights.get("enc")
        self.dyn = weights["dyn"]
        self.P = max(K, NFRAME)

    def reset(self, E, rng):
        noise = SENSORS[self.sensor].get("noise", 0.0)
        self.Y = rng.normal(0, 1, (E, self.P, self.ny)).astype(np.float32) * noise
        self.A = np.zeros((E, self.P), np.float32)
        self.first = True

    def observe(self, y, a_prev):
        if a_prev is not None:
            self.Y = np.concatenate([self.Y[:, 1:], y[:, None, :].astype(np.float32)], axis=1)
            self.A = np.concatenate([self.A[:, 1:], a_prev[:, None].astype(np.float32)], axis=1)
        else:
            self.Y[:, -1] = y

    def _estimate(self):
        E = self.Y.shape[0]
        if self.K == 0:
            return self.Y[:, -NFRAME:, :].reshape(E, -1), np.zeros((E, 0), np.float32)
        X = np.concatenate([self.Y[:, -self.K:].reshape(E, -1), self.A[:, -self.K:] * A_SCALE], axis=1)
        out = _np_mlp(self.enc, X)
        return out[:, self.zdim:], out[:, :self.zdim]

    def rollout(self, U):
        E, N, H = U.shape
        fr, z = self._estimate()
        B = E * N
        nf = 2 * NFRAME
        X = np.zeros((B, nf + 3 + self.zdim), np.float32)
        X[:, :nf] = np.repeat(fr, N, axis=0)
        X[:, nf] = np.repeat(self.A[:, -2], N) * A_SCALE
        X[:, nf + 1] = np.repeat(self.A[:, -1], N) * A_SCALE
        if self.zdim:
            X[:, nf + 3:] = np.repeat(z, N, axis=0)
        Uf = U.reshape(B, H).astype(np.float32) * A_SCALE
        sR = np.zeros((B, H), np.float32); sL = np.zeros((B, H), np.float32)
        for h in range(H):
            X[:, nf + 2] = Uf[:, h]
            new = X[:, nf - 2:nf] + _np_mlp(self.dyn, X)
            X[:, :nf - 2] = X[:, 2:nf]
            X[:, nf - 2:nf] = new
            X[:, nf] = X[:, nf + 1]
            X[:, nf + 1] = Uf[:, h]
            sR[:, h] = new[:, 0]; sL[:, h] = new[:, 1]
        return sR.reshape(E, N, H).astype(float), sL.reshape(E, N, H).astype(float)


def train_learned(seed, truth, sensor="probe", K=30, zdim=4, n_data=50000, steps=2500, verbose=False):
    """Train (or load from the cache) the learned predictor on excitation data
    drawn over the training range of liquid parameters."""
    tag = f"learned_{truth}_{sensor}_K{K}_z{zdim}_n{n_data}_s{seed}"
    path = os.path.join(MODEL_DIR, tag + ".npz")
    if os.path.exists(path):
        raw = np.load(path)
        w = {}
        for part in ("enc", "dyn"):
            n = sum(1 for k in raw.files if k.startswith(part + "_W"))
            if n:
                w[part] = [(raw[f"{part}_W{i}"], raw[f"{part}_b{i}"]) for i in range(n)]
        return Learned(w, K, zdim, sensor)

    import torch
    import torch.nn as nn
    torch.set_num_threads(2)
    torch.manual_seed(seed)
    T = 100
    n_traj = max(1, n_data // T)
    d = plant.make_dataset(seed, 0, n_traj, T, "train", truth)
    rng = np.random.default_rng([seed, 1])
    Y = plant.read_sensors(rng, sensor, d["O"], d["F"])
    ny = Y.shape[-1]
    P = max(K, NFRAME)
    noise = SENSORS[sensor].get("noise", 0.0)
    Yp = np.concatenate([rng.normal(0, 1, (n_traj, P, ny)) * noise, Y], axis=1)
    Op = np.concatenate([np.zeros((n_traj, P, 2)), d["O"]], axis=1)
    Ap = np.concatenate([np.zeros((n_traj, P)), d["A"]], axis=1) * A_SCALE
    Yp, Op, Ap = (torch.tensor(a, dtype=torch.float32) for a in (Yp, Op, Ap))

    def mlp(i, h, o):
        return nn.Sequential(nn.Linear(i, h), nn.ReLU(), nn.Linear(h, h), nn.ReLU(), nn.Linear(h, o))

    nf = 2 * NFRAME
    enc = mlp(K * ny + K, ENC_H, zdim + nf) if K > 0 else None
    dyn = mlp(nf + 3 + zdim, DYN_H, 2)
    params = list(dyn.parameters()) + (list(enc.parameters()) if enc is not None else [])
    opt = torch.optim.Adam(params, lr=2e-3)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, steps, eta_min=1e-4)
    gen = torch.Generator().manual_seed(seed)
    batch = 256
    ar = torch.arange(batch)
    for it in range(steps):
        tr = torch.randint(0, n_traj, (batch,), generator=gen)
        i = torch.randint(P, P + T - UNROLL + 1, (batch,), generator=gen)   # index of the current reading
        if K > 0:
            widx = i[:, None] + torch.arange(-K + 1, 1)[None, :]
            xin = torch.cat([Yp[tr[:, None], widx].reshape(batch, -1), Ap[tr[:, None], widx - 1]], dim=1)
            out = enc(xin)
            z, fr = out[:, :zdim], out[:, zdim:]
        else:
            fidx = i[:, None] + torch.arange(-NFRAME + 1, 1)[None, :]
            fr = Yp[tr[:, None], fidx].reshape(batch, -1)
            z = torch.zeros(batch, 0)
        fidx = i[:, None] + torch.arange(-NFRAME + 1, 1)[None, :]
        loss = ((fr - Op[tr[:, None], fidx].reshape(batch, -1)) ** 2).mean() if K > 0 else 0.0
        a0, a1 = Ap[tr, i - 2], Ap[tr, i - 1]
        roll = 0.0
        for r in range(1, UNROLL + 1):
            u = Ap[tr, i + r - 1]
            new = fr[:, -2:] + dyn(torch.cat([fr, a0[:, None], a1[:, None], u[:, None], z], dim=1))
            roll = roll + ((new - Op[tr, i + r]) ** 2).mean()
            fr = torch.cat([fr[:, 2:], new], dim=1)
            a0, a1 = a1, u
        loss = loss + roll / UNROLL
        opt.zero_grad(); loss.backward(); opt.step(); sched.step()
        if verbose and it % 250 == 0:
            print(it, float(loss), flush=True)

    def export(net):
        return [(m.weight.detach().numpy().T.copy(), m.bias.detach().numpy().copy())
                for m in net if isinstance(m, nn.Linear)]

    w = {"dyn": export(dyn)}
    if enc is not None:
        w["enc"] = export(enc)
    os.makedirs(MODEL_DIR, exist_ok=True)
    np.savez(path, **{f"{p}_{n}{i}": arr for p, layers in w.items()
                      for i, (Wt, b) in enumerate(layers) for n, arr in (("W", Wt), ("b", b))})
    return Learned(w, K, zdim, sensor)
