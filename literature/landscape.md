# Landscape

Searches (all candidates in `literature/candidates.jsonl`): "slosh-free liquid container transport robot
trajectory optimization", "learned liquid dynamics model predictive control sloshing manipulation", "MPPI model
predictive path integral learned dynamics neural network", "online adaptation latent context encoder dynamics
model rapid motor adaptation", "input shaping sloshing suppression pendulum model container", plus three
title searches for source papers. Only titles and abstracts were read.

## What exists
- **Equivalent mechanical slosh models.** Mass-spring-damper and pendulum analogies are the standard reduced-order
  description of sloshing [capolupo2025equivalent]; a linear and a nonlinear mass-spring-damper model are used to
  estimate the sloshing height at the container wall for planar motions [guagliumi2021simple] and for 2-D motions
  of a cylindrical container with experiments up to 9.5 m/s^2 [leva2022sloshing].
- **Pendulum-based slosh-free planning.** A spherical-pendulum model with a QP trajectory optimiser
  [muchacho2022solution]; real-time slosh-free tracking that avoids the pendulum model through a virtual quadrotor
  [arrizabalaga2024geometric]; feedforward rest-to-rest manoeuvres with multi-mode pendulum parameters identified
  from a finite-element model [toth2024rapid].
- **Time-optimal anti-slosh planning and MPC.** Time-optimal trajectories with a bound on the liquid surface
  height for several containers [ferrari2026time]; real-time MPC with a nonlinear spherical-pendulum slosh model
  for containers on a tray [medico2026model]; MPC for time-optimal spill-free emergency stops
  [hynninen2026emergency].
- **Learned liquid dynamics.** Spill-free transport in clutter with a learned dynamics model
  [abderezaei2024clutter]. Humans appear to use simplified internal models when moving a sloshing cup
  [bazzi2024simplified].
- **Tools used here.** Sampling-based MPC: MPPI variants [asmar2022model; kicki2025lp], CEM planning through
  learned probabilistic ensembles [chua2018deep], GP residual models in MPC [hewing2017cautious]. Latent context
  inferred from history for adaptation: RMA [kumar2021rma], implicit identification [evans2022context]. Input
  shaping as a command-convolution method for vibration suppression [kotaniemi2025data].

## Closest work
[medico2026model], [ferrari2026time] and [hynninen2026emergency] solve fast or time-optimal slosh-bounded motion
with a fitted pendulum-type model. [abderezaei2024clutter] uses a learned model. None of the abstracts read
reports a head-to-head of the two model classes in the same time-minimising controller.

## Gap
A controlled comparison: same plant, same optimiser, same spill criterion, same tuning rule for the safety
margin, with the model class as the only change, including liquids outside the identification range, pushes and
different sensors. This study fills it only in simulation with a reduced-order ground truth.
