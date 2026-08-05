# V2.8 Fresh Reserve Construction

**Decision: `construction_failed_do_not_freeze_model_evaluation_contract`**

| Construction measure | Frozen requirement | Observed |
|---|---:|---:|
| Balanced questions | 8 | 5 |
| Adjacency answer retention | at least 7 | 3 |
| Gain over isolated Top-3 | at least +2 | +1 |
| Mean target character ratio | at most 50% | 25.5% |
| Model calls | 0 | 0 |

The four fresh conversations produced six corrected exact-string candidates. The
frozen maximum of three cases per conversation reduced this to five balanced
cases because one conversation contained four candidates, one contained none,
and the other two contained one each.

Adjacency retained the answer-bearing source in 3/5 cases, compared with 2/5
for isolated Top-3. This +1 gain is below the preregistered +2 gate. The compact
representation remained within the character-ratio budget.

No model evaluation, runtime change, memory write, or VRM action is authorized.
This result measures deterministic construction and source retention only. It
does not measure answer quality or full-pipeline memory behavior. The final two
reserve conversations remain excluded from case selection.
