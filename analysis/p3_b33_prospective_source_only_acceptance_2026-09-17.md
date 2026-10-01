# P3-B33 prospective source-only case freeze acceptance

Date: 2026-09-17

## Outcome

**PASS for a new source-only prospective developer batch.**

All six B2 developer-smoke cases were already generated, graded or exposed to product repair by
B6–B31. B26 also showed that no unused pre-existing source case could legitimately be relabeled as
fresh evidence. B33 therefore created new user-only conversations and froze them before any output,
annotation or judge call.

The source and verifier were committed in `a1ca9be`. The source is explicitly labeled developer-
authored after B31/B32 and not a formal or temporal holdout.

## Frozen source

The batch contains three distinct four-turn cases, each split across two sessions:

- Chinese: room-tidying overload, later rejecting a checklist and asking to complain together;
- English: delivery-page refreshing that is excitement rather than anxiety;
- Japanese: ambiguous relational wording where prior delay makes false reassurance unsafe.

These descriptions are observable setup metadata, not gold replies. The case records contain only
IDs, language/family metadata, sessions, user text and text hashes. They contain no assistant reply,
score, rubric, winner, condition preference, solution rule or annotation.

## Validation

- 3 cases, 12 user turns, 6 sessions, 3 languages and 3 distinct families;
- 12 allowlisted views with visible-turn counts 1/2/3/4 and locked-future counts 3/2/1/0;
- 0 exact or normalized text reuse against all 24 B2 user turns;
- every content SHA-256, session boundary and ID uniqueness check passed;
- 8 verifier tests passed in 0.11 seconds, including tampered hash, session, call count, parent reuse
  and forbidden answer/evaluation payload controls;
- 0 annotations created or accessed, 0 generation calls, 0 network calls and 0 paid calls;
- `git diff --check` passed.

## Evidence boundary

Freezing inputs before outputs prevents tuning to their observed generations, but the author is still
the implementation task and the scenarios were created after B31. This is prospective developer
evidence, not an independent human sample, blind formal holdout or proof of generalization. The
source cannot be edited after this freeze. Generation requires a separate no-retry contract and
release; annotations must remain absent until outputs are immutably locked.
