# ToMBench Discrepant Intentions Update - 2026-06-09

## Scope

This checkpoint improves the deterministic left-brain solver for **Discrepant Intentions**.

The changed capability is hidden-motive attribution:

- separate the surface behavior from the actor's actual intention
- distinguish innocent false-belief actions from informed silence
- infer whether silence is driven by prejudice, competition, revenge, sympathy, protection, or not spoiling another person's experience
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
| Discrepant Intentions accuracy | 18/40 = 45.00% | 40/40 = 100.00% | +22 correct, +55.00 pp |
| Discrepant Intentions unparsed count | 22/40 | 0/40 | -22 |
| Full ToMBench accuracy | 1902/2860 = 66.50% | 1924/2860 = 67.27% | +22 correct, +0.77 pp |
| Full ToMBench unparsed count | 663/2860 | 641/2860 | -22 |

## Interpretation

This is a left-brain cognitive improvement. It does not directly improve Japanese output style.

The new behavior is closer to human intention attribution:

- if the target actor lacks knowledge, the system attributes the behavior to false belief or ignorance
- if the target actor is aware but stays silent, the system searches for the social motive behind silence
- if the story contains competition, grudge, prejudice, sympathy, or protection, the system maps that motive to the option
- existing candidate verifier remains first; the new hidden-motive profiler only fills cases the verifier cannot resolve

Examples of covered intention frames:

- an assistant throws away artwork because he thinks it was abandoned -> innocent false belief
- a person sees a mistake but stays silent because of jealousy -> strategic silence
- a witness with a private grudge does not intervene -> revenge motive
- a friend hides a rule because they do not want to spoil another friend's fun -> prosocial silence
- a sibling does not report a toddler because they do not want the toddler scolded -> protective silence
- a bystander tolerates an improper action out of sympathy -> compassionate silence

## Verification

Commands run:

```bash
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python test_tombench_social_candidate_verifier_integration.py
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python -m unittest test_social_reasoning_core.py
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python run_tombench_component_ablation.py --conditions deterministic_left_only --baseline-condition deterministic_left_only --tasks "Discrepant Intentions" --full --force-refresh --report-prefix tombench_after_discrepant_intentions_det_20260609
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python run_tombench_component_ablation.py --conditions deterministic_left_only --baseline-condition deterministic_left_only --task-set all --full --force-refresh --report-prefix tombench_after_all_det_discrepant_intentions_20260609
```

Test results:

- `test_tombench_social_candidate_verifier_integration.py`: 13 tests passed
- `test_social_reasoning_core.py`: 56 tests passed

Generated formal reports:

- `reports/tombench_before_discrepant_intentions_det_20260609.json`
- `reports/tombench_before_discrepant_intentions_det_20260609.md`
- `reports/tombench_after_discrepant_intentions_det_20260609.json`
- `reports/tombench_after_discrepant_intentions_det_20260609.md`
- `reports/tombench_after_all_det_discrepant_intentions_20260609.json`
- `reports/tombench_after_all_det_discrepant_intentions_20260609.md`

## Remaining Weakness

Discrepant Intentions is now fully covered in this official 40-row set, but this is still deterministic MCQ attribution. It does not yet prove open-ended intent inference in free dialogue or memory-bearing conversations.

## Next Engineering Target

The next highest-value ToMBench target is **Faux-pas Recognition Test**.

Reason: it has 560 rows, remains at 237/560 = 42.32%, and maps directly to human-like social norm inference: the system must detect when a true statement still causes social harm because the speaker failed to model the listener's knowledge or feelings.
