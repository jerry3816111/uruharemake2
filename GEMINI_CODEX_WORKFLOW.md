# Gemini x Codex Workflow

## Purpose

This repository now uses a split execution model to reduce Codex token consumption.

- Gemini: primary implementation worker
- Codex: acceptance reviewer, regression verifier, and final gate

The default rule from this point forward is:

1. Codex defines the next task precisely.
2. Gemini performs the implementation.
3. Gemini writes a handoff record.
4. Codex reviews, reruns focused checks, and either accepts or rejects.
5. Only after acceptance does Codex write the final engineering note and commit.

Codex should avoid doing the implementation itself unless one of these is true:

- a production-breaking issue must be fixed immediately
- Gemini is blocked on an architecture decision
- Gemini's patch is structurally wrong and a minimal surgical fix is faster than another full round-trip

## Role Split

### Gemini owns

- routine implementation work
- UI plumbing and component additions
- report script additions
- batch workflow features
- repetitive refactors
- file generation and report regeneration
- first-pass local checks
- writing detailed implementation notes into the exchange log

### Codex owns

- defining task boundaries and acceptance criteria
- architecture consistency checks
- regression and smoke verification
- reviewing diffs for logic errors or hidden coupling
- deciding whether a patch is accepted or returned
- final commit after acceptance
- maintaining the review standard and project direction

## Standard Delivery Cycle

### Phase 0: Task Definition by Codex

Codex writes a task packet before Gemini starts.

The task packet must include:

- objective
- exact files likely to change
- non-goals
- acceptance checks
- known risks
- whether a git checkpoint is required after acceptance

Codex should write this into `URUHABRAIN_EVOLUTION_LOG.md` before the user switches to Gemini.

### Phase 1: Implementation by Gemini

Gemini performs the task and should keep scope tight.

Gemini must avoid:

- changing architecture outside the assigned packet
- silently rewriting unrelated files
- changing evaluation meaning without documenting it
- committing broad cleanup unrelated to the assigned work

### Phase 2: Handoff by Gemini

After implementation, Gemini must append a handoff note to `URUHABRAIN_EVOLUTION_LOG.md`.

The handoff note must contain:

- date/time and signature
- changed files
- what was implemented
- commands run
- outputs or metrics produced
- known risks / unresolved issues
- exact point where Codex should verify

Minimum handoff format:

- task name
- changed files
- validation run
- expected acceptance result
- open issues

### Phase 3: Acceptance by Codex

Codex does not continue feature work immediately.
Codex first performs acceptance only.

Acceptance checklist:

1. read Gemini's handoff note completely
2. inspect the touched files only
3. run focused verification, not broad unrelated work
4. verify outputs/reports/ui states match the stated result
5. decide one of:
   - accept
   - reject with requested fixes
   - accept with follow-up debt recorded

### Phase 4: Outcome

If accepted:

- Codex appends an acceptance note to `URUHABRAIN_EVOLUTION_LOG.md`
- Codex creates the commit
- Codex defines the next task packet for Gemini

If rejected:

- Codex does not implement the whole feature itself
- Codex writes a rejection note listing exact required fixes
- user switches back to Gemini with that rejection note as the task source

## Acceptance Criteria Template

For each task, Codex should define acceptance in this structure:

- functional: what must work
- UI/report: what must appear
- data: what files or outputs must be regenerated
- safety: what must not regress
- proof: exact commands or smoke checks to run

Example:

- functional: batch review bucket can filter drafts by failure type
- UI/report: Human Annotation panel shows bucket selector and preview
- data: annotation draft queue and unified summary regenerate successfully
- safety: no direct write to annotations happens unless accept action is triggered
- proof:
  - `python3 build_annotation_draft_queue.py`
  - `python3 build_unified_eval_summary.py`
  - targeted Gradio smoke import

## Task Types and Default Owner

### Gemini-first tasks

These should normally go to Gemini first:

- web UI features
- report generation scripts
- dataset plumbing
- markdown/report formatting
- automation around annotation/regression loops
- repetitive logic extension on existing modules

### Codex-first tasks

These stay with Codex unless explicitly delegated after scoping:

- architecture redesign
- benchmark interpretation changes
- evaluation metric definition changes
- memory/planner/right-brain coupling decisions
- acceptance review and release gatekeeping

## What Gemini Must Provide for Every Implementation Round

Gemini should always leave behind:

- exact file list
- why each file changed
- commands run
- whether outputs were regenerated
- whether commit is recommended
- what Codex should inspect first

## What Codex Must Not Do Under This Mode

To preserve tokens, Codex should not:

- proactively continue implementation after acceptance unless asked
- redo the same feature Gemini already completed
- run broad full-suite validations if focused checks are enough
- expand scope during review unless a real regression is found

## Escalation Rules

Switch back to Codex immediately when any of these happen:

- Gemini changed architecture beyond scope
- Gemini touched unrelated files
- evaluation semantics changed unexpectedly
- smoke passes but logic appears incoherent
- regression metrics conflict with the implementation claim

## Recommended Working Rhythm

1. User asks Codex for the next step.
2. Codex writes a task packet for Gemini.
3. User switches to Gemini and asks it to execute exactly that packet.
4. Gemini implements and writes handoff.
5. User switches back to Codex.
6. Codex only reviews and accepts/rejects.
7. Repeat.

## Immediate Rule For This Repository

From this point on, for ordinary feature work:

- Gemini executes
- Codex reviews
- Codex commits only after acceptance

This is now the preferred operating mode unless the user explicitly overrides it.
