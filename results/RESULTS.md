# Results

All numbers are from `results/runs.jsonl` (tables in `results/tables/`, statistics from `rh compare`).
Main table: 5 seeds x 50 test episodes; ablations and sweeps: 3 seeds x 50 episodes. Total experiment
wall-clock about 39 minutes on 2 CPU threads.

## Tuned settings (validation rule, nominal task)
Learned-Ctx 0.90, Learned no-context 0.90, Pendulum 0.70, Spring-mass 0.80, Two-mode spring-mass 0.85,
ZV shaping peak acceleration 1.4 m/s^2, Oracle 1.0. lin1: 0.95 / 0.95 / 0.95 / 1.0 / 1.0 / 1.9.

## H1 (nominal: learned faster than pendulum, spill-free): SUPPORTED, with qualifications
| System | transport time [s] | spill rate |
|---|---|---|
| ZV input shaping | 1.890 +- 0.000 | 0 |
| Two-mode spring-mass MPC | 1.965 +- 0.007 | 0 |
| Learned MPC (no context) | 1.987 +- 0.018 | 0 |
| Learned-Ctx MPC | 1.993 +- 0.010 | 0 |
| Spring-mass MPC | 2.041 +- 0.014 | 0 |
| Pendulum MPC | 2.147 +- 0.012 | 0 |
| Oracle MPC (privileged reference) | 1.916 +- 0.008 | 0.008 |

Learned-Ctx vs Pendulum: -0.154 s (-7.2%), Welch p = 2.4e-8, per-seed ranges disjoint. But: the pendulum got a
smaller margin than the equally accurate spring-mass model from the grid rule (one validation spill at 0.8);
against spring-mass the gain is 2.3%. The learned model is not the fastest: two-mode spring-mass is 0.028 s
faster (p = 0.001) and ZV shaping 0.103 s faster. ZV shaping also beats the oracle MPC, so the sampling optimiser
is not time-optimal.

## H2 (held-out + push: learned with encoder spills less at equal time): SUPPORTED at equal time only
At tuned margins (main, heldout_push): Learned-Ctx 2.024 s / 12.0% spills; Pendulum 2.270 s / 0.8% spills
(pendulum spills less, p = 7e-4, and is 0.25 s slower). Equal-margin sweep (sweep_margin_hp, 3 seeds): at margin
0.8 Learned-Ctx 2.129 s / 0.7%, Pendulum 2.128 s / 18.0%; pendulum reaches 0.7% only at 2.271 s (margin 0.7).
No-context: 2.164 s / 3.3% at margin 0.8. ZV shaping: 97% spills; two-mode spring-mass: 29%.

Nominal liquid + push (main, task push): Learned-Ctx 2.012 s / 2.4%; Pendulum 2.183 s / 0%; two-mode 1.981 s /
5.6%; ZV shaping 98.8% spills.

## H3 (single linear mode: learned advantage vanishes): SUPPORTED
lin1: Learned-Ctx 1.797 +- 0.014 s, Pendulum 1.806 +- 0.005 s, Welch p = 0.23, no spills for either. Fitted
models have lower 20-step RMSE (0.033 vs 0.046). ZV shaping 1.650 s (at the top of its grid).

## H4 (sensor set matters; F/T is the best single addition): FIRST PART SUPPORTED, SECOND NOT SUPPORTED
abl_sensor (heldout_push, 3 seeds), spill rate: cart only 67%, + camera proxy 25%, + force/torque 15%,
+ probe 12%. Cart-only vs probe p = 0.026; F/T vs probe p = 0.55 (indistinguishable); probe has the lowest mean.
Noise levels were not swept, so "per unit noise" is untested.

## Other ablations (heldout_push, 3 seeds)
- History: K=0 2.241 s / 16% / RMSE20 0.373; K=10 2.030 s / 11% / 0.238; K=30 2.026 s / 12% / 0.172.
- Data: 1k 50% spills; 10k 17%; 50k 12% (10k vs 50k not significant).
- MPC: horizon 15 1.963 s, horizon 45 2.171 s, 32 samples 2.158 s, 128 samples 1.992 s, default 2.026 s;
  spill rates 9-12%, not distinguishable. The optimiser moves time as much as the model choice does.
- Push sweep (nominal liquid): ZV shaping 75% spills at 0.02 m/s; at 0.08 m/s Learned-Ctx 23%, two-mode 29%,
  pendulum 11%.

## Verdict
`rh verdict`: target tier not reached; the method is not the best system on the primary task (ZV input shaping
is faster on the nominal liquid). The outcome is mixed, and is reported as such.
