# Learned Versus Pendulum Slosh Models in MPC for Fast Spill-Free Cart Transport

## Seed
I want to create a robot system that can handel transporting a container filled with fluid (to the brim). this system needs to be able to identify the state of the liquid, identify the properties of the liquid based on how it moves (traits like viscosity, etc to help with prediction), a model or some kind of predictor that takes in the current state, potentially a numerical fluid simulation formula (navier stokes equation) to find the optimal position and movement to transport the container object from one location to another. this means that the system needs to have a policy for grasping position and for movement and trajectory. it should be able to handle slight external force interruption to at least minimize the amount of spillage, and it  should also be able to identify close to spill or spill and stop, slow down, etc. this system is best if it is adaptable.

## Clarifications
- **Which core research question should the study test?** Does a learned slosh-dynamics predictor inside MPC or trajectory optimization beat a simple pendulum or spring-mass slosh model?
- **What setting should the experiments run in?** Quick CPU study: a 2D or 3D reduced-order slosh model (pendulum or spring-mass) on a simulated cart or arm in MuJoCo, with liquid parameters varied
- **How should the system perceive the liquid state, and how will liquid properties be identified?** we want to find a good solution so test all cameras and sensors (po
- **What does success look like, and which baselines must be beaten?** spill free is easy. we want to make it the fastest spill free transport system
- **How much scope and what prior assets do you have?** Mid-size study on a single GPU, with a few days of compute and no real robot
- **Notes:** spill free is easy. we want to make it the fastest spill free transport system

## Research question
Does a learned slosh-dynamics predictor inside sampling-based MPC enable faster spill-free container transport than MPC using a fitted pendulum or spring-mass slosh model, across varied liquid parameters and external pushes?

## Hypotheses
- H1: Under nominal liquid parameters, MPC with a learned slosh predictor reaches a lower spill-free transport time than MPC with a parameter-fitted pendulum model, measured over 3 or more seeds with non-overlapping confidence intervals.
- H2: Under held-out liquid parameters (viscosity-like damping and fill level) and random lateral impulses, the learned predictor with online context inference (a history encoder) keeps spill rate lower than a fixed-parameter pendulum MPC at equal transport time.
- H3: Learned-model advantage shrinks or vanishes when the ground-truth slosh is well described by a single-mode pendulum. This is falsified if the learned model still wins on that setting by a margin above seed noise.
- H4: A richer sensing set (cart state only vs. plus slosh-height or force/torque vs. plus a noisy camera-derived surface-angle estimate) changes the achievable spill-free time, and force/torque is the most informative single addition per unit noise.

## Baselines
- Single-mass pendulum slosh model in MPC (reimplemented, parameters fit by least squares)
- Spring-mass-damper slosh model in MPC (reimplemented)
- Input-shaping / jerk-limited open-loop trajectory (reimplemented)
- MPPI with the learned model but no latent liquid-property inference (ablation baseline, reimplemented)

## Tasks
- MuJoCo planar cart carrying a brim-full container, 1 m point-to-point transport, with a reduced-order two-mode nonlinear slosh ground truth
- Liquid parameter sweep: damping (viscosity proxy) and fill level, with train and held-out ranges
- Perturbation test: random lateral impulse during transport (3 magnitudes)
- Sensor-set comparison on simulated sensors: cart state only, plus force/torque, plus slosh-height probe, plus noisy surface-angle (camera proxy)

## Metrics
- Spill-free transport time in seconds (lower is better)
- Spill rate over 100 episodes per condition (lower is better)
- Peak normalized surface displacement relative to the brim (lower is better)
- One-step and 20-step slosh prediction RMSE (lower is better)
- MPC solve time per step in ms (lower is better)

## Ablations
- With vs. without latent liquid-property encoder (history length 0, 10, 30 steps)
- Training data size for the learned predictor (1k, 10k, 50k transitions)
- Sensor set (cart only, plus force/torque, plus slosh height, plus noisy angle)
- MPC horizon length and number of samples
- Model-mismatch: ground truth with vs. without nonlinearity

## Plan
- Implement the MuJoCo cart and container with the reduced-order slosh ground truth, the spill criterion, and a parameter randomizer with train and held-out ranges.
- Collect excitation data (random and chirp accelerations) over the train range; fit the pendulum and spring-mass baselines by least squares.
- Train the learned predictor (MLP and GRU with history encoder) on CPU, checking one-step and rollout RMSE on held-out parameters.
- Implement MPPI/CEM MPC with a pluggable model and a time-minimizing cost with a spill-margin constraint, plus the input-shaping baseline.
- Search for the minimum spill-free transport time for each method by sweeping the time budget, with 3 or more seeds and 100 episodes per condition in the nominal, held-out parameter, and perturbation settings.
- Run the sensor and encoder ablations, aggregate the mean and std over seeds, and report the results, including any negative results.

## Out of scope
- Full Navier-Stokes or SPH/CFD simulation of the liquid
- Real robot hardware and real camera perception of liquid
- Grasp-pose policy learning and 6-DoF arm manipulation
- Stop/slow-down spill-detection policy beyond the MPC spill margin
- GPU-scale training and foundation-model or VLA policies
- Real-fluid property identification beyond damping and fill level proxies

## Method
Build a MuJoCo cart (1D/2D planar) carrying a container whose liquid is simulated as a reduced-order multi-mode slosh system (a ground-truth two-mode spring-damper-pendulum model with nonlinearity, damping, and fill-level parameters randomized, plus a spill event when the surface displacement exceeds the brim). Train a small MLP or GRU one-step slosh predictor with a history encoder that infers latent liquid properties (damping, fill) from recent motion, and plug it into a sampling-based MPC (MPPI/CEM) that minimizes transport time subject to a spill margin. Compare it with the same MPC using a pendulum and a spring-mass model with parameters fitted by system identification, and with a fixed-profile open-loop baseline.

Field: control-systems learning-control-sysid
Scale: quick study, cpu, about 40 minutes of experiments.
