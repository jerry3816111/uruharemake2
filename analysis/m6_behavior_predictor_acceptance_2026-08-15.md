# M6 Behavior Predictor — Frozen First-Generation Acceptance

Date: 2026-08-15 (JST)

## Outcome

M6 completes the required pre-language behavior pipeline on a bounded, author-designed synthetic overlay:

`transitioned state + event + memories + person parameters → logits → probabilities → temperature calibration → behavior selection`

All engineering gates pass. The preregistered narrow synthetic lift hypothesis also passes, but this is not a fresh or real-person result. The raw artifact deliberately retains the one Ours Top-1 failure and the risk of overconfidence from tiny-dev temperature selection.

## Frozen information boundary

- 32 cutoff-before history records: 24 train rows plus 8 dev rows.
- 8 future holdout events, one per M5 scenario.
- 256 history references checked; future leakage = 0.
- Same local foundation model, `qwen3.5:9b`, for B1–B5 and M5's inherited Ours feature extractor.
- B0–B5 receive the same 32 authorized historical events under their defined information conditions.
- Ours uses the frozen M5 T3 event features and transitioned states; it does not call an LLM again in M6.
- No condition generates an utterance.

## Actual holdout comparison

| Condition | Top-1 ↑ | Top-3 ↑ | Macro F1 ↑ | Brier ↓ | NLL ↓ | ECE ↓ |
|---|---:|---:|---:|---:|---:|---:|
| B0 prior | 25.0% | 62.5% | 0.067 | 0.813 | 1.734 | 0.013 |
| B1 base LLM | 50.0% | 62.5% | 0.317 | 0.740 | 1.518 | 0.305 |
| B2 persona prompt | **87.5%** | 87.5% | **0.911** | 0.381 | 0.928 | 0.274 |
| B3 RAG | 75.0% | 75.0% | 0.806 | 0.441 | 1.034 | 0.182 |
| B4 full-history summary | **87.5%** | 87.5% | **0.911** | 0.504 | 1.041 | 0.467 |
| B5 structured history | 75.0% | **100%** | 0.689 | **0.347** | **0.695** | 0.166 |
| Ours hybrid | **87.5%** | **100%** | 0.800 | **0.151** | **0.194** | **0.104** |

The preregistered lift rule required Ours Top-1 to be at least the best B0–B5 while strictly improving the best B0–B5 Brier and NLL. All three checks pass. The evidence is still narrow because the overlay and mappings are synthetic and known during construction.

## Calibration mechanism

- Selected L2 alpha: 0.0, by lowest dev NLL.
- Selected temperature: 0.5, by lowest dev NLL from the frozen grid.
- Dev NLL changes from 0.0323 at temperature 1.0 to 0.00135 at temperature 0.5.
- Holdout ECE is 0.104, lower than every LLM baseline in this run except the uninformative B0 prior.

The very low dev NLL and temperature below 1.0 increase confidence. With only eight synthetic dev rows this may overfit; it is a mechanism check, not evidence of general calibration.

## Preserved failure

For `quiet_success::holdout`, the true synthetic behavior is `acknowledge_then_continue`. Ours instead assigns 0.775 to `direct_rejection` and 0.225 to the correct label. B2, B3, B4, and B5 classify this row correctly. This failure is visible in the graphical lab and must guide M7 intervention analysis rather than being removed by post-hoc retuning.

## Direct explanation evidence

Every Ours row stores the exact linear contribution of every transitioned-state, event, memory-signal, and person-parameter feature to every behavior logit. The displayed explanation ranks those actual contributions; no second LLM creates a plausible-sounding rationale after prediction.

## Resource accounting

Fresh B0–B5 execution:

- 41 calls: one B4 summary plus 40 prediction calls.
- 40,136 prompt tokens + 5,376 completion tokens = 45,512 tokens.
- 426.77 seconds accumulated local model latency.
- B5 alone: 20,474 prompt tokens and 131.05 seconds for eight predictions.

Ours inclusive accounting:

- 40 inherited M5 feature calls.
- 6,121 prompt tokens + 2,493 completion tokens = 8,614 tokens.
- 178.76 seconds inherited feature latency.
- 4.55 seconds M6 numeric fitting, calibration, and prediction.
- 0 incremental M6 model calls.

These costs are not perfectly token-parity because each method has a different computation graph; they are reported rather than normalized away.

## Verification and boundary

- M6 core/runner tests before frozen-result tests: 6/6 pass.
- Frozen M6 result tests add four checks for hash, calls, preserved failure, and no language realization.
- Formal Uruha data gate remains blocked.
- This result does not establish human private-state validity, Uruha prediction, unseen semantic generalization, causal importance of the state features, rolling-cutoff stability, second-person transfer, or human preference.

Raw result: `analysis/m6_behavior_predictor_synthetic_first_generation_raw.json`  
Result SHA-256: `b042011646c16b7fd565f39ed8acab621cbd16fb2a9e910a0e776e5829ea20b4`

The next dependency is M7: use frozen component ablations and probability-level interventions to test whether the claimed transitioned-state, event, memory, and person features actually change behavior probabilities, including an analysis of the `quiet_success` failure.
