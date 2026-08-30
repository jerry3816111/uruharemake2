# M35 Same-Model Longitudinal Pragmatic Comparison — Frozen Result

Date: 2026-08-25  
Decision: **FAIL — seven frozen gates failed**

## Question

Under the same `qwen3.5:9b`, current input, public-Uruha expression prompt, temperature, seed, output budget, machine, and paired prompt-token gate, does adding the M34 verified longitudinal branch packet improve desired-response selection over current-turn-only direct generation?

This is an information-path comparison. It is not a model-architecture comparison: baseline intentionally cannot read verified history, while system receives only the typed M34 output computed from that history.

## Frozen design

- 12 isolated cases, 6 counterfactual pairs, Chinese/English/Japanese 4 cases each.
- Within every pair the current utterance is byte-identical; only the previously requested and supported response form differs.
- Both conditions use the same local model and expression contract.
- Two fixed real-token preflight rounds per condition and stage; scored prompt-token delta must be at most 2.
- Dataset SHA-256: `5ab3fcd8a1dbbe0b5a036499e8cd1425b1812620076b61007a1e1359cf0b299f`.
- Protocol SHA-256: `a89288889f914f7494d020fe64d45eae5d4d5be5b6c929e68a147e4439c1ec67`.
- Implementation freeze SHA-256: `ba299284eff32c22d6cc0af51700efb71362d0bbb3429c688eaf89ef1f7f5f29`.
- Raw result SHA-256: `8e7bfb0a93e44e9116753b5abbcc30ffdfe87bd7be78396f7b5ba860b6e1a948`.

## Frozen result

| Measure | Baseline | System | Difference / result |
|---|---:|---:|---:|
| Current desired-response policy accuracy | 25.0% | 75.0% | **+50.0pp** |
| Pair behavior | 100% invariant | 83.33% divergent | one system pair failed to diverge |
| Current surface proxy match | 0.0% | 58.33% | +58.33pp, below 75% gate |
| Visible Japanese, current + feedback | 100% | 100% | tie |
| Scored prompt tokens | 20,040 | 20,040 | exact parity |
| Completion tokens | 450 | 464 | system 1.0311x |
| Scored latency | 24.2748s | 24.5850s | system 1.0128x |

Mechanism-only checks were also below gate:

- M34 current-policy accuracy: 75.0% rather than 100%.
- M34 next-turn outcome verification: 66.67% rather than 100%.
- System contradiction-revision gate: 20% under the frozen labels and mechanism trace.
- No transport or JSON parse errors; every paired real-token gate passed.
- Unverified mental-fact writes and raw adaptive-ledger persistence: 0.

The evaluation made 48 scored model calls and 96 fixed preflight calls. Scored calls used 40,080 prompt tokens and 914 completion tokens in total; preflight calls processed 76,140 prompt tokens and discarded their one-token outputs.

## Safari presentation evidence

`analysis/m35_safari_same_model_frozen_result_2026-08-25.jpeg` shows the immutable M35 comparison inside the real local Web UI. The card deliberately presents the usable current-turn observation (baseline 25%, longitudinal system 75%, +50pp, 83% pair divergence) beside the red `FROZEN GATE · FAIL` decision, cost ratios, seven failed gates, and the frozen feedback-label warning. It is a visualization of the recorded experiment, not a replacement run or a corrected score.

## Concrete controlled contrast

For the byte-identical Chinese current input `凌晨了，腦袋還是一直轉個不停。`:

| Verified history condition | Current-turn-only baseline | M34 longitudinal system |
|---|---|---|
| user previously confirmed “tease me” | `うん、夜中って頭が冴えてくるよね` (`listen_presence`) | `頭が止まらなくて困るのかよ` (`playful_tease`) |
| user previously confirmed “tell me what to do” | same baseline reply (`listen_presence`) | `深呼吸してみようか？` (`solve_regulation`) |

This is the strongest valid M35 result: with identical current wording and exact scored-token parity, the baseline stayed invariant while the longitudinal system produced two distinct, history-consistent branches.

## Why the full gate failed

1. **Cross-lingual signal coverage remains brittle.** English `My thoughts keep racing even though it's late.` did not reuse the verified solve policy, although the paired companionship condition worked. Japanese `今夜は頭がずっと止まらない。` failed to activate either verified branch because the adverb interrupted the current literal cue pattern.
2. **Feedback linkage remains phrase-sensitive.** English corrections such as `No, give me one concrete step this time.` and `No, I want you to hear me out, no advice.` produced the correct visible direct response but M34 did not link them as a contradiction to the previous prediction.
3. **Correct policy declaration does not guarantee felt surface execution.** Several listening cases selected `listen_presence` but only paraphrased the situation instead of clearly inviting the user to continue.
4. **Frozen feedback-label audit found two annotation errors.** A pre-freeze mechanical edit incorrectly changed two contradiction targets to `not_applicable`; two support/unknown rows also retained non-comparable policy labels. Therefore the formal `system_feedback_policy_accuracy=60%` is not usable evidence. The raw file and failed decision remain immutable; no corrected M35 score is substituted after seeing outputs.

## What may and may not be claimed

M35 supports a narrow controlled observation: on this frozen set, the longitudinal condition improved current branch accuracy by 50 percentage points at exact scored prompt-token parity and about 1.3% latency overhead.

M35 does **not** establish a completed same-model advantage milestone because the mechanism, pair-divergence, surface, and correction gates failed. It also provides no human felt-understanding preference, private-intent truth, general LLM superiority, or human-brain-equation evidence.

## Next milestone

M36 must be a new, non-overwriting milestone with:

- compositional multilingual response-form and arousal normalization rather than adding exact sentence templates;
- explicit-target feedback linkage that treats sentence-initial `No`／`違う` as a contradiction only when a valid replacement policy is present;
- a programmatic annotation-consistency validator before sealing;
- a new source-disjoint reserve and a separate surface-realization diagnostic.
