# ToMBench Component Ablation

This is a research ablation report. It changes one cognitive component condition at a time while holding the benchmark, model, scoring, and memory policy fixed.

## Variables

### Independent / Operated Variables
- deterministic_left_only: left-brain deterministic solver only
  - Uses deterministic social-reasoning solver only. Uncovered rows are counted incorrect, so this measures rule coverage and precision without LLM fallback.

### Controlled Variables
- benchmark: official ToMBench rows loaded by run_formal_brain_benchmarks_v2.load_tombench_items(full=True)
- model: qwen2.5:7b through the same local OpenAI-compatible endpoint for LLM conditions
- temperature: 0.0
- scoring: exact match against official A/B/C/D answer key
- memory: disabled for all ToMBench ablation conditions; no profile, episodes, recent_dialogue, or working_memory_items are passed
- right_brain: not used for MCQ scoring because ToMBench only accepts option letters
- cache_policy: condition-specific checkpoints; use --force-refresh for strict no-cache reruns

### Dependent Variables
- accuracy
- correct_count
- unparsed_count
- task_breakdown accuracy
- delta_vs_baseline_full_cognitive_system
- only_condition_correct / only_baseline_correct against baseline
- selection_mode_breakdown

## Important Scope Note

ToMBench can evaluate social understanding, belief/intent inference, process traces, and candidate self-checking. It cannot directly evaluate right-brain Japanese surface naturalness because the dependent variable is only an A/B/C/D option letter. Therefore right_brain_surface is marked not_applicable_mcq rather than falsely treated as proven by this benchmark.

## Summary
- deterministic_left_only: correct=1797/2860, accuracy=0.6283, unparsed=768, delta_vs_deterministic_left_only=0.0

## Task Breakdown
### deterministic_left_only
- Ambiguous Story Task: correct=105/200, accuracy=0.525, unparsed=66
- Completion of Failed Actions: correct=17/20, accuracy=0.85, unparsed=3
- Discrepant Desires: correct=17/20, accuracy=0.85, unparsed=3
- Discrepant Emotions: correct=40/40, accuracy=1.0, unparsed=0
- Discrepant Intentions: correct=18/40, accuracy=0.45, unparsed=22
- Emotion Regulation: correct=17/20, accuracy=0.85, unparsed=3
- False Belief Task: correct=600/600, accuracy=1.0, unparsed=0
- Faux-pas Recognition Test: correct=237/560, accuracy=0.4232, unparsed=173
- Hidden Emotions: correct=35/80, accuracy=0.4375, unparsed=35
- Hinting Task Test: correct=103/103, accuracy=1.0, unparsed=0
- Knowledge-Attention Links: correct=20/20, accuracy=1.0, unparsed=0
- Knowledge-Pretend Play Links: correct=26/30, accuracy=0.8667, unparsed=0
- Moral Emotions: correct=21/40, accuracy=0.525, unparsed=4
- Multiple Desires: correct=1/20, accuracy=0.05, unparsed=19
- Percepts-Knowledge Links: correct=40/40, accuracy=1.0, unparsed=0
- Persuasion Story Task: correct=14/100, accuracy=0.14, unparsed=86
- Prediction of Actions: correct=14/20, accuracy=0.7, unparsed=6
- Scalar Implicature Test: correct=72/200, accuracy=0.36, unparsed=111
- Strange Story Task: correct=172/407, accuracy=0.4226, unparsed=196
- Unexpected Outcome Test: correct=228/300, accuracy=0.76, unparsed=41

## Deltas Against Baseline: deterministic_left_only

## Reproduction Command

```bash
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python /Users/jerrychang/Desktop/uruharemake2/run_tombench_component_ablation.py --conditions deterministic_left_only --baseline-condition deterministic_left_only --task-set all --full --force-refresh --report-prefix tombench_after_all_det_unexpected_outcome_20260609
```
