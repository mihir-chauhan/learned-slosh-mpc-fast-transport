| Method | transport_time_s | spill_rate | pred_rmse_20 | n |
|---|---|---|---|---|
| horizon 45 | 2.171 ± 0.025 | **0.087 ± 0.031** | 0.172 ± 0.014 | 3 |
| 32 samples | 2.158 ± 0.008 | _0.093 ± 0.064_ | 0.172 ± 0.014 | 3 |
| 128 samples | _1.992 ± 0.031_ | 0.113 ± 0.081 | 0.172 ± 0.014 | 3 |
| horizon 15 | **1.963 ± 0.021** | 0.113 ± 0.050 | _0.172 ± 0.014_ | 3 |
| Learned-Ctx MPC | 2.026 ± 0.007 | 0.120 ± 0.020 | **0.172 ± 0.014** | 3 |

Mean ± std over seeds; bold = best, underline = second. Directions: transport_time_s ↓, spill_rate ↓, pred_rmse_20 ↓.
