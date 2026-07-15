# V50 Qwen2B non-semantic carrier probe

| carrier | parse | fidelity | single | unexpected | median | p95 | eligible |
|---|---:|---:|---:|---:|---:|---:|---:|
| boolean_two_field_control | 0.0% | 0.0% | 0.0% | 0.0% | 1.09s | 1.12s | False |
| enum_two_field_candidate | 0.0% | 0.0% | 0.0% | 0.0% | 1.09s | 1.12s | False |
| enum_single_field_candidate | 0.0% | 0.0% | 0.0% | 0.0% | 1.07s | 1.09s | False |
| scalar_enum_candidate | 0.0% | 0.0% | 100.0% | 0.0% | 0.82s | 0.92s | False |

- Selected carrier: `None`
- Decision: `retire_qwen35_2b_from_binary_gate_role`
- This result measures transport compatibility only, not semantic ability or runtime safety.
