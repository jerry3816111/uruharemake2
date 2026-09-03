# M56.12 Outcome-Derived Artifact Containment and Public Projection Plan

Date: 2026-09-03
Status: prospective engineering contract; frozen before implementation and before any real M56 target-outcome access
Single changed variable: public projection boundary for private outcome-derived scoring artifacts

## Problem proved before the change

M56.10 correctly stores its full score report inside a private full-sync checkpoint. Existing live dashboards show
only global, pre-formal zeros and do not accept a run id. There is no sanctioned run-specific operation that can
show a scoring run's progress without handing a renderer, logger or telemetry producer a private checkpoint/report.

An isolated forged 30-row run demonstrated the sensitivity of the naive workaround. Serializing the checkpoint plus
canonical report emitted 57,024 UTF-8 bytes, 60 sample-id occurrences, 60 primary pair-record occurrences, 14
condition-metric blocks, three outcome-key-hash occurrences and two decisions. This is retained in
`analysis/m56_12_prechange_naive_private_projection_probe_2026-09-03.json`. No deployed leak was observed, and no
real outcome was read.

## Single attributable change

Add a new run-id-only public projection module around the unchanged M56.10 private state. It validates the private
state internally, then creates one exact allowlisted state-only projection. Dashboard, log and telemetry views must
all derive from that same projection and accept no checkpoint, report, result, metric, decision or readiness input.

The projection may reveal only:

- a coarse frozen phase;
- booleans for mode, intent, checkpoint, canonical report, result commitment and terminal failure;
- whether a result artifact exists, never its decision or score;
- zero retry/fallback policy;
- explicit redaction policy and evidence boundary;
- a hash of this already-public projection.

It must not reveal the run id, artifact hashes, dataset/prediction identifiers, sample ids, pair rows, metrics,
reliability bins, labels, decision, source text, raw output or reasoning. Existing private artifacts and formal
scoring semantics do not move or change.

## Frozen phases

1. `pre_outcome_not_started`: valid M56.8 run, no M56.10 state;
2. `pre_outcome_mode_committed`: valid mode but no join intent;
3. `private_join_incomplete_unknown_access`: intent without checkpoint/failure; public view cannot claim whether the
   answer was opened;
4. `terminal_ambiguous_no_result`: validated terminal failure, no checkpoint/report/result;
5. `private_checkpoint_committed`: valid checkpoint, canonical report not yet committed;
6. `private_report_committed`: valid checkpoint/report, result commitment not yet committed;
7. `formal_result_committed`: valid checkpoint/report/result commitment; public decision and metrics remain redacted.

Any impossible ordering, mutation, checkpoint/report mismatch, malformed projection or forbidden key fails closed.

## Frozen success conditions

- all public functions accept only `run_id`; no private artifact/projection injection exists;
- completed forged state maps to `formal_result_committed` and all partial/terminal states map correctly;
- projection, canonical log record, telemetry record and HTML contain zero forbidden keys and zero unique private
  canary values from the checkpoint/report;
- the public schema excludes raw run id, all private hashes, metrics, decisions, sample/pair/label content;
- dashboard/log/telemetry are byte-consistent projections of the same validated state;
- mutating a private artifact or public projection fails closed rather than showing partial content;
- frozen M56.10 semantics/hashes and prior compatibility tests remain unchanged;
- output-size and validation-time costs are measured on forged data and not called production throughput;
- a read-only graphical page explains the private-to-public membrane and current scientific denial.

## Evidence boundary

M56.12 can establish a cooperative allowlisted projection for the sanctioned local application path. It cannot stop
same-host code with direct filesystem or old-API access, replace OS permissions/encryption, prove that every future
UI/log/telemetry consumer uses this API, or establish a historical production leak. It adds no human label, real
temporal row, target-outcome access, model-performance result, Equation V1 validation, solved human-response
equation, full-pipeline evidence or production authorization.
