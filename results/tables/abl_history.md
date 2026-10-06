| Method | transport_time_s | spill_rate | pred_rmse_20 | n |
|---|---|---|---|---|
| history 10 | _2.030 ± 0.022_ | **0.113 ± 0.012** | _0.238 ± 0.007_ | 3 |
| history 0 (no encoder) | 2.241 ± 0.087 | 0.160 ± 0.072 | 0.373 ± 0.008 | 3 |
| Learned-Ctx MPC | **2.026 ± 0.007** | _0.120 ± 0.020_ | **0.172 ± 0.014** | 3 |

Mean ± std over seeds; bold = best, underline = second. Directions: transport_time_s ↓, spill_rate ↓, pred_rmse_20 ↓.
