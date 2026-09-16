# P3-B26 pre-existing source eligibility audit

Date: 2026-09-16

## Outcome

**FAIL: no eligible pre-existing speaker-qualified-memory case exists in the frozen B2 source corpus.**

The audit opened only `datasets/p3_developer_smoke_source_v1.json`, whose SHA-256 still matches the
B2 freeze. It did not open the annotation file or any target outcome.

The corpus has six cases and exactly one `speaker_qualified_memory` family member:
`p3-smoke-speaker-memory-en`. That case was executed in B23, its failure trace directly motivated the
B24 mechanism, and its bounded scenario was used again for B24/B25 product and Safari acceptance.
It therefore fails both the not-previously-executed and not-repair-exposed criteria.

The other five cases test different families. Relabeling one of them as speaker-memory validation
would change the research question after looking at the repair and would not test the B24 mechanism.
No source projection, output-lock config or release was created.

## Access and cost boundary

- annotation content accessed: no;
- target outcome accessed: no;
- generation, judge, network and paid calls: 0;
- production database access: 0;
- B23 output and score changed or rerun: no.

This failure does not say B24 is ineffective. It says the current frozen source inventory cannot
provide a non-exposed validation of that repair. A new post-repair developer case could test another
example but could not honestly be renamed a pre-existing holdout.

For overall P3 progress, repository artifacts show case03, case04 and case05 have case-specific output
locks, while `p3-smoke-unknown-topic-ja` has no case-specific generation artifact. The next task may
freeze case06 as a pre-existing, unexecuted **developer-smoke** comparison for the separate
`unknown_and_topic_change` family. It must not be cited as B24 generalization or an independent
holdout, and its annotations remain unopened until generation is locked.
