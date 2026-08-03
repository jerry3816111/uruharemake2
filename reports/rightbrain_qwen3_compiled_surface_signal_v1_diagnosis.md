# Qwen3 compiled surface-signal diagnosis

## Decision

- Formal outcome: `compiled_surface_signal_alignment_not_improved`
- The preregistered hypothesis failed.
- Full-pipeline holdout, training, adapter save, persona claim, and production activation remain unauthorized.

## What changed

The control exposed the current abstract provider object at the first top-level JSON field. The candidate replaced only that object with a deterministic Japanese compilation describing concrete surface operations. Model weights, system message, semantic plan, memory policy, prompts outside the signal, decoding, references, and scoring were unchanged.

## Reproducible result

All three repeats produced the same output hashes, including the repeat with reversed condition order.

| Measure | Abstract control | Compiled signal | Delta |
| --- | ---: | ---: | ---: |
| Joint semantic/memory/surface contract | 8/8 | 8/8 | 0 |
| Correct provider-reference direction | 3/8 | 5/8 | +2/8 |
| Mean provider-reference margin | -0.030762 | 0.014993 | +0.045754 |
| Target/neutral pairs with different output | 4/4 | 2/4 | -2/4 |
| Exact reference copies | 0 | 0 | 0 |

Peak MLX memory was 8,598,573,144 bytes. Each repeat used the unchanged 4,022,468,096-parameter bfloat16 base model and performed 16 greedy generations with no optimizer update or save.

## Why the hypothesis failed

The compiler made the shared instructions executable: both providers became shorter, plain-form, and contract-preserving. It did not make their provider-specific differences sufficiently executable. Both signals still shared the strongest operations: one short sentence, at most two clauses, casual plain form, no added facts, and semantic/memory priority.

For the noodle invitation and the nine-o'clock progress commitment, these shared operations dominated the weaker target-versus-neutral delivery instructions, so both providers converged to exactly the same reply. This explains why reference direction improved while provider-pair differentiation regressed: the candidate moved outputs toward the common short-casual region of both reference sets rather than establishing a distinct target-conditioned policy.

The provider-reference margin is therefore not sufficient by itself. It is partly sensitive to brevity and shared wording. The paired-difference gate correctly prevented that metric from authorizing the mechanism.

## Evidence boundary and next research direction

This result supports three narrow conclusions:

1. Concrete surface instructions can preserve the semantic and memory contract better than moving abstract labels alone.
2. A prompt-only compiler does not yet provide a reliable provider identity channel.
3. Further wording changes on synthetic references would risk optimizing the probe instead of learning public-persona behavior.

Before another RightBrain modification, the next high-value unit should freeze a source-disjoint public-persona evaluation corpus and evaluator. That unit must measure observable target-versus-neutral behavior on unseen public situations, include non-copy and provenance checks, and remain separate from training. Only after the evaluator is reliable should the project compare prompt conditioning, lightweight adaptation, or candidate reranking against the same frozen target-specific holdout.
