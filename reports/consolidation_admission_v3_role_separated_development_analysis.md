# Consolidation Admission Role-Separated Development Pilot V3

| Condition | Correct | Accuracy | Median | Warm p95 |
|---|---:|---:|---:|---:|
| Frozen V2 indexed tool | 9/18 | 50.00% | 2.845s | 2.963s |
| V3 role-separated tool | 10/18 | 55.56% | 2.396s | 2.532s |

- Accuracy delta: +5.56 percentage points
- Net correct gain: +1 cases
- Wisdom: 3/6
- Procedural: 2/6
- Episodic-only none: 5/6
- Exact semantic frame: 7/18
- Grounded evidence: 9/18
- Positive grounded evidence: 8/12
- Derived applicability: 10/18
- False long-term writes: 1
- Missed long-term writes: 6
- Tool parse success: 77.78%
- Index contract success: 66.67%
- Successful model calls: 36
- Transport attempts: 36
- All preregistered gates: **FAIL**
- Decision: `freeze_negative_result_and_stop_single_call_qwen25_7b_frame_simplification`

This is a Codex-labeled development pilot, not an official benchmark or runtime-memory test. It cannot establish broad human-like memory.

- Newly correct case IDs: cav3_eng_wisdom_color_accessibility, cav3_eng_procedural_recap_signal, cav3_jpn_procedural_parallel_translation
- Regression case IDs: cav3_eng_wisdom_keyboard_navigation, cav3_cmn_wisdom_mind_map
