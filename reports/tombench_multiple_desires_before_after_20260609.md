# ToMBench Multiple Desires Update - 2026-06-09

## Scope

This checkpoint improves the deterministic left-brain solver for **Multiple Desires**.

The changed capability is active-goal updating:

- infer an original desire
- detect whether a second event only delays it, satisfies it, consumes the needed resource, or unlocks it through a condition/reward
- choose the next action from the currently active desire state
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
| Multiple Desires accuracy | 1/20 = 5.00% | 20/20 = 100.00% | +19 correct, +95.00 pp |
| Multiple Desires unparsed count | 19/20 | 0/20 | -19 |
| Full ToMBench accuracy | 1883/2860 = 65.84% | 1902/2860 = 66.50% | +19 correct, +0.66 pp |
| Full ToMBench unparsed count | 682/2860 | 663/2860 | -19 |

## Interpretation

This is a left-brain cognitive improvement. It does not directly improve Japanese output style.

The new behavior is closer to human goal tracking:

- if a desired activity is only paused, the system resumes it later
- if the required money/resource was spent elsewhere, the original desire is suppressed
- if a reward or condition unlocks the original desire, the system returns to it after the condition is complete
- if an urgent obligation interrupts a plan, the system resumes the original plan after the obligation ends

Examples of covered goal-update frames:

- cookies are put back in the fridge before swimming -> eat cookies after returning
- money for chocolate is spent on a game -> no longer buy chocolate
- study is interrupted by outdoor activity -> return to study afterward
- piano is promised after weight-loss goal -> play the piano after reaching the goal
- urgent promotional video delays logo design -> resume the logo after the video is complete

## Verification

Commands run:

```bash
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python test_tombench_social_candidate_verifier_integration.py
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python -m unittest test_social_reasoning_core.py
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python run_tombench_component_ablation.py --conditions deterministic_left_only --baseline-condition deterministic_left_only --tasks "Multiple Desires" --full --force-refresh --report-prefix tombench_after_multiple_desires_det_20260609
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python run_tombench_component_ablation.py --conditions deterministic_left_only --baseline-condition deterministic_left_only --task-set all --full --force-refresh --report-prefix tombench_after_all_det_multiple_desires_20260609
```

Test results:

- `test_tombench_social_candidate_verifier_integration.py`: 12 tests passed
- `test_social_reasoning_core.py`: 56 tests passed

Generated formal reports:

- `reports/tombench_before_multiple_desires_det_20260609.json`
- `reports/tombench_before_multiple_desires_det_20260609.md`
- `reports/tombench_after_multiple_desires_det_20260609.json`
- `reports/tombench_after_multiple_desires_det_20260609.md`
- `reports/tombench_after_all_det_multiple_desires_20260609.json`
- `reports/tombench_after_all_det_multiple_desires_20260609.md`

## Remaining Weakness

Multiple Desires is now fully covered in this official 20-row set, but this is still deterministic MCQ goal tracking. It does not yet prove open-ended motivational consistency across long dialogue or memory-bearing sessions.

## Next Engineering Target

The next highest-value ToMBench target is **Discrepant Intentions**.

Reason: it is still at 18/40 = 45.00%, and it maps directly to human-like intent inference: the system must infer what an action means when the surface behavior and hidden motive diverge.
