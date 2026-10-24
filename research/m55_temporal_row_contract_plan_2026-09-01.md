# M55 Temporal Row Contract and Leakage Gate · 2026-09-01

## Single question

Can the independently coded V9 public-observation events be converted into Equation V1
`cutoff -> unseen observable behavior` rows without letting any part of the target behavior enter the
model-visible input?

## One attributable change

Add one downstream, content-free temporal-row contract between V9 event coding and the existing M1
temporal dataset validator. The V7 and V9 frozen codebooks, frames, ledgers, reliability thresholds, and
results remain unchanged. No Uruha source content, private ledger, sealed future, model call, or formal
result is consumed by this milestone.

The new contract requires a selected event to be split into half-open observable intervals:

```text
event start <= observable input start < prediction cutoff
prediction cutoff < observable target-behavior start < target-behavior end <= event end
```

The current V9 schema records only whole-event start/end. It therefore cannot by itself prove that the
context paraphrase stops before the target behavior begins. The gap must be visible and fail closed;
the whole-event start must never be silently reused as the prediction cutoff.

## Data boundary

- real rows remain in the existing gitignored private research area;
- only researcher paraphrases are allowed; copied quotes, transcripts, media, model output, target
  replies, and private-state claims are forbidden;
- current model input may contain only the pre-cutoff observable-input paraphrase and prior completed
  observations;
- the current row's behavior label and behavior paraphrase remain outcome-side only;
- the nine M54 variables receive an explicit `observed`, `derived_pre_cutoff`,
  `unavailable_not_inferred`, or later-computed status; missing fields are never imputed;
- synthetic fixtures may test the compiler, but can never authorize a real-person claim or M56.

## Acceptance

1. Contract bindings and the nine-variable crosswalk validate deterministically.
2. A current-schema audit identifies the missing prediction-boundary fields and reports that V9 alone
   is not M56-compilable.
3. A synthetic, raw-free record pack compiles to the existing temporal schema with zero leakage.
4. The compiled model view contains no current outcome label, outcome paraphrase, annotation
   confidence, or post-cutoff timestamp.
5. Missing/overlapping boundaries, false attestations, prohibited raw fields, non-independent review,
   and unknown behavior labels fail closed.
6. A real-person pack cannot authorize model execution while the live M55 human gate is incomplete.
7. The graphical audit explains `observable input -> locked cutoff -> future behavior` without exposing
   source URLs, session tokens, or private paraphrases.

## Claim boundary

A pass proves only that the future-prediction row format and compiler are leakage-resistant and ready
for later human-coded inputs. It does not create human labels, validate Equation V1, authorize M56,
prove Uruha similarity, or describe a biological human brain.
