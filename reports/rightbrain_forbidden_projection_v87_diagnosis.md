# V87 Post-hoc Control-Variable Diagnosis

- Formal V87 decision remains: `inconclusive_effect_between_preregistered_gates`
- Formal replay reproduced: **YES**
- Control-variable violation found: **YES**

| Replay setting | Contract match | Gate accept | Semantic rejects | Projected markers |
|---|---:|---:|---:|---:|
| Observed control | 0/12 | 0/12 | 11 | 0 |
| Observed treatment | 0/12 | 1/12 | 11 | 6 |
| Intended control (post-hoc) | 12/12 | 10/12 | 0 | 0 |
| Intended treatment (post-hoc) | 12/12 | 12/12 | 0 | 4 |

## Root Cause

The V87 replay left canonical memory cues and the explicit length contract at their default-off runtime values even though the preregistration required the frozen V86 treatment settings. The candidate gate therefore evaluated a different semantic contract from the V86 replies.

The intended-setting rows are exploratory diagnostics, not a replacement formal result.

## Next Falsifiable Step

Preregister and lock a corrected V87.2 paired replay that explicitly sets canonical memory cues and the explicit length contract to true in both conditions, while changing only forbidden-conflict projection.
