| Method | Task | transport_time_s | spill_rate | peak_disp | pred_rmse_20 | n |
|---|---|---|---|---|---|---|
| Pendulum MPC | nominal | 2.147 ± 0.012 | 0.000 ± 0.000 | **0.799 ± 0.010** | 0.135 ± 0.005 | 5 |
| ZV input shaping | nominal | **1.890 ± 0.000** | 0.000 ± 0.000 | 0.975 ± 0.007 | — | 5 |
| Learned MPC (no context) | nominal | 1.987 ± 0.018 | _0.000 ± 0.000_ | 0.904 ± 0.022 | _0.092 ± 0.003_ | 5 |
| Spring-mass MPC | nominal | 2.041 ± 0.014 | 0.000 ± 0.000 | 0.925 ± 0.011 | 0.136 ± 0.005 | 5 |
| Two-mode spring-mass MPC | nominal | _1.965 ± 0.007_ | 0.000 ± 0.000 | 0.904 ± 0.007 | 0.094 ± 0.007 | 5 |
| Learned-Ctx MPC | nominal | 1.993 ± 0.010 | **0.000 ± 0.000** | _0.887 ± 0.013_ | **0.063 ± 0.004** | 5 |
| Pendulum MPC | heldout | 2.193 ± 0.008 | **0.000 ± 0.000** | **0.800 ± 0.014** | 0.473 ± 0.015 | 5 |
| ZV input shaping | heldout | **1.890 ± 0.000** | 1.000 ± 0.000 | 1.253 ± 0.021 | — | 5 |
| Learned MPC (no context) | heldout | 2.043 ± 0.024 | 0.100 ± 0.071 | 0.902 ± 0.033 | _0.316 ± 0.013_ | 5 |
| Spring-mass MPC | heldout | 2.085 ± 0.010 | 0.104 ± 0.065 | 0.920 ± 0.016 | 0.470 ± 0.014 | 5 |
| Two-mode spring-mass MPC | heldout | 2.009 ± 0.015 | 0.228 ± 0.101 | 0.961 ± 0.021 | 0.462 ± 0.013 | 5 |
| Learned-Ctx MPC | heldout | _1.996 ± 0.009_ | _0.024 ± 0.017_ | _0.892 ± 0.019_ | **0.176 ± 0.012** | 5 |
| Pendulum MPC | heldout_push | 2.270 ± 0.032 | **0.008 ± 0.011** | **0.812 ± 0.014** | 0.473 ± 0.015 | 5 |
| ZV input shaping | heldout_push | **1.890 ± 0.000** | 0.972 ± 0.023 | 1.276 ± 0.026 | — | 5 |
| Learned MPC (no context) | heldout_push | 2.057 ± 0.008 | 0.184 ± 0.093 | 0.922 ± 0.026 | _0.316 ± 0.013_ | 5 |
| Spring-mass MPC | heldout_push | 2.160 ± 0.049 | 0.132 ± 0.097 | 0.932 ± 0.018 | 0.470 ± 0.014 | 5 |
| Two-mode spring-mass MPC | heldout_push | 2.029 ± 0.041 | 0.292 ± 0.125 | 0.972 ± 0.025 | 0.462 ± 0.013 | 5 |
| Learned-Ctx MPC | heldout_push | _2.024 ± 0.006_ | _0.120 ± 0.032_ | _0.915 ± 0.011_ | **0.176 ± 0.012** | 5 |
| Pendulum MPC | lin1 | 1.806 ± 0.005 | _0.000 ± 0.000_ | **0.898 ± 0.003** | 0.033 ± 0.000 | 5 |
| ZV input shaping | lin1 | **1.650 ± 0.000** | 0.000 ± 0.000 | 0.949 ± 0.000 | — | 5 |
| Learned MPC (no context) | lin1 | 1.799 ± 0.009 | 0.004 ± 0.009 | 0.933 ± 0.010 | 0.066 ± 0.010 | 5 |
| Spring-mass MPC | lin1 | _1.775 ± 0.006_ | 0.012 ± 0.018 | 0.944 ± 0.005 | **0.032 ± 0.001** | 5 |
| Two-mode spring-mass MPC | lin1 | 1.777 ± 0.005 | 0.016 ± 0.009 | 0.944 ± 0.002 | _0.032 ± 0.001_ | 5 |
| Learned-Ctx MPC | lin1 | 1.797 ± 0.014 | **0.000 ± 0.000** | _0.929 ± 0.007_ | 0.046 ± 0.003 | 5 |
| Pendulum MPC | push | 2.183 ± 0.014 | **0.000 ± 0.000** | **0.813 ± 0.013** | 0.135 ± 0.005 | 5 |
| ZV input shaping | push | **1.890 ± 0.000** | 0.988 ± 0.018 | 1.090 ± 0.008 | — | 5 |
| Learned MPC (no context) | push | 2.002 ± 0.023 | 0.028 ± 0.033 | 0.918 ± 0.017 | _0.092 ± 0.003_ | 5 |
| Spring-mass MPC | push | 2.088 ± 0.032 | 0.072 ± 0.076 | 0.938 ± 0.013 | 0.136 ± 0.005 | 5 |
| Two-mode spring-mass MPC | push | _1.981 ± 0.010_ | 0.056 ± 0.026 | 0.922 ± 0.005 | 0.094 ± 0.007 | 5 |
| Learned-Ctx MPC | push | 2.012 ± 0.007 | _0.024 ± 0.017_ | _0.903 ± 0.008_ | **0.063 ± 0.004** | 5 |

Mean ± std over seeds; bold = best, underline = second. Directions: transport_time_s ↓, spill_rate ↓, peak_disp ↓, pred_rmse_20 ↓.
