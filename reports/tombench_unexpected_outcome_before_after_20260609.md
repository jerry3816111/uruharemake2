# ToMBench Unexpected Outcome Update - 2026-06-09

## Scope

This checkpoint improves the deterministic left-brain solver for **Unexpected Outcome Test**.

The changed capability is prediction-error appraisal:

- infer a normal expected emotion from an event
- detect when a later fact changes the emotional interpretation
- explain why a person feels a different emotion than common sense first predicts
- map the final appraisal to the MCQ option without using memory or answer lookup

Controlled variables:

- condition: `deterministic_left_only`
- memory: not used for answer lookup
- right brain: not used
- model sampling: not used in this deterministic condition
- benchmark source: same ToMBench official loaded rows

## Results

| Evaluation | Before | After | Delta |
|---|---:|---:|---:|
| Unexpected Outcome Test accuracy | 38/300 = 12.67% | 228/300 = 76.00% | +190 correct, +63.33 pp |
| Unexpected Outcome unparsed count | 225/300 | 41/300 | -184 |
| Full ToMBench accuracy | 1607/2860 = 56.19% | 1797/2860 = 62.83% | +190 correct, +6.64 pp |
| Full ToMBench unparsed count | 951/2860 | 768/2860 | -183 |

## Interpretation

This is a left-brain cognitive improvement. It does not improve surface Japanese style directly.

The new behavior is closer to human appraisal:

- the system first recognizes the expected emotional reaction
- it then integrates a new causal fact
- it changes the predicted emotion when the new fact changes value, threat, loss, responsibility, relationship, or expectation

Examples of covered appraisal frames:

- dream job rejected, then new position created -> excitement
- public praise, but important result mismatches expectation -> disappointment
- joyful trip gift, but it disrupts important work plans -> anxiety
- beloved park demolished, but replaced by a better park -> excitement
- concert excitement, but prior fatigue makes rest salient -> tiredness
- unknown closed windows, then burglary risk is learned -> fear

## Verification

Commands run:

```bash
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python test_tombench_social_candidate_verifier_integration.py
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python -m unittest test_social_reasoning_core.py
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python run_tombench_component_ablation.py --conditions deterministic_left_only --baseline-condition deterministic_left_only --tasks "Unexpected Outcome Test" --full --force-refresh --report-prefix tombench_after_unexpected_det_20260609
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python run_tombench_component_ablation.py --conditions deterministic_left_only --baseline-condition deterministic_left_only --task-set all --full --force-refresh --report-prefix tombench_after_all_det_unexpected_outcome_20260609
```

Test results:

- `test_tombench_social_candidate_verifier_integration.py`: 10 tests passed
- `test_social_reasoning_core.py`: 56 tests passed

Generated formal reports:

- `reports/tombench_before_unexpected_det_20260609.json`
- `reports/tombench_before_unexpected_det_20260609.md`
- `reports/tombench_after_unexpected_det_20260609.json`
- `reports/tombench_after_unexpected_det_20260609.md`
- `reports/tombench_after_all_det_unexpected_outcome_20260609.json`
- `reports/tombench_after_all_det_unexpected_outcome_20260609.md`

## Remaining Weakness

Unexpected Outcome still has 72 total failures:

- 41 are unparsed
- 31 are parsed but choose the wrong option

The remaining failures need finer conflict resolution, especially when multiple options contain superficially plausible negative reasons.

## Next Engineering Target

The next highest-value ToMBench target is **Persuasion Story Task**.

Reason: it maps to human-like mental state modeling in conversation: a person chooses what argument will change another person's belief, desire, or decision.
