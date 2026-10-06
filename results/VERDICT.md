# Verdict: tier 0 (not best) — target tier 2 (solid)

Method: Learned-Ctx MPC | primary metric: penalised_time_s | primary task: nominal

| Task | Ours | Best baseline | Their mean | Rel. gain | p | Cohen d | n |
|---|---|---|---|---|---|---|---|
| heldout | 2.026 | Learned MPC (no context) | 2.165 | +6.4% | 0.0144 | 1.98 | 5 |
| heldout_push | 2.173 | Pendulum MPC | 2.272 | +4.4% | 0.000197 | 2.73 | 5 |
| lin1 | 1.797 | ZV input shaping | 1.65 | -8.9% | 1.89e-05 | -14.97 | 5 |
| nominal | 1.993 | ZV input shaping | 1.89 | -5.5% | 2.04e-05 | -14.68 | 5 |

| Ablation | Delta vs full | p | Matters? |
|---|---|---|---|
| abl_history (encoder history 0/10/30) | missing |  | NO |
| abl_data (1k/10k/50k transitions) | missing |  | NO |
| abl_sensor (cart / +F/T / +probe / +camera proxy) | missing |  | NO |
| abl_mpc (horizon and samples) | missing |  | NO |
| sweep_push (push magnitude) | missing |  | NO |
| sweep_margin (spill margin) | missing |  | NO |

## Why this tier
- not best on nominal: ours 1.993 vs ZV input shaping 1.89

## To reach the next tier
- beat the best baseline on the primary task

TARGET NOT REACHED
