# V44 non-semantic carrier probe

| carrier | parse | label fidelity | single result | unexpected | median | p95 | eligible |
|---|---:|---:|---:|---:|---:|---:|---:|
| scalar_enum_schema | 0.0% | 0.0% | 100.0% | 0.0% | 0.93s | 1.08s | False |
| two_field_object_schema | 100.0% | 100.0% | 100.0% | 0.0% | 1.14s | 1.21s | True |
| nested_label_schema | 100.0% | 83.3% | 100.0% | 0.0% | 0.97s | 1.01s | False |
| tool_call_schema | 100.0% | 100.0% | 100.0% | 0.0% | 2.38s | 2.46s | True |

- Selected carrier: `two_field_object_schema`
- Decision: `run_v44_semantic_development`
- This probe contains no benchmark utterance and authorizes no runtime or physical action.
