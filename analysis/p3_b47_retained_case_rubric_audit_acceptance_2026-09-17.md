# P3-B47 retained case01 rubric audit acceptance

## Result

P3-B47 completed a deterministic audit of the only B46 case that reached immutable paired outputs. The semantic judgements are a post-lock Codex developer proxy, not an independent human rating. The auditor verifies every judgement against the source, rubric, locked reply hash, exact rubric act ids and quoted reply evidence before aggregating it.

Both conditions fail the predeclared case rule (`u4=5/5` and no critical failure):

| Condition | Required acts | Forbidden acts absent | Source grounding | Uncertainty | Natural Japanese | Total | u4 | Critical failures | Pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| UruhaBrain product | 0/4 | 3/4 | 0/4 | 4/4 | 4/4 | 11/20 | 2/5 | u4 contradicts explicit request | no |
| same-model direct | 1/4 | 3/4 | 3/4 | 4/4 | 1/4 | 12/20 | 2/5 | u2/u3 non-Japanese; u4 contradicts request | no |

Cases 02 and 03 are `not_generated` with `score=null`; they are not silently counted as failures or zeros. There is no batch comparison and no condition winner.

## What this adds beyond the B46 surface failure

The product's language guard works in this case, but natural Japanese is not equivalent to understanding. Its four replies all pass the Japanese-surface dimension while none passes source grounding or the complete required semantic act. Conversely, the direct condition usually stays on the current topic but cannot maintain the Japanese character surface. The one-point proxy-total difference is not evidence that the direct condition is generally better; both fail the primary-turn rule, and the audit is neither independent nor a complete batch.

## Trace diagnosis

The locked product trace localizes the product failure to late semantic realization rather than database contamination or transport:

1. **u1:** the upstream deterministic candidate was grounded (`一回、その版って何の作品の話だよ。`), but the adaptive desired-response policy later replaced it with the scenario-specific `calibrate_need` template about sleep and racing thoughts. Source-atom authorization had already reported `source_pattern_unavailable`, yet the policy surface and M39 policy-act verifier accepted the unrelated sentence.
2. **u2:** the system correctly detected the Chinese `不用幫我列方法` span as `practical_help_forbidden`, but it again realized `calibrate_need` as the same sleep/racing-thought template. The response-form decision was retained while the current topic and acknowledgement were lost.
3. **u3:** the intermediate core (`連註解都不停，真煩人。`) contained the requested complaint meaning but was Chinese. The visible-language guard rejected an internal rewrite instruction and used the safe Japanese fallback `ん、その話もう少し聞かせて。`, losing the semantic content.
4. **u4:** `陪我吐槽` was classified as generic `share_arousal`; the fixed realization produced generic presence. The verifier checked that the chosen policy was performed, but did not require the current topic or the more specific requested action to survive.

These are three manifestations of one missing invariant: **a late surface may be Japanese and policy-shaped while no longer carrying the current turn's observable topic and requested conversational act.** B48 should add that invariant at the current-turn semantic-commit boundary; it should not add another case-specific reply template.

## Verification

- 6 focused tests passed in 0.32 seconds;
- bound artifact drift, invented rubric acts, inconsistent dimension scores, non-existent evidence quotes and non-Japanese critical-failure inconsistency all fail closed;
- audit execution used 0 model calls and 0 network calls;
- the full row-level evidence is in `analysis/p3_b47_retained_case_rubric_audit_2026-09-17.json`.

## Claim boundary

This is an inspectable developer-proxy diagnosis of one exposed case. It is not human-preference evidence, a formal temporal holdout, a three-case comparison, proof of general UruhaBrain advantage, or permission to regenerate the exposed v3 case as if it were fresh.
