# Reflection Admission Evidence-Gate Development Pilot V6

| Condition | Correct | Accuracy |
|---|---:|---:|
| Admit every proposed procedural reflection | 16/32 | 50.00% |
| Qwen 3.5 4B evidence gate | 19/32 | 59.38% |

- Accuracy delta: +9.38 percentage points
- Net correct gain: +3 cases
- Explicit instructions retained: 3/16
- Unsupported proposals rejected: 16/16
- False admits: 0
- False rejects: 13
- Tool parse success: 100.00%
- Exact evidence contract success: 100.00%
- Median wall time: 3.474s
- Warm p95 wall time: 3.641s
- All preregistered gates: **FAIL**
- Decision: `freeze_negative_result_and_abandon_exact_evidence_gate_contract`

This is one development-only test on a Codex-labeled Tatoeba sample. It does not authorize runtime memory writes, a fresh holdout, or a broad claim about human-like dialogue.

- False-reject case IDs: v6_eng_admit_9189284, v6_eng_admit_9007204, v6_eng_admit_5088052, v6_eng_admit_4667130, v6_eng_admit_2595690, v6_eng_admit_264353, v6_eng_admit_12455447, v6_eng_admit_10871911, v6_jpn_admit_9518677, v6_jpn_admit_10558888, v6_jpn_admit_218968, v6_cmn_admit_1182071, v6_cmn_admit_382997
