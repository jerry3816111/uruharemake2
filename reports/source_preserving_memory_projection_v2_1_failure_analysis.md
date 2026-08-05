# Source-preserving Memory Projection V2.1 Failure Analysis

**Decision: phase 1 failed; no phase 2 and no runtime authorization.**

- Exact projections recognized: 5/8 (gate: >= 6/8)
- Projection misses despite preserved answers: 3/8
- Invalid long-context tool outputs: 4/32
- Prompt characters reduced: 90.3%
- Mean latency: 8.07s -> 3.43s

## Localized failures

- `6ade9755`: Where do I take yoga classes? (answer preserved: True)
- `af8d2e46`: How many shirts did I pack for my 5-day trip to Costa Rica? (answer preserved: True)
- `60d45044`: What type of rice is my favorite? (answer preserved: True)

The source projection remained exact and transport/model identity checks passed. The frozen 4B evidence extractor, not source corruption, is the unresolved bottleneck.
