# P3-B49 semantic-preserving Japanese repair acceptance

## Result

P3-B49 repairs the data-flow break behind B47 u3. When self-monitor detects a non-Japanese surface, it no longer replaces the semantic core with the internal instruction `日本語だけで、元の意味を落とさず言い直す`. The original semantic source remains available. Immediately before the visible-language firewall, a new bounded repair seam either:

1. restores an already guard-valid Japanese semantic core with zero model calls;
2. on an ordinary non-protected turn, asks the existing M31 source-first authorizer for a Japanese realization and accepts it only when language, shared anchors and any predeclared observable conversation act pass; or
3. records a rejection and leaves the existing fail-closed language fallback in control.

Memory, identity, crisis/support, boundary/refusal, explicit response-form and correction-authority routes do not enter the new model repair. A completed earlier M31 call is not retried.

## Visible before and after

The exposed B47 developer source contained an intermediate core with the correct topic and complaint meaning: `連註解都不停，真煩人。`

| Stage | Visible result | Topic retained | Complaint act retained |
| --- | --- | ---: | ---: |
| B47 before | `ん、その話もう少し聞かせて。` | no | no |
| first B49 real attempt | `注釈がまた届くんだね` | yes | no |
| final B49 isolated local attempt | `また新しい注釈が来たのはうざいだろ` | yes | yes |

The first real attempt is deliberately retained as a negative result. Natural Japanese alone was not accepted as semantic success. The final attempt required two Japanese anchors shared by the source normalization and reply, plus an observable `frustration_complaint` marker. It passed with M31 confidence 0.95, two visible anchors and no final language-rejection reason.

This final line is model-generated and guard-valid, but it has not been independently human-rated for naturalness. It must not be described as the best possible Japanese wording.

## Observable act is not private-state inference

The added act requirement is intentionally narrow. It recognizes visible multilingual complaint cues such as rhetorical “will it ever stop”, `有完沒完`, `うざい` or `いい加減`. It does not claim the speaker's hidden feeling as fact. A neutral translation is rejected when the source visibly performs that act; no generic complaint sentence is appended after generation.

## Verification

- new B49 tests: **8 passed**;
- B49 + M31/M32 + language/memory/M48 focused and adjacent set: **70 passed**;
- expanded planner/runtime/graph/personhood/proactive regression set: **164 passed**;
- initial expanded run exposed 8 fake-right-brain compatibility failures; the final seam now records `not_evaluated` and preserves the reply when that test capability is absent, after which all 164 passed;
- existing warnings: 9 dependency/deprecation warnings;
- `git diff --check`: clean before freeze;
- local development model calls: **4**, all localhost qwen3.5:9b; external calls: **0**;
- approximate shell wall time across the four calls: **55.4 seconds**;
- exact tokens: unavailable because those isolated diagnostic calls did not attach the compute ledger.

The Web compact trace and node graph expose `japanese_semantic_repair_m49 -> visible_language_guard`, including authority, status, act preservation and failure checks without raw dialogue.

## Claim boundary and remaining failure

This is mechanism evidence plus one exposed isolated local example. It is not a fresh prospective case, full product-session evidence, Safari evidence, human preference evidence, formal temporal holdout evidence, independent translation certification or proof that UruhaBrain outperforms direct LLM generation.

It addresses the u3 class: non-Japanese semantic content no longer has to be erased by the final language fallback. It does not address u4: the explicit request `陪我吐槽` is still classified as generic `share_arousal`, so the requested conversation act can be lost before language repair. P3-B50 takes that separate variable next. The immutable B46/v3 release remains closed.
