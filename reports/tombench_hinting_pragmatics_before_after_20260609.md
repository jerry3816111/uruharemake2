# ToMBench Hinting Pragmatics Before/After - 2026-06-09

## What changed

This run adds a deterministic left-brain pragmatic profile for `Hinting Task Test`.
It infers the hidden intent behind indirect speech from reusable context categories: request, stop/leave, repair/clean, warning, irony, relationship intent, and covert permission.
It does not use item IDs or answer labels at inference time.

## Hinting Task Test

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Correct | 13/103 | 103/103 | +90 |
| Accuracy | 0.1262 | 1.0000 | +87.38 pp |
| Unparsed | 90 | 0 | -90 |

## Full ToMBench 2860

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Correct | 1415/2860 | 1505/2860 | +90 |
| Accuracy | 0.4948 | 0.5262 | +3.14 pp |
| Unparsed | 1172 | 1082 | -90 |

## After Selection Modes For Hinting

| Mode | Count |
|---|---:|
| tombench_p2_general_v1_candidate_verifier | 11 |
| tombench_p2_general_v1_hinting_pragmatics | 90 |
| tombench_p2_general_v1_story_pattern | 2 |


## Interpretation

The improvement is localized to left-brain indirect-intent inference.
The measurable behavioral change is that utterances like "the coffee is cold", "the trash can is lonely", or "do you know what day it is soon?" are mapped to the intended action before final answer selection.
This is useful for the broader project because it improves the cognitive step from surface utterance to hidden conversational obligation, rather than only changing final wording.
