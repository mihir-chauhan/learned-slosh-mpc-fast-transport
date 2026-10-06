"""Ground-truth plant: a planar cart carrying a brim-full rectangular container.

The liquid is a reduced-order two-mode slosh model. Modal amplitudes are
normalised by the freeboard, so a wall elevation of 1 means the surface is at
the brim. Everything is vectorised over a leading batch shape.
"""
import numpy as np

G = 9.81
W = 0.12        # container width along the motion axis [m]
FREE = 0.010    # freeboard: brim height above the rest surface [m]
DT = 0.03       # control period [s]
SUB = 6         # RK4 substeps per control period
U_MAX = 4.0     # cart acceleration limit [m/s^2]
GOAL = 1.0      # transport distance [m]
ZETA2_RATIO = 1.5   # damping of mode 2 relative to mode 1

NOMINAL = dict(zeta=0.03, h=0.035)
TRAIN_RANGE = dict(zeta=(0.01, 0.08), h=(0.020, 0.050))
HELDOUT_RANGE = dict(zeta=((0.005, 0.010), (0.08, 0.12)), h=((0.014, 0.020), (0.050, 0.070)))

# nonlinearity of the "full" ground truth (dimensionless, in freeboard units)
NONLIN = dict(kappa=0.3, delta=0.5, eps=0.08, beta=0.15)

# sensor noise (standard deviations) and camera latency
SENSORS = {
    "cart": dict(dim=0),
    "probe": dict(dim=2, noise=0.03),            # both wall heights, freeboard units
    "ft": dict(dim=1, noise=0.05),               # specific lateral slosh force [m/s^2]
    "cam": dict(dim=1, noise=0.08, delay=2),     # surface tilt proxy, freeboard units
}


def sample_params(rng, n, mode):
    """Liquid parameters (damping ratio of mode 1, liquid depth) for n episodes."""
    if mode == "nominal":
        return np.full(n, NOMINAL["zeta"]), np.full(n, NOMINAL["h"])
    if mode == "train":
        lo, hi = TRAIN_RANGE["zeta"]
        zeta = np.exp(rng.uniform(np.log(lo), np.log(hi), n))
        h = rng.uniform(*TRAIN_RANGE["h"], n)
        return zeta, h
    if mode == "heldout":
        out = []
        for key in ("zeta", "h"):
            (a0, a1), (b0, b1) = HELDOUT_RANGE[key]
            side = rng.random(n) < 0.5
            out.append(np.where(side, rng.uniform(a0, a1, n), rng.uniform(b0, b1, n)))
        return out[0], out[1]
    raise ValueError(mode)


class Liquid:
    """Two antisymmetric slosh modes of a rectangular tank (linear modal theory:
    omega_n^2 = g k_n tanh(k_n h), wall gain 4 tanh(k_n h)/(w k_n)), plus
    optional nonlinear terms. truth in {"full", "lin2", "lin1"}."""

    def __init__(self, zeta, h, truth="full"):
        zeta = np.asarray(zeta, float)
        h = np.asarray(h, float)
        k1, k2 = np.pi / W, 3 * np.pi / W
        t1, t2 = np.tanh(k1 * h), np.tanh(k2 * h)
        self.w1sq, self.w2sq = G * k1 * t1, G * k2 * t2
        self.w1, self.w2 = np.sqrt(self.w1sq), np.sqrt(self.w2sq)
        self.g1 = 4 * t1 / (W * k1) / FREE
        self.g2 = 4 * t2 / (W * k2) / FREE
        self.z1, self.z2 = zeta, ZETA2_RATIO * zeta
        # centre-of-mass shift per unit modal amplitude (for the force sensor)
        self.c1 = 2 * FREE / (h * W * k1 ** 2)
        self.c2 = 2 * FREE / (h * W * k2 ** 2)
        self.truth = truth
        nl = NONLIN if truth == "full" else dict(kappa=0.0, delta=0.0, eps=0.0, beta=0.0)
        self.kappa, self.delta, self.eps, self.beta = nl["kappa"], nl["delta"], nl["eps"], nl["beta"]
        if truth == "lin1":
            self.g2 = self.g2 * 0.0

    def expand(self):
        """Add a trailing axis to every parameter (for rollouts of shape (E, N))."""
        import copy
        o = copy.copy(self)
        for k in ("w1sq", "w2sq", "w1", "w2", "g1", "g2", "z1", "z2", "c1", "c2"):
            setattr(o, k, np.asarray(getattr(self, k))[..., None])
        return o

    def deriv(self, s, u):
        p1, v1, p2, v2 = s
        a1 = (-2 * self.z1 * self.w1 * (1 + self.delta * np.abs(p1)) * v1
              - self.w1sq * p1 / np.sqrt(1 + self.kappa * p1 * p1) - self.g1 * u)
        a2 = -2 * self.z2 * self.w2 * v2 - self.w2sq * (p2 + self.eps * p1 ** 3) - self.g2 * u
        return (v1, a1, v2, a2)

    def step(self, s, u):
        """One control period with the acceleration u held constant (RK4)."""
        dt = DT / SUB
        for _ in range(SUB):
            k1 = self.deriv(s, u)
            k2 = self.deriv(tuple(a + 0.5 * dt * b for a, b in zip(s, k1)), u)
            k3 = self.deriv(tuple(a + 0.5 * dt * b for a, b in zip(s, k2)), u)
            k4 = self.deriv(tuple(a + dt * b for a, b in zip(s, k3)), u)
            s = tuple(a + dt / 6 * (b + 2 * c + 2 * d + e) for a, b, c, d, e in zip(s, k1, k2, k3, k4))
        return s

    def walls(self, s):
        """Normalised surface elevation at the right and left wall."""
        p1, _, p2, _ = s
        asym = self.beta * p1 * p1
        return p1 + p2 + asym, -p1 - p2 + asym

    def force(self, s, u):
        """Specific lateral slosh force: acceleration of the liquid centre of mass
        relative to the container [m/s^2]."""
        _, a1, _, a2 = self.deriv(s, u)
        return self.c1 * a1 + self.c2 * a2

    def zero_state(self, shape):
        z = np.zeros(shape)
        return (z, z.copy(), z.copy(), z.copy())


def excitation(rng, n, T):
    """Random acceleration sequences (n, T): piecewise-constant, transport-like
    bang-coast-bang, chirp and smooth noise, mixed."""
    A = np.zeros((n, T))
    t = np.arange(T) * DT
    for i in range(n):
        kind = rng.integers(4)
        if kind == 0:
            j = 0
            while j < T:
                hold = rng.integers(1, 13)
                A[i, j:j + hold] = rng.uniform(-3.0, 3.0) * (rng.random() < 0.8)
                j += hold
        elif kind == 1:
            a = rng.uniform(0.5, 3.0) * rng.choice([-1, 1])
            t1 = rng.integers(8, 30)
            coast = rng.integers(0, 20)
            dec = rng.uniform(0.5, 3.0)
            t2 = int(min(T, round(abs(a) * t1 / dec)))
            A[i, :t1] = a
            A[i, t1 + coast:t1 + coast + t2] = -np.sign(a) * dec
            A[i] += rng.normal(0, 0.3, T)
        elif kind == 2:
            f0, f1 = rng.uniform(0.3, 2.0), rng.uniform(2.0, 5.5)
            if rng.random() < 0.5:
                f0, f1 = f1, f0
            f = f0 + (f1 - f0) * t / t[-1]
            A[i] = rng.uniform(0.2, 1.2) * np.sin(2 * np.pi * np.cumsum(f) * DT + rng.uniform(0, 6.28))
        else:
            x = rng.normal(0, 1, T + 20)
            wlen = rng.integers(2, 10)
            x = np.convolve(x, np.ones(wlen) / wlen, mode="same")[10:10 + T]
            A[i] = x / (x.std() + 1e-9) * rng.uniform(0.3, 1.5)
    return np.clip(A, -U_MAX, U_MAX)


def simulate(liq, A):
    """Roll the liquid from rest under accelerations A (n, T). Returns the wall
    elevations O (n, T+1, 2), the force signal F (n, T+1) and the states."""
    n, T = A.shape
    s = liq.zero_state(n)
    O = np.zeros((n, T + 1, 2))
    F = np.zeros((n, T + 1))
    for t in range(T):
        s = liq.step(s, A[:, t])
        O[:, t + 1, 0], O[:, t + 1, 1] = liq.walls(s)
        F[:, t + 1] = liq.force(s, A[:, t])
    return O, F


def make_dataset(seed, stream, n_traj, T, pmode, truth, max_amp=1.5):
    """n_traj excitation trajectories of T steps. A brim-full container cannot be
    excited far past the brim, so a trajectory whose surface exceeds max_amp
    freeboards is redrawn with its amplitude scaled down by 0.8 per attempt."""
    rng = np.random.default_rng([seed, stream])
    A = np.zeros((n_traj, T)); O = np.zeros((n_traj, T + 1, 2)); F = np.zeros((n_traj, T + 1))
    Z = np.zeros(n_traj); H = np.zeros(n_traj)
    todo = np.arange(n_traj)
    scale = 1.0
    while len(todo):
        zeta, h = sample_params(rng, len(todo), pmode)
        a = excitation(rng, len(todo), T) * scale
        o, f = simulate(Liquid(zeta, h, truth), a)
        A[todo], O[todo], F[todo], Z[todo], H[todo] = a, o, f, zeta, h
        todo = todo[np.abs(o).max(axis=(1, 2)) > max_amp]
        scale *= 0.8
    return dict(A=A, O=O, F=F, zeta=Z, h=H)


def read_sensors(rng, sensor, O, F):
    """Noisy sensor readings Y (n, T+1, dim) from true wall elevations and force."""
    spec = SENSORS[sensor]
    n, T1 = O.shape[:2]
    if sensor == "cart":
        return np.zeros((n, T1, 0))
    if sensor == "probe":
        return O + rng.normal(0, spec["noise"], O.shape)
    if sensor == "ft":
        return (F + rng.normal(0, spec["noise"], F.shape))[..., None]
    if sensor == "cam":
        tilt = 0.5 * (O[..., 0] - O[..., 1])
        d = spec["delay"]
        tilt = np.concatenate([np.zeros((n, d)), tilt[:, :T1 - d]], axis=1)
        return (tilt + rng.normal(0, spec["noise"], tilt.shape))[..., None]
    raise ValueError(sensor)
