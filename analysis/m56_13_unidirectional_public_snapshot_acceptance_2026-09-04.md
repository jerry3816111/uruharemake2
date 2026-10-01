# M56.13 Unidirectional Public Snapshot Boundary — Acceptance

Date: 2026-09-04

Decision: **PASS as a bounded engineering milestone; M56 formal science remains denied**

Single changed variable: public consumers' data capability, from direct private-state validation to public-snapshot-only reads

## Problem and frozen change

M56.12 already removed private fields from its output, but each sanctioned dashboard, log and telemetry call still
imported private M56 modules and invoked the private-state loader. The retained pre-change probe disabled that loader:
all 3 consumers became unavailable, the loader was called 3 times, and the consumer module had 4 private M56 imports.
No output leak was observed; this proved retained capability and repeated validation only.

M56.13 splits the path into two roles without changing scoring, metrics, decisions or the M56.12 projection:

1. `export_public_scoring_snapshot(run_id)` validates the complete private state once, creates a random 128-bit id,
   and full-sync writes one immutable `0600` allowlisted snapshot to a separate public root;
2. the standalone reader accepts only `snapshot_id`, imports no M56 module and supplies projection, log, telemetry and
   HTML entirely from that snapshot.

The prospective contract was frozen before implementation and before any real target-outcome access. The
implementation freeze binds the plan, contract, exporter, reader, tests and forged evidence.

## Retained implementation failure

The first rehearsal wrapped `build_public_scoring_projection` to count calls. That mock changed the callable signature,
and the frozen M56.12 contract correctly rejected it with
`public_api.signature:build_public_scoring_projection`. The contract was not loosened. The measurement was moved to
the internal `_load_validated_private_state` boundary, leaving the public function and its signature unchanged.

## Measured result

| Measure | Before M56.13 | After M56.13 |
|---|---:|---:|
| Public surfaces usable with private loader/root disabled | 0/3 | 4/4 fresh child processes |
| Private validations for one export and all public reads | 3 for three M56.12 surfaces | 1 during export; 0 in children |
| M56 private imports in public consumer | 4 | 0 |
| Private-root permissions during public reads | required | `000` |
| Snapshot id | run-specific API | random 32-character lowercase hex |
| Public snapshot files in rehearsal | none | 1 immutable `0600` file |
| Public snapshot size | not applicable | 1,954 UTF-8 bytes |
| Projection/log/telemetry equality | same validated projection, repeated private reads | byte-identical public projection |
| Private canary hits | 0 in M56.12 output | 0 across four child outputs |
| Model calls / real target-outcome reads | 0 / 0 | 0 / 0 |

The actual rehearsal used a temporary forged 30-row completed scoring run. It changed the private root to mode `000`
before launching four fresh Python processes. Projection, log, telemetry and HTML all exited 0; all children were
reaped; stderr was empty; the export receipt had no forbidden public key.

## Cost

Seven independent forged rehearsals were retained:

- median validated snapshot export: **0.145821 s**;
- median four fresh public children: **0.151264 s**;
- median complete forged rehearsal: **1.307229 s**;
- observed complete range: **1.300077–1.314878 s**;
- every run: 1 private validation, 4 public processes, 1,954-byte snapshot, 0 private-canary hits.

These are local temporary harness costs. They are not formal-model latency, production throughput or a hostile-user
security benchmark.

## Verification

- focused M56.13: **10/10 passed**;
- direct M54–M56.13: **268/268 passed**;
- selected M1/M2/M6/V7/V9/M54–M56.13 compatibility: **333/333 passed**;
- Python compile, JSON validation, dependency/freeze hashes and `git diff --check`: passed;
- file guards cover malformed/traversal ids, hash/content mutation, forbidden-field injection, symlink, hard link and
  group/world permissions;
- public root nested inside the private run root is rejected before export.

These are selected suites, not a claim that every historical repository test was run.

## Safari graphical acceptance

Safari reused the existing M56.12 test tab and navigated it to `http://127.0.0.1:7921/dashboard`. Tab count remained
33 before and after; no user tab was closed or created. The page visibly showed:

- `PRIVATE EXPORTER → IMMUTABLE SNAPSHOT → PUBLIC READER`;
- before `0/3` consumers with the private loader disabled;
- after `4/4` fresh children with private root mode `000`;
- 1 private validation, 0 private imports and 0 canary hits;
- `DENIED NOW · 0 REAL OUTCOME READS` and the full evidence boundary.

No form or visible horizontal overflow was observed. The local server was stopped after acceptance; the remaining
read-only tab is safe to close. Evidence:

- `analysis/m56_13_safari_unidirectional_snapshot_top_2026-09-04.png`
- `analysis/m56_13_safari_unidirectional_snapshot_boundary_2026-09-04.png`
- `analysis/m56_13_safari_unidirectional_public_snapshot_acceptance_2026-09-04.json`

## Evidence boundary and next milestone

M56.13 establishes only that the supplied public consumer can operate from a validated immutable snapshot without
importing or reading M56 private state. The processes still share one OS user; content hashes do not authenticate a
malicious writer; a crash after snapshot creation can leave a safe orphan; snapshot revocation/latest lifecycle is
absent; other same-host programs or old APIs are not physically prevented from reading private files.

It adds no human data, real outcome access, model performance, Equation V1 validity, solved human-response equation,
full-pipeline value or production authorization. Authoritative science remains V7 `0/18 + 0/18`, V9/real temporal
rows `0/30`, formal calls/outcome/result zero or absent.

**M56.13 closes the M56 decimal hardening chain. There will be no M56.14.** The next research milestone is M57:
outcome-blind, component-level error localization for perception, retrieval, state, decision and realization. Its
protocol and harness may be prepared without future answers, but a formal M57 conclusion requires an authorized M56
result and cannot be fabricated while the two-human data gate is empty.
