# Memory Source Monitoring + Adaptive Reread V3: Preregistration

## Research question

Can the memory pipeline distinguish the user's own autobiographical statements from an assistant's
guess, refuse to invent an answer when the user never supplied one, and reread the original episode
only when its first evidence pass is insufficient?

This is not a benchmark-answer patch. The implementation receives source roles, a generic question
frame, and model-extracted evidence, but never receives a gold answer, gold source index, or the
case's answerability label.

## Evidence behind the design

- The Source Monitoring Framework treats memory as including judgments about where information
  came from; those judgments use flexible criteria and can fail:
  https://pubmed.ncbi.nlm.nih.gov/8346328/
- FLARE actively decides when and what to retrieve, and regenerates when the first generation has
  low-confidence content instead of paying for retrieval unconditionally:
  https://aclanthology.org/2023.emnlp-main.495/
- Self-RAG reports that indiscriminate retrieval can be unhelpful and instead retrieves and
  reflects on demand: https://arxiv.org/abs/2310.11511
- HiLight preserves the original context and adds minimal evidence highlights rather than replacing
  the episode with a lossy summary: https://arxiv.org/abs/2604.22565

These sources motivate source checking and conditional rereading. They do not prove that this
implementation works; the frozen paired experiment below must show that.

## Frozen matched conditions

| condition | user source authority | insufficiency gate | highlighted second read | final stage |
| --- | --- | --- | --- | --- |
| A: full-session freeform | existing mixed-role path | no | no | existing freeform |
| P: provenance gate | user self-report only | yes | no | freeform or explicit abstention |
| R: adaptive reread | user self-report only | yes | only after P is insufficient | freeform or explicit abstention |
| S: R + span contract | user self-report only | yes | reuse R | grounded source spans or abstention |

`P - A` isolates source authority plus the generic sufficiency gate. `R - P` isolates conditional
rereading. `S - R` isolates source-span realization. `R - A` is the primary end-to-end comparison.

## Frozen data and controls

- 16 entirely new scenarios, each placed at the beginning, middle, and end: 48 paired cases.
- 36 cases have sufficient user evidence; 12 contain only assistant guesses and explicit user
  uncertainty, so the correct behavior is abstention.
- Development and transfer each contain 24 cases with disjoint scenario IDs and questions.
- Zero official benchmark items and no V1/V2 scenario ID or question reuse.
- The frozen selector finds all 96 relevant user utterances, selects 96 utterances in total, and may
  not be tuned on V3.
- Model, seed, temperature, context budget, question frames, item order, fixed abstention sentence,
  and scoring rules are frozen.
- Dataset file SHA-256: `e9ce06826cf68e37b03656500b2f5b64caf1a9bb620d7597fcd63f08241c64e2`.
- Canonical cases SHA-256: `329b3df20845434b494f5a97330d5fbac18616c789d7f39e7128a8a49c12e1f3`.

## Generic gate and success boundary

The gate does not know whether a case is answerable. It accepts only grounded user events, rejects
pure uncertainty, and checks only the expected answer shape derived from the question: clock time,
quantity, cadence, placement, explicit yes/no ownership, or two comparable numeric endpoints.

Every treatment must abstain on all 12 unanswerable cases. Adaptive rereading must not lower
answerable accuracy in either split or any capability family, may run only after primary
insufficiency, and must not admit assistant-only facts. Every removed highlight tag must restore an
exact source quote. Passing permits only a new untouched evaluation; it does not authorize a
runtime change or an external benchmark claim.
