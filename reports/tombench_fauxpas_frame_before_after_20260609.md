# ToMBench Faux-pas Frame Before/After - 2026-06-09

## What changed

This update adds a conservative Faux-pas social-harm frame to the deterministic leftbrain path. It only runs after the existing story-pattern solver and candidate verifier fail to produce an answer, so it fills previously unparsed items instead of overriding already parsed answers.

The added reasoning frame checks whether an utterance is socially inappropriate because it reveals disappointing information, criticizes a person or group connected to the listener, rejects something prepared by the listener, or says something insensitive in the current context. This is an architectural reasoning rule, not a per-item answer table.

## Score Summary

| Scope | Before | After | Delta | Unparsed Before | Unparsed After |
|---|---:|---:|---:|---:|---:|
| Faux-pas Recognition Test | 80/560 (0.1429) | 237/560 (0.4232) | +157 / +28.03 pp | 451 | 173 |
| Full ToMBench 2860 | 1138/2860 (0.3979) | 1295/2860 (0.4528) | +157 / +5.49 pp | 1600 | 1322 |

## Selection Mode Impact

| Mode | Count |
|---|---:|
| tombench_p2_general_v1_fauxpas_frame | 278 |

## Interpretation

This is a real leftbrain improvement because the system now performs a reusable pragmatic check: it identifies when a sentence is inappropriate relative to the listener's knowledge, emotional stake, and social relationship. It does not improve the rightbrain surface wording yet; it improves the inner social reasoning layer used for ToMBench-style tasks.

The remaining weak areas after this run are Ambiguous Story Task, Strange Story Task, Hinting Task Test, Persuasion Story Task, Multiple Desires, and Unexpected Outcome Test. Those need separate reasoning modules; forcing Faux-pas rules into those tasks would be overfitting.

## Verification

- `python test_tombench_social_candidate_verifier_integration.py`: 6 tests passed.
- `python -m unittest test_social_reasoning_core.py`: 56 tests passed.
- `run_tombench_component_ablation.py --tasks "Faux-pas Recognition Test" --full`: 237/560.
- `run_tombench_component_ablation.py --task-set all --full`: 1295/2860.
