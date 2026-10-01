# M27 Causal Outcome Calibration Ledger and Evidence-Count Guard

Status date: 2026-08-25  
Scope: bounded product mechanism and isolated Safari validation  
Claim boundary: privacy-safe online outcome accounting; not external human calibration

## 1. Problem closed

M26 exposed a normalized operational belief such as `p=0.44`, but the number had no empirical sample history. M27 prevents that engineering score from quietly becoming a calibration claim.

```text
M26 prediction / abstention
→ privacy-safe pending ledger entry
→ next-turn causal-link check
→ supported / contradicted OR unknown excluded
→ effective sample count, coverage, selective risk, descriptive Brier bins
→ minimum-evidence guard
→ no automatic threshold tuning
```

## 2. Runtime implementation

- The adaptive-person store is upgraded to version 4 and keeps at most 120 M27 ledger entries.
- Each entry contains a prediction ID, turn number, input digest, categorical scope, implicit top policy/mode, performed policy, M26 action, probability, margin, evidence quality, and linked outcome.
- No raw utterance or reply is written into the ledger.
- Only `supported` or `contradicted` outcomes with `feedback_linked_to_previous_prediction=true` enter the effective sample.
- `uncertain`, unrelated new requests, topic shifts, missing feedback, and M25 explicit-authority bypasses do not increase implicit success.
- The minimum descriptive gate is eight decisive executed samples. Even after that gate, the status is only `descriptive_online_evidence_only`; automatic threshold tuning remains disabled and external calibration remains unestablished without a fresh holdout.
- M27 adds `causal_outcome_resolution_m27` and `causal_outcome_calibration_ledger_m27` nodes to the actual runtime graph. The pre-M27 blackboard window was enlarged by exactly two nodes so older personhood evidence was not evicted.

## 3. Automated evidence

- M27-specific tests: **6 passed**.
- Focused V2.12 + Japanese/identity/proactive + observatory + M16–M27 compatibility: **204 passed, 3 warnings** in 6.91 seconds.
- Covered contracts: linked support counts; unrelated next turn is excluded; explicit bypass is excluded; n=8 only enables offline descriptive review; persistence is bounded and raw-free; real runtime/graph/compact payload carries M27.

One retained implementation failure was found and repaired: `對就是這樣` was recognized, but natural punctuation in `對，就是這樣。` initially broke the support detector. The typed support cue now accepts the punctuated form, and the real Safari run verifies it.

## 4. Isolated Safari six-turn acceptance

Runtime isolation:

- page: `http://127.0.0.1:7868/?m27final=1`
- session: `20260825_122512_97c5ba0c`
- log: `/tmp/uruha-m27-safari.ZcCGaK/web.jsonl`
- adaptive state: `/tmp/uruha-m27-safari.ZcCGaK/adaptive.json`
- production DB was not used or modified.

| Turn | Input role | M26 action / previous outcome | M27 result after turn |
|---|---|---|---|
| 1 | ambiguous arousal | abstain; no previous outcome | effective n=0; abstention pending |
| 2 | explicit correction to practical help | explicit bypass; prior abstention contradicted and causally linked | decisive abstention=1; executed n remains 0 |
| 3 | repeated ambiguous arousal | execute implicit practical help; prior explicit-bypass outcome unknown | one executed prediction pending; coverage=0.50 |
| 4 | `對，就是這樣。` | no new implicit action; prior execution supported and causally linked | **effective executed n=1**, selective risk=0.00 |
| 5 | repeated arousal again | execute implicit practical help | second executed prediction pending; coverage=0.6667 |
| 6 | unrelated weather statement | no new implicit action; prior execution uncertain/unlinked | effective n stays **1**; unknown/unlinked becomes **1** |

The persisted store contains four ledger entries: abstention→contradicted, explicit bypass→uncertain/excluded, execution→supported, execution→uncertain/excluded. All raw-dialogue flags are false, and none of the six input strings occurs in the serialized ledger.

Visual evidence:

- `analysis/m27_safari_causal_support_effective_sample_2026-08-25.png`
- `analysis/m27_safari_unknown_excluded_2026-08-25.png`
- `analysis/m27_safari_causal_calibration_graph_2026-08-25.png`
- `analysis/m27_safari_calibration_ledger_node_detail_2026-08-25.png`

## 5. Honest completion boundary

M27 establishes that UruhaBrain can account for whether its implicit response choices receive causally linked support or contradiction without counting unknown outcomes as wins. It does not establish that the probabilities are calibrated for a population, that eight online samples are sufficient for deployment, or that UruhaBrain is preferred by humans.

The minimum count of eight is an engineering review guard, not a research-derived universal constant. A fresh source-disjoint holdout and human evaluation are still required for external calibration claims.

## 6. Retained product failures and M28

The M27 ledger was correct while two visible surfaces were not:

1. After the user confirmed `對，就是這樣。`, the visible reply reopened a listening-vs-solving clarification instead of simply acknowledging the support.
2. After an unrelated weather statement, the visible reply said it did not want to pretend understanding and asked for one more detail, showing that stale uncertainty could still hijack a topic shift.

Therefore the next necessary product milestone is **M28 Feedback Acknowledgement and Topic-Shift Surface Continuity**: make decisive support yield a short acknowledgement, make unrelated new content start a clean current-turn response, prevent stale desired-response uncertainty from becoming the surface act, and retain the M27 ledger outcome unchanged.
