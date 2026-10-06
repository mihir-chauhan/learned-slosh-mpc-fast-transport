# Protocol

- **Tasks.** nominal (nominal liquid), heldout (held-out damping and depth), heldout_push (held-out liquid +
  one lateral push of 0.04 m/s), lin1 (nominal liquid, single linear mode ground truth; all models refit /
  retrained on that truth).
- **Splits.** Model data: random stream 0/1 (learned) or 10/11 (system identification) of the seed. Validation
  episodes: stream 100. Test episodes: stream 200. Prediction test set: stream 300. No test episode is used for
  any choice.
- **Tuning budget.** One scalar per system: the spill margin (MPC systems; grid 0.6, 0.7, 0.8, 0.85, 0.9, 0.95,
  1.0) or the peak acceleration (ZV shaping; grid 0.9..1.5). Chosen by `experiments/select.py`: the largest grid
  value such that it and every smaller value has zero spills and full arrival on the validation episodes of the
  nominal task pooled over seeds 0-2 (30 episodes each). lin1 has its own selection on lin1 validation
  episodes (grid 0.8, 0.9, 0.95, 1.0; shaping 1.4..1.9). MPPI hyperparameters were set once with the oracle
  model on development seed 100 (not reported) and are shared by every system.
- **Seeds.** Main table: seeds 0-4, 50 test episodes per run (250 per condition). Ablations and sweeps: seeds
  0-2, 50 episodes.
- **Metrics.** transport_time_s (mean arrival time; 3.3 s if never arrived), spill_rate, peak_disp (mean
  per-episode maximum wall elevation, freeboard units), arrive_rate, penalised_time_s (as transport time but a
  spilled or non-arrived episode counts 3.3 s), pred_rmse_1 / pred_rmse_20 (open-loop wall-elevation error 1
  and 20 steps ahead on 100 fresh excitation trajectories of the task's liquid range), solve_ms (controller
  wall-clock per step for the whole batch of episodes; not reproducible).
- **Hardware.** Shared CPU, 2 threads.
