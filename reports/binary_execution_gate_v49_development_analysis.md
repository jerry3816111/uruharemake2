# V49 binary immediate-execution gate result

Retired V45 data are used for development only. V47 candidate perception and V48 compilation are fixed.

| model | size | parse | binary | execute P/R | calls | false | median / p95 | eligible |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen35_0_8b_binary | 873.44M | 91.8% | 37.7% (23/61) | 75.0% / 8.6% | 43.8% (21/48) | 1 | 0.61s / 1.27s | False |
| qwen35_2b_binary | 2.3B | 0.0% | 0.0% (0/61) | 0.0% / 0.0% | 39.6% (19/48) | 0 | 1.14s / 2.33s | False |
| qwen35_4b_binary | 4.7B | 100.0% | 90.2% (55/61) | 93.9% / 88.6% | 87.5% (42/48) | 1 | 1.69s / 3.60s | False |

- Selected: `None`
- Decision: `reject_binary_gate_only_hypothesis`
- Interpretation: A single binary model gate is still insufficient; the next step must add calibrated rejection or separate immediate-request perception from semantic state, without tuning on this dataset.
- No result in this development run authorizes runtime or physical VRM execution.
