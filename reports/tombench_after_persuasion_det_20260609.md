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
- deterministic_left_only: correct=100/100, accuracy=1.0, unparsed=0, delta_vs_deterministic_left_only=0.0

## Task Breakdown
### deterministic_left_only
- Persuasion Story Task: correct=100/100, accuracy=1.0, unparsed=0

## Deltas Against Baseline: deterministic_left_only

## Reproduction Command

```bash
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python /Users/jerrychang/Desktop/uruharemake2/run_tombench_component_ablation.py --conditions deterministic_left_only --baseline-condition deterministic_left_only --tasks Persuasion Story Task --full --force-refresh --report-prefix tombench_after_persuasion_det_20260609
```
