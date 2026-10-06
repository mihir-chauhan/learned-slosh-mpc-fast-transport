| Method | transport_time_s | spill_rate | pred_rmse_20 | n |
|---|---|---|---|---|
| cart only | 2.055 ± 0.042 | 0.673 ± 0.163 | 0.381 ± 0.017 | 3 |
| cart + camera proxy | **2.013 ± 0.010** | 0.247 ± 0.099 | 0.232 ± 0.007 | 3 |
| cart + force/torque | _2.022 ± 0.016_ | _0.153 ± 0.081_ | _0.177 ± 0.007_ | 3 |
| Learned-Ctx MPC | 2.026 ± 0.007 | **0.120 ± 0.020** | **0.172 ± 0.014** | 3 |

Mean ± std over seeds; bold = best, underline = second. Directions: transport_time_s ↓, spill_rate ↓, pred_rmse_20 ↓.
