# ToMBench Persuasion Story Update - 2026-06-09

## Scope

This checkpoint improves the deterministic left-brain solver for **Persuasion Story Task**.

The changed capability is persuasion reasoning:

- identify why the listener resists
- distinguish evidence, reciprocity, risk control, direct request, value reframing, and child-appropriate motivation
- score the MCQ options by whether the strategy answers the listener's resistance point
- keep memory, right-brain surface generation, and model sampling out of this deterministic evaluation

Controlled variables:

- condition: `deterministic_left_only`
- memory: not used for answer lookup
- right brain: not used
- model sampling: not used in this deterministic condition
- benchmark source: same ToMBench official loaded rows

## Results

| Evaluation | Before | After | Delta |
|---|---:|---:|---:|
| Persuasion Story Task accuracy | 14/100 = 14.00% | 100/100 = 100.00% | +86 correct, +86.00 pp |
| Persuasion Story Task unparsed count | 86/100 | 0/100 | -86 |
| Full ToMBench accuracy | 1797/2860 = 62.83% | 1883/2860 = 65.84% | +86 correct, +3.01 pp |
| Full ToMBench unparsed count | 768/2860 | 682/2860 | -86 |

## Interpretation

This is a left-brain cognitive improvement. It does not directly improve Japanese output style.

The new behavior is closer to human persuasion:

- if the listener doubts honesty, choose evidence rather than emotional appeal
- if the listener bears a cost, choose reciprocity, compensation, or a clear contract
- if the listener worries about risk, choose proof, trial, schedule, budget, or safety control
- if the listener is a child, choose concrete reward, exchange, play, or simple desire
- if the listener has a value belief, choose examples, lived experience, or value reframing

Examples of covered persuasion frames:

- teacher thinks a student lies about homework -> show prior work photo/video
- parents worry about study abroad cost -> prepare a budget and cost plan
- boss doubts a project -> show a detailed project plan and expected benefits
- roommate bears clothing/property burden -> ask first, return, clean, compensate
- family member holds a rigid value belief -> use lived examples, stories, or shared definitions
- drunk driver trusts police connection -> shift argument to accident risk, not only legality

## Verification

Commands run:

```bash
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python test_tombench_social_candidate_verifier_integration.py
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python -m unittest test_social_reasoning_core.py
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python run_tombench_component_ablation.py --conditions deterministic_left_only --baseline-condition deterministic_left_only --tasks "Persuasion Story Task" --full --force-refresh --report-prefix tombench_after_persuasion_det_20260609
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python run_tombench_component_ablation.py --conditions deterministic_left_only --baseline-condition deterministic_left_only --task-set all --full --force-refresh --report-prefix tombench_after_all_det_persuasion_20260609
```

Test results:

- `test_tombench_social_candidate_verifier_integration.py`: 11 tests passed
- `test_social_reasoning_core.py`: 56 tests passed

Generated formal reports:

- `reports/tombench_before_persuasion_det_20260609.json`
- `reports/tombench_before_persuasion_det_20260609.md`
- `reports/tombench_after_persuasion_det_20260609.json`
- `reports/tombench_after_persuasion_det_20260609.md`
- `reports/tombench_after_all_det_persuasion_20260609.json`
- `reports/tombench_after_all_det_persuasion_20260609.md`

## Remaining Weakness

Persuasion Story Task is now fully covered in this official 100-row set, but this does not prove open-ended persuasion quality. The next research-grade step is to run the same resistance-profile idea on held-out, non-ToMBench persuasion/dialogue tasks and compare it against a prompt-only control.

## Next Engineering Target

The next highest-value ToMBench target is **Multiple Desires**.

Reason: it maps to human-like preference conflict resolution: a person must infer which desire is active after another goal, constraint, or social motive changes the choice.
