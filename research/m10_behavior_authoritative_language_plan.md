# M10 behavior-authoritative language realization plan

Status: frozen design baseline before the first registered M10 model call  
Date: 2026-08-15  
Authority: `/Users/jerrychang/Downloads/RESEARCH_SPEC_FOR_CODEX.md`

## Why this stage is necessary

M1–M9 stop at a calibrated behavior distribution. The master specification requires language to be generated only after behavior selection. The existing chat and public-persona systems are reusable downstream subsystems, but they do not yet prove that the language model obeys the frozen M9 decision instead of silently deciding again.

M10 therefore separates two questions:

1. **realization faithfulness** — does the utterance express the behavior selected upstream?
2. **end-to-end outcome fit** — was that upstream behavior prediction correct for the observed future?

An utterance can be faithful to a wrong prediction. Keeping these measures separate prevents fluent Japanese from hiding a prediction failure.

## Frozen conditions

All conditions use the same `qwen3.5:9b`, event, state snapshot, development-only Uruha surface brief, generation options, output budget, and hardware.

| Condition | Behavior authority | Runtime meaning |
|---|---|---|
| `L0_DIRECT` | none | direct-language baseline; the LLM may choose its own act |
| `L1_PREDICTED_BEHAVIOR` | frozen M9.1 `MIRA_FULL_ADAPTATION` distribution and selected label | proposed architecture |
| `L2_ORACLE_BEHAVIOR` | one-hot actual future label | future-leaking diagnostic ceiling; forbidden at runtime |

The 16 M9 Mira future events are all included. They are new to language realization but are already exposed for behavior analysis, so the claim is a **nonfresh synthetic downstream diagnostic**, not new prediction evidence.

## Falsifiable hypotheses

1. Scored prompt-token range is at most two tokens within every three-condition case.
2. `L1` and `L2` each express their authoritative behavior on at least 75% of cases according to a separately prompted frozen classifier proxy.
3. At least 90% of `L1` and `L2` replies pass the Japanese visible-output contract.
4. `L2` outcome-label alignment is at least `L1` and strictly better than `L0`.
5. `L1` outcome-label alignment is at least `L0`; failure here means upstream prediction errors outweigh the value of explicit control.
6. No condition invents private Uruha facts or claims mind-reading.

The proxy classifier is not a human judgment. Every failure and raw output remains visible.

## Persona and evidence boundary

The surface brief is limited to the existing public-evidence development hypotheses: casual, direct without automatic hostility, guarded with unfamiliar people, and no forced catchphrase. It changes wording only and may not override the behavior label. Existing governance explicitly forbids runtime persona activation and persona-fidelity claims; M10 does not change that authorization.

Synthetic Mira is the behavior target in this diagnostic. Uruha is only a separable development expression carrier here. This does not constitute a coherent or validated Uruha human model.

## Evaluation and artifacts

- preserve raw generation and classifier replies;
- record prompt hashes, actual Ollama prompt tokens, completion tokens, latency, model identity, and condition order;
- build a blinded three-way human-rating packet, but report human preference as pending until independent ratings exist;
- render event → behavior distribution → selected action → Japanese utterance → decoded act → observed outcome as an interactive Web graph;
- do not write to production dialogue memory and do not call tools or perform physical actions.

## Stop and embodiment rule

Voice synthesis and VRM are optional downstream demonstrations. They remain outside the scientific claim until the behavior-prediction stability problem exposed by M8/M9 and the M10 language-authority gate are honestly characterized. A failed M10 hypothesis is retained; it is not repaired against these 16 exposed outcomes.
