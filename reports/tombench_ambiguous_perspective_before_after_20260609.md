# ToMBench Ambiguous Perspective Update - 2026-06-09

## Scope

This checkpoint improves the deterministic left-brain solver for **Ambiguous Story Task**.

The changed capability is social ambiguity resolution:

- infer the actor's hidden intention from an ambiguous gesture or indirect action
- separate the actor's private plan from an observer's limited knowledge
- score social frames such as inclusion, exclusion, surprise planning, care, conflict repair, romance, status pressure, and planning/recommendation

Controlled variables:

- condition: `deterministic_left_only`
- memory: not used for answer lookup
- right brain: not used
- model sampling: not used in this deterministic condition
- benchmark source: same ToMBench official loaded rows

## Results

| Evaluation | Before | After | Delta |
|---|---:|---:|---:|
| Ambiguous Story Task accuracy | 3/200 = 1.50% | 105/200 = 52.50% | +102 correct, +51.00 pp |
| Ambiguous unparsed count | 197/200 | 66/200 | -131 |
| Full ToMBench accuracy | 1505/2860 = 52.62% | 1607/2860 = 56.19% | +102 correct, +3.57 pp |
| Full ToMBench unparsed count | 1082/2860 | 951/2860 | -131 |

## Interpretation

The improvement is concentrated in Ambiguous Story Task. That is expected because the new solver is only wired for that task.

This is a left-brain improvement, not a right-brain surface-style improvement. It makes the system better at deciding what an ambiguous social action means before any Japanese natural-language response is generated.

The remaining Ambiguous errors are mostly:

- still-uncovered story frames
- low-confidence ties between options
- observer questions where the correct option requires finer access-state modeling
- options where lexical overlap is misleading

## Verification

Commands run:

```bash
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python test_tombench_social_candidate_verifier_integration.py
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python -m unittest test_social_reasoning_core.py
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python run_tombench_component_ablation.py --conditions deterministic_left_only --baseline-condition deterministic_left_only --tasks "Ambiguous Story Task" --full --force-refresh --report-prefix tombench_after_ambiguous_det_20260609
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python run_tombench_component_ablation.py --conditions deterministic_left_only --baseline-condition deterministic_left_only --task-set all --full --force-refresh --report-prefix tombench_after_all_det_ambiguous_perspective_20260609
```

Test results:

- `test_tombench_social_candidate_verifier_integration.py`: 9 tests passed
- `test_social_reasoning_core.py`: 56 tests passed

Generated formal reports:

- `reports/tombench_before_ambiguous_det_20260609.json`
- `reports/tombench_before_ambiguous_det_20260609.md`
- `reports/tombench_after_ambiguous_det_20260609.json`
- `reports/tombench_after_ambiguous_det_20260609.md`
- `reports/tombench_after_all_det_ambiguous_perspective_20260609.json`
- `reports/tombench_after_all_det_ambiguous_perspective_20260609.md`

## Next Engineering Target

The next highest-value ToMBench target is one of:

- **Unexpected Outcome Test**: currently 38/300 = 12.67%, mostly unparsed.
- **Persuasion Story Task**: currently 14/100 = 14.00%, mostly unparsed.
- **Multiple Desires**: currently 1/20 = 5.00%, almost entirely unparsed.

For project value, the best next target is **Unexpected Outcome Test**, because it maps directly to human-like expectation updating: a person predicts an outcome, observes mismatch, then explains the emotion caused by that prediction error.
