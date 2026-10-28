# P4 codec amendment 1: preserve frozen research-reader hashes

This amendment is prospective to the source commit and does not change the
2026-10-27 storage variable, size/CPU thresholds, or original evidence. A
read-only lock search during implementation found that
`planner_supervision_v76.py` is pinned by V84–V88 harness locks, and
`build_rightbrain_forbidden_projection_live_evidence.py` is pinned by the
V90 harness lock. Editing either in place would silently change historical
research artifacts. The latter and the selector builder only consume top-level
fields from Web rows, so they do not need the trace decoded for their frozen
scoring logic; their files remain byte-identical to HEAD.

Keep `planner_supervision_v76.py` unchanged. For any **new** compressed Web
row handed to its input-context function, explicitly call the new
side-effect-free `load_decoded_conversation_jsonl(path)` bridge first. Do not
claim that the historical V76 CLI's unmodified `load_jsonl` automatically
supports new encoded rows. New annotation, Web graph, compute-retention and
M45–M52 evidence readers that actually inspect trace may adopt strict decode
without rewriting archived row bytes or frozen reports. A synthetic old/new
parity test must cover the explicit V76 bridge and every changed reader.

The V90 suite already had SHA lock mismatches on committed HEAD before this
batch: `uruha_brain_mac.py` HEAD SHA
`c1833a55ecb9c690decca66d1b90a6bdf075780db83066a5b9c6ea47bc0e7fff`
versus frozen `75d18d08...`, and Web HEAD SHA
`2b541d6f3a1062ae3972df33676597fb42f60b8f19c9610338595f04fc90167a`
versus frozen `2b874e70...`. Do not amend those historical hashes or call
the V90 current-main authorization PASS; report its 3 failures separately.
This hash mismatch does not authorize changing V90 source to make it green.

This is a scope correction, not a second storage variable. Same-model
inspection only; no independent human review or formal study authorization.
