# V46 local model-capacity development result

This uses the consumed V45 holdout as retired development data. It is not a new holdout result.

| model | size | parse | commitment | requested P/R | call exact | false action | extra requested | median / p95 | eligible |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen35_0_8b | 873.44M | 100.0% | 14.8% (9/61) | 0.0% / 0.0% | 39.6% (19/48) | 0.0% | 0 | 0.72s / 1.45s | False |
| qwen35_2b | 2.3B | 100.0% | 60.7% (37/61) | 64.3% / 77.1% | 64.6% (31/48) | 12.5% | 1 | 1.11s / 2.26s | False |
| qwen35_4b_reference | 4.7B | 100.0% | 83.6% (51/61) | 93.9% / 88.6% | 85.4% (41/48) | 4.2% | 1 | 2.32s / 4.76s | False |
| qwen35_9b | 9.7B | 100.0% | 86.9% (53/61) | 85.0% / 97.1% | 83.3% (40/48) | 10.4% | 0 | 3.65s / 7.47s | False |
| qwen25_7b_historical | 7.6B | 100.0% | 86.9% (53/61) | 91.4% / 91.4% | 85.4% (41/48) | 6.2% | 0 | 1.45s / 2.99s | False |

- Selected model: `None`
- Decision: `reject_model_capacity_only_hypothesis`
- Interpretation: No installed model satisfied the fixed safety and semantic contract. Model capacity alone is not an adequate correction; the next experiment must split candidate grounding, deterministic scope perception, and uncertain semantic judgment.
- Runtime remains unchanged; physical VRM execution remains disabled.
