# P3-B44 prospective v3 data and rubric freeze acceptance

Date: 2026-09-17

## Outcome

**PASS for pre-generation data and rubric commitment.**

Three new four-turn developer cases and their turn-level evaluation contracts were committed in
`4169bf9` before any product or direct-baseline output was generated. The product under test remains
the earlier snapshot `0cab07b`; source creation did not authorize tuning that product before its
first v3 execution.

This improves on B33's source-only sequence by fixing the semantic scoring contract before outputs
exist. It does not make the cases independent human data or a formal temporal holdout: the same
project developer authored both source and rubric, and the scenarios intentionally probe known
failure families with new wording.

## Frozen batch

- Chinese: a third report revision receives more comments; the user knows how to revise and asks
  for shared exasperation rather than analysis or a checklist.
- English: repeated concert-ticket checking is clarified as excitement; after a session boundary,
  the user explicitly asks for shared excitement and one tentative song guess.
- Japanese: an ambiguous team follow-up has a prior two-week delay; the user asks to keep the
  current state pending rather than call it rejection or offer false reassurance.

Each case has four turns split across two sessions. At each generation step, only the current and
earlier user turns may be visible; future turns and every annotation remain locked.

## Predeclared evaluation

Each of the 12 turns has already-fixed:

- evidence turn IDs;
- required and forbidden semantic acts;
- acceptable semantic alternatives;
- an uncertainty boundary.

The five binary dimensions are required acts, forbidden-act avoidance, source grounding,
uncertainty handling and natural Japanese surface. The fourth turn is primary; a case passes only
when that turn scores 5/5 and no critical failure appears in any turn. Ties remain ties. There is no
gold reply, target wording, model output, condition winner or style tiebreak in the annotation file.

## Verification

- 3 cases, 12 turns, 6 sessions and languages ordered Chinese / English / Japanese;
- 12/12 content hashes and 12/12 predeclared turn rubrics validated;
- future-turn evidence references: 0;
- exact normalized text overlap with the 24 B2 and 12 B33 user turns: 0;
- source-side answer, score, rubric or winner payloads: 0;
- annotation-side target replies or winner payloads: 0;
- 13 focused and adjacent freeze tests passed in 0.20 seconds;
- `git diff --check` passed;
- 0 model calls, 0 network calls, 0 paid calls and 0 generated outputs.

## Claim boundary and next gate

B44 proves only that the next comparison cannot legitimately change these inputs or semantic
criteria after seeing outputs. It proves no system quality or advantage. The next gate must bind an
immutable, no-retry execution contract to these exact source and annotation hashes while keeping
the annotations unavailable to both generation conditions until every output is locked.
