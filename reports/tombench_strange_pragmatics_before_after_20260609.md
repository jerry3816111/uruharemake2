# ToMBench Strange Story Pragmatics Before/After - 2026-06-09

## What changed

This update adds a Strange Story pragmatic-profile solver to the deterministic leftbrain path. It is only used after the existing story-pattern solver and candidate verifier fail, so it fills previously unparsed items rather than replacing earlier answers.

The new profile recognizes reusable non-literal communication types: sarcasm, forgetfulness / false belief, white lies or politeness, jokes, roleplay, metaphor, mixed emotion, self-protective lies, strategic deception, and inverse deception where a listener distrusts a known liar or captive.

## Score Summary

| Scope | Before | After | Delta | Unparsed Before | Unparsed After |
|---|---:|---:|---:|---:|---:|
| Strange Story Task | 52/407 (0.1278) | 172/407 (0.4226) | +120 / +29.48 pp | 346 | 196 |
| Full ToMBench 2860 | 1295/2860 (0.4528) | 1415/2860 (0.4948) | +120 / +4.20 pp | 1322 | 1172 |

## Selection Mode Impact

| Mode | Count |
|---|---:|
| tombench_p2_general_v1_strange_story_pragmatics | 150 |

## Interpretation

This is a leftbrain improvement, not a surface-language or prompt-only improvement. The system now maps a story to a pragmatic intent type before selecting an answer. This directly supports the project goal of modeling the cognitive step between hearing an utterance and deciding what the utterance really means.

The solver still leaves 196 Strange Story rows unparsed. The next likely gains are in Hinting Task, Ambiguous Story, and Persuasion Story, because those require adjacent pragmatic skills: indirect requests, ambiguous intent disambiguation, and motive-based persuasion.

## Verification

- `python test_tombench_social_candidate_verifier_integration.py`: 7 tests passed.
- `python -m unittest test_social_reasoning_core.py`: 56 tests passed.
- `run_tombench_component_ablation.py --tasks "Strange Story Task" --full`: 172/407.
- `run_tombench_component_ablation.py --task-set all --full`: 1415/2860.
