# P3-B21 case04 native diagnostic grade

Date: 2026-09-15

## Outcome

**COMPLETE as a one-case developer-proxy diagnosis; negative for the product on this case.**

The eight immutable B20 replies were judged twice per turn, once in AB order and once in BA order,
using local `qwen3.5:9b` with native direct JSON Schema. All eight judgments passed the strict quote,
visible-evidence, correction-applicability and schema validators. Mapped preferences agreed across
both orders for all four turns.

| measure | product system | full-history direct-v2 | product minus direct |
| --- | ---: | ---: | ---: |
| attunement (0–2) | 1.125 | 1.625 | -0.500 |
| grounding (0–2) | 1.875 | 1.875 | 0.000 |
| correction (eligible u3/u4 only, 0–2) | 0.750 | 2.000 | -1.250 |
| continuity (0–2) | 1.750 | 1.875 | -0.125 |
| mapped preferences | 2 | 6 | — |

The judge preferred the product twice on u1, then preferred direct-v2 twice on each of u2, u3 and
u4. The largest operational failure is correction: product u3 restated the boundary without promising
to change its own behavior, and product u4 ignored the consent/compliance distinction entirely. In
contrast, direct-v2 explicitly said it would avoid a commanding tone on u3 and separated jokes from
action on u4.

The u4 result confirms the pre-grade trace diagnosis. The product selected `playful_tease` from
`可以吐槽我`, reused an arousal-specific core sentence, then M39 removed an unsupported `朝から`
reference by replacing it with another brain-related canned tease. No component preserved the other
half of the current act: `不要把玩笑當成我答應照做`.

## Reliability and cost boundary

- Result commit: `2a9dc88`; result SHA-256:
  `e307d3b27d8c286e284fb4aaf4d433735925f73868560002fe7cea5fc99e9ba5`.
- 8/8 judgments, 6,098 prompt + 2,111 completion tokens, 122.106642 s summed judge wall,
  122.139371 s runner wall, zero retries and zero paid calls.
- Preference order agreement was 4/4 turns (1.0). Individual sub-scores were not perfectly stable:
  for example product u3 correction was 0 in AB and 1 in BA, and one order flagged a Japanese issue
  that the reverse order did not. Therefore the exact decimal means are diagnostic, not gold labels.
- Generation cost retained from B20: product 1,747 total tokens and 38.924088 s summed turn wall;
  direct-v2 1,527 tokens and 9.197616 s. Product used 1.144x tokens and 4.232x turn wall on this case.
- B20 remains a preregistered generation-gate failure because its product-call minimum was wrong.
  B21 does not repair or relabel that failure.

This is a developer-authored case scored by a model judge, after annotation access, with no human
preference or independent holdout. It is useful for choosing the next single engineering variable,
but it cannot establish general inferiority or superiority, human felt understanding, or the formal
quality gate.

## Next attributable repair

The smallest supported repair is not a new global prompt. M39's bounded source frame should represent
an explicit current-turn distinction between permission to joke and permission to act/command. When
the selected policy is `playful_tease` and an upstream canned reply requires repair, the fallback must
tease about the visible topic while acknowledging that distinction, rather than reuse the old
"overactive brain" sentence. This can be tested deterministically in Chinese, English and Japanese,
then in an isolated product runtime; it does not authorize rerunning or rescoring B20/B21.
