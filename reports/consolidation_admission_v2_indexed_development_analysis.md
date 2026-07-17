# Consolidation Admission Indexed Development Pilot V2

| Condition | Correct | Accuracy | Median | Warm p95 |
|---|---:|---:|---:|---:|
| Frozen V1 source-bound JSON | 6/18 | 33.33% | 5.135s | 7.117s |
| V2 indexed tool frame | 8/18 | 44.44% | 2.853s | 3.038s |

- Accuracy delta: +11.11 percentage points
- Net correct gain: +2 cases
- Wisdom: 2/6
- Procedural: 0/6
- Episodic-only none: 6/6
- Exact frame: 1/18
- Grounded evidence: 8/18
- Positive grounded evidence: 8/12
- False long-term writes: 0
- Missed long-term writes: 10
- Tool parse success: 83.33%
- Index contract success: 72.22%
- Successful model calls: 36
- Transport attempts: 36
- All preregistered gates: **FAIL**
- Decision: `freeze_negative_result_and_leave_enabled_consolidation_unchanged`

This is a Codex-labeled development pilot, not an official benchmark or a runtime-memory test. It cannot establish broad human-like memory.

- Newly correct case IDs: cav2_eng_wisdom_train_commute, cav2_jpn_wisdom_paper_books
