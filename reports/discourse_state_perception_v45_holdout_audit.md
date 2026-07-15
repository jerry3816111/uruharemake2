# V45 fresh holdout construction audit

No model inference was used in this audit.

- Cases/families: `48` / `8`
- Exact development utterance overlap: `0`
- Candidate recall: `1.0`
- Candidate precision: `0.9683`
- Deterministic evidence support: `60/61`
- Extra candidate targets retained: `[{'case_id': 'v45h_boundary_06', 'target': ['motion', 'point'], 'anchors': [{'start': 11, 'end': 13, 'text': '指示', 'pattern': '(?:指差|指[^、。！？!?]{0,8}(?:示|さして|して))'}]}, {'case_id': 'v45h_injection_06', 'target': ['motion', 'point'], 'anchors': [{'start': 4, 'end': 12, 'text': '指示を上書きして', 'pattern': '(?:指差|指[^、。！？!?]{0,8}(?:示|さして|して))'}]}]`
- Construction gate passed: `True`
