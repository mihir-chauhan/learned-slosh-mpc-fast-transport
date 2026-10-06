# Design

Everything is numpy (plant, parametric models, MPC, inference of the learned model); torch is used only to
train the learned predictor. One entrypoint: `python method/run.py --system <s> --task <t> --seed <n> --out <json>`.

## Plant (`plant.py`)
- Cart: double integrator, acceleration command clipped to +-4 m/s^2, control period 0.03 s, 1 m move.
- Container: rectangular, width 0.12 m, freeboard 0.010 m. All surface quantities are in freeboard units; spill
  when the larger of the two wall elevations exceeds 1.
- Liquid ("full" truth): modes n=1,2 with k_n=(2n-1)pi/w, omega_n^2 = g k_n tanh(k_n h), wall gain
  4 tanh(k_n h)/(w k_n); damping zeta (mode 1) and 1.5 zeta (mode 2). Nonlinear terms: softening stiffness
  p/sqrt(1+0.3 p^2), amplitude-dependent damping (1+0.5|p|), cubic forcing of mode 2 by mode 1 (0.08), wall
  asymmetry +0.15 p1^2 on both walls. RK4, 6 substeps per control period. "lin1": single linear mode.
- Liquid parameters: nominal zeta=0.03, h=0.035 m; training range zeta in [0.01,0.08] (log-uniform), h in
  [0.020,0.050]; held-out zeta in [0.005,0.01] or [0.08,0.12], h in [0.014,0.020] or [0.050,0.070].
- Sensors: probe (two wall heights, noise 0.03), force/torque (specific slosh force, noise 0.05 m/s^2), camera
  proxy (surface tilt, noise 0.08, 2-step latency), cart only (no liquid reading). Cart position, velocity and
  the measured acceleration of the last period are always available.
- Push: velocity change (0.04 m/s in the main tasks) spread over two control periods at a random time in
  [0.24, 1.35) s with random sign.

## Models (`models.py`)
- Pendulum (L, damping, output scale), spring-mass (k, c, b), two-mode spring-mass (6 parameters): output-error
  least squares (`scipy.optimize.least_squares`) on 40 excitation trajectories x 100 steps of the nominal liquid
  with probe noise. State from a steady-state Kalman observer on the antisymmetric probe signal.
- Learned: encoder MLP (K=30 readings and accelerations -> 128 -> 128 -> z (4) + 3 frames of 2 wall
  elevations); dynamics MLP (3 frames, 2 past accelerations, next acceleration, z -> 96 -> 96 -> elevation
  increment). Loss: frame-estimate MSE + mean MSE of a 15-step unroll. Adam, lr 2e-3 cosine to 1e-4, 2500 steps,
  batch 256, 50k transitions (500 trajectories x 100 steps) over the training range. Excitation trajectories
  are redrawn at lower amplitude if the surface exceeds 1.5 freeboards.
- No-context variant: same encoder used only as state estimator (z dimension 0). History 0: raw last 3 probe frames.
- Oracle: true model, true state, true parameters.

## Controller (`mpc.py`)
- MPPI, 64 samples, horizon 30 steps (0.9 s), 2 iterations per step (6 at the first step), temperature 0.01,
  smooth knot noise (knot spacing 5 steps, sigma 0.6 for even samples and 0.18 for odd samples), plus 16
  structured candidates (nominal retimed, rescaled, ramp offsets). Noise shrinks as the cart settles.
- Cost: dt * sum of a smooth "not at goal" indicator + minimum-time-to-go of the double integrator at the horizon
  end (acceleration bound = margin x 2 m/s^2) + 50 * sum of squared margin violation + 5 * max violation
  + 0.01 * squared acceleration increments + 1e-4 * squared acceleration.
- ZV input shaping: bang-bang profile of peak a_peak convolved with a two-impulse ZV shaper from the fitted
  spring-mass frequency and damping; PD tracking (kp=100, kd=20).
- Episode 3.3 s (110 steps). Arrival: first step after which |x-1|<0.01 m and |v|<0.03 m/s until the end.
