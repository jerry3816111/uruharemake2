# Semantic recall support V1 holdout diagnosis

- Decision: `holdout_reject_or_inconclusive`
- Wrong trace selections: 9
- Target-removed selections: 6/8
- Lexically supported target / replacement / hard negative: 7/8 / 3/8 / 6/8
- Target and hard-negative shared-unit ranges: [0, 4] / [0, 4]
- Whole-record sensitive suppressions: 1

## Conclusion

Both target and hard-negative shared-count ranges are 0 to 4; raising the threshold removes valid targets while retaining some hard negatives.

A bypass must require a question-conditioned answer-bearing evidence span, not topic overlap. Span-level speakability must inspect only the proposed evidence span.

Forbidden: Do not tune token stoplists, shared-unit thresholds, or case-specific terms against this exposed holdout.
