# M56.13 Unidirectional Public Snapshot Boundary Plan

Date: 2026-09-03
Status: prospective engineering contract; frozen before implementation and before any real M56 target-outcome access
Single changed variable: public consumers' data capability, from direct private-state validation to public-snapshot-only reads

## Problem proved before the change

M56.12 correctly redacts its outputs, but its dashboard, log and telemetry functions each call the private-state
validator. When that validator was disabled, all three surfaces failed and it was called three times. The consumer
module also imports four private M56 scoring modules. M56.12's three-surface forged cost was 0.433071 seconds because
the full private state was independently revalidated three times.

This is retained in
`analysis/m56_13_prechange_public_consumer_private_capability_probe_2026-09-03.json`. It proves retained capability
and repeated reads, not a data leak.

## Single attributable change

Split publication into two roles:

1. a private exporter calls the unchanged M56.12 validator exactly once and full-sync writes only its safe
   projection as an immutable randomly named snapshot in a separate configured public compartment;
2. a standalone public reader imports no M56 Python module, accepts only a 128-bit random snapshot id, validates the
   snapshot/projection hashes and allowlists, and supplies dashboard/log/telemetry without private-root access.

The export receipt may reveal the random public snapshot id and public hashes, never run id, private artifact name,
metric, decision, sample, label or source. Snapshot ids are not derived from run ids. Each export is immutable and
one-shot; automatic latest pointers, replacement and orphan recovery are outside this version.

## Frozen success conditions

- exporter API accepts only `run_id`; public APIs accept only `snapshot_id`;
- public reader source imports no M56 module and has no private-root parameter or environment dependency;
- snapshot id is 32 lowercase hex characters from `secrets.token_hex(16)`, not derived from run id;
- public root is outside the private run root; snapshot is a regular, same-owner, single-link, non-symlink file with
  no group/world permissions;
- exporter validates M56.12 private state once, writes exactly one safe projection, and returns no private value;
- after private-root permissions are removed, fresh child processes can load projection, produce log/telemetry and
  render HTML from the snapshot; no private canary appears;
- projection, log and telemetry remain byte-identical; dashboard derives only from the validated projection;
- tampered snapshot/hash, traversal/symlink/hard-link, malformed projection and injected private field fail closed;
- frozen M56.12/M56.10 behavior and selected compatibility tests remain unchanged;
- process-launch, export, read and output-byte costs are reported as forged harness costs;
- graphical page explains the one-way boundary and current scientific denial.

## Known deliberate limits

- processes still run as the same OS user; this is capability reduction by code/data path, not a hostile-user sandbox;
- public snapshot integrity uses content hashes, not a secret signature, so a malicious same-host writer is outside
  the claim;
- a crash after snapshot write but before receipt return can leave a safe orphan;
- random immutable snapshots have no revocation/latest lifecycle in M56.13;
- the exporter still requires private access, while public consumers do not.

## Evidence boundary

M56.13 can establish that the provided standalone public consumer operates from an immutable allowlisted snapshot
without importing or reading M56 private state. It cannot prevent other same-host programs from reading private
files, prove OS-user isolation, authenticate against a malicious writer, guarantee every future consumer uses this
reader, or add human evidence, real outcome access, model performance, Equation V1 validity, solved human-response
equation, full-pipeline value or production authorization.
