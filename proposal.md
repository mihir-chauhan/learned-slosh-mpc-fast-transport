# Proposal: learned versus pendulum slosh models in MPC for fast spill-free cart transport

## Question
Inside one time-minimising sampling-based MPC, does a learned slosh predictor with a history encoder give a
faster spill-free 1 m transport than a least-squares-fitted pendulum or spring-mass model?

## Landscape and gap
See `literature/landscape.md`. Pendulum and mass-spring models dominate slosh-aware planning
[muchacho2022solution; toth2024rapid; medico2026model; ferrari2026time]; learned liquid dynamics exist
[abderezaei2024clutter]; a like-for-like comparison of the model classes in the same controller is missing.

## Method
- Plant: planar cart (double integrator, |a| <= 4 m/s^2) carrying a rectangular container; liquid = two
  antisymmetric modes from linear modal theory plus amplitude-dependent stiffness and damping, mode coupling
  and crest/trough asymmetry. Spill = wall elevation above the freeboard.
- Learned-Ctx MPC: encoder (30 readings + accelerations -> latent context z and 3-frame state estimate) and MLP
  dynamics, trained on 50k excitation transitions over a training range of damping and depth; MPPI planner.
- Margin tuning: each system's spill margin is the largest value with zero spills on validation episodes of the
  nominal liquid; test episodes use different random streams.

## Hypotheses and what refutes them
| ID | Hypothesis | Group / task | Metric | Refuted if |
|---|---|---|---|---|
| H1 | learned MPC is faster than pendulum MPC, spill-free, on the nominal liquid | main / nominal | transport_time_s, spill_rate | learned is not faster, or spills more |
| H2 | on held-out liquids with pushes the learned model with encoder spills less at equal time | main / heldout_push, sweep_margin_hp | spill_rate vs transport_time_s | pendulum time-spill curve is at or below the learned curve |
| H3 | the learned advantage vanishes on a single linear mode | main / lin1 | transport_time_s | learned still faster by more than seed noise |
| H4 | sensing matters and F/T is the best single addition to cart-only | abl_sensor / heldout_push | spill_rate, transport_time_s, pred_rmse_20 | sets indistinguishable, or F/T not best |

## Baselines (all reimplemented here)
Pendulum MPC, spring-mass MPC, two-mode spring-mass MPC (all fitted by output-error least squares on the nominal
liquid, Kalman observer on the probe), ZV input shaping with PD tracking, learned MPC without latent context.
A privileged oracle MPC (true model and state) is a reference, not a baseline.

## Ablations
History length (0/10/30), training transitions (1k/10k/50k), sensor set, MPC horizon and samples, push magnitude.

## Risks
The sampling optimiser is not exactly time-optimal, so model differences can be masked by optimiser noise; the
ground truth is a reduced-order model chosen by the authors of the study, not CFD or a real liquid.
