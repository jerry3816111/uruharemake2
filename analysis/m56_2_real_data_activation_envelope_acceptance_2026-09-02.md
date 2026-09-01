# M56.2 Formal Real-Data Activation Envelope Acceptance · 2026-09-02

## Decision

**Activation-control engineering gate: PASS. Current formal activation: DENIED. Formal M56 result: ABSENT.**

M56.1 made the Equation fit/state/transition artifacts genuine and content-addressed, but the frozen
capsule still intentionally rejected real data.  M56.2 adds the missing prospective real-data path and
places one live gate in front of it that the public API cannot bypass through caller-supplied readiness.
A packet that merely looks like 30 real rows can now
build only pending mechanics; it cannot obtain an activation receipt unless the standard V7, V9, and M55
evidence on disk passes at that moment.

The frozen M54–M56.1 files were not modified.

## What changed

### Live evidence rather than caller assertion

The public audit API has no `readiness` argument.  It reads the standard V7 ledgers, frozen reliability
lock, V9 result, and supplied private M55 compilation through the existing readiness audit.  A caller
cannot pass `m56_authorized=true` to bypass the two-human chain.

### Prepared real-data mechanics

After the live gate eventually passes, the controller can:

1. split the private 30-row compilation into a prediction packet and a separately stored outcome key;
2. capture the local `qwen3.5:9b` manifest, Ollama version, OS, CPU, architecture, and memory;
3. create a same-model run manifest for B0–B5/Ours;
4. construct 30 × 7 = **210** condition-separated prediction tasks;
5. construct 30 fit + 30 state + 30 transition = **90** real pre-outcome Equation artifacts;
6. bind all content, dependencies, runtime, layout, packet, outcome-key hash, and resource rules into one
   activation request.

Every artifact remains `pending_activation`; none of these shapes alone authorizes a call or result.

### Four private compartments and one-use receipt

Formal artifacts must live under the Git-ignored
`analysis/local_m56_formal_execution_v1/<run-id>/` in four non-overlapping directories:

- `generation`: packet, manifest, capsule, runtime snapshot, and Equation artifacts;
- `commitments`: activation request, short-lived receipt, and later prediction commitment;
- `scoring`: private outcome key and split report;
- `telemetry`: actual CPU, prompt/completion token, latency, memory, and sensitivity evidence.

The receipt authorizes only one complete no-retry generation run for 30 minutes.  It does not authorize
scoring before commitment, a scientific result claim, production-memory writes, or deployment.  Atomic
lease creation prevents a consumed receipt from being used again.

This is an application-level fail-closed boundary, not a cryptographic trust boundary against an attacker
who can rewrite the code and all files on the same computer.  Hashes expose drift under the frozen runner;
they are not digital signatures.

## Fail-closed evidence

The focused suite covers:

- no caller-supplied readiness parameter;
- current live denial and zero receipt/model call/outcome access;
- Git-ignored private layout and rejection of shared/outside paths;
- exact live model-manifest and hardware binding;
- synthetic rehearsal using a different schema and never authorizing formal execution;
- a deliberately forged 30-row real-shaped packet that can create pending mechanics but cannot satisfy
  the live gate;
- outcome-key injection, capsule/bundle tampering, stale dependency, wrong model artifact, expired receipt,
  consumed receipt, excess scoring authority, and write-before-gate attacks;
- graphical read-only rendering with no form submission.

The forged packet is test-only, in memory, and explicitly has no human provenance.  It is useful because
it demonstrates that a structurally valid packet still cannot replace the authoritative human chain.

## Tests and resources

- focused M56.2 suite: **13/13 passed**;
- direct M54–M56.2 compatibility suite: **123/123 passed**;
- selected M1/M2/V7/V9/M54–M56.2 compatibility suite: **188/188 passed**;
- Python compilation: PASS;
- contract and ten frozen dependency bindings: PASS;
- implementation freeze: PASS;
- formal model calls: **0**;
- generation target-outcome access: **0**;
- production-memory writes: **0**;
- formal result: **not created**;
- activation contract hash:
  `0a449537e9db629c579bd7f7240f9c06dc4895289a94a276dee6978207bd77ab`;
- dependency-set hash:
  `ca074573da1f72145cd18f69d2fdea4161b80884cb8bc939f2206bc36cc4f078`;
- local qwen3.5:9b manifest SHA-256:
  `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`;
- current audit hash:
  `5c31289d6cb20e8ebf2cc74fc79871157add6d8fb4fcb696e048d95542504913`.

The first expanded test invocation used Python 3.14 without the repository's pytest installation and
therefore produced seven import-environment errors.  It was not counted as a code result.  Re-running the
same scoped files with the existing Python 3.12 pytest environment produced the 123/123 and 188/188
results above.

## Safari graphical acceptance

Safari reused the existing M56.1 local tab and navigated it to
`http://127.0.0.1:7910/dashboard`.  Safari remained at **29 tabs**; no tab was created or closed and no
form was submitted.

The page visibly showed:

1. four human/data gates waiting at `0/18 + 0/18`, `0/30`, and `0/30`;
2. model/hardware binding and the private four-compartment layout passing;
3. `M55 human rows → M56.2 activation → one formal M56 run`;
4. the outcome key isolated in the private scoring compartment;
5. the exact local qwen manifest hash and an explicit synthetic-rehearsal boundary;
6. `DENIED NOW`, zero formal calls, and no formal result rather than a misleading green completion card.

The desktop-width page rendered without visible horizontal overflow.  Evidence:

- `analysis/m56_2_safari_activation_gate_overview_2026-09-02.png`
- `analysis/m56_2_safari_activation_compartments_boundary_2026-09-02.png`

The local page is read-only and can be safely closed; it does not hold the private data or activation
state.

## Exact remaining boundary

Current authoritative state remains:

- V7 independent ledgers: **0/18 and 0/18**;
- V7 reliability: **not passed**;
- V9 independently reviewed Uruha events: **0/30**;
- V9 human coders: **0**;
- real M55 temporal rows: **0/30**;
- formal activation receipt: **absent**;
- formal M56 model calls: **0**;
- formal M56 result: **absent**.

M56.2 closes the unsafe transition from engineering fixtures to a future formal run.  It does not add
human evidence or a model score.  The next non-substitutable dependency is still two different humans
completing V7.  Until that chain passes, this work cannot support real-person predictive validity,
Equation V1 validity, Ours superiority, private mental truth, a solved human-brain equation, full-pipeline
readiness, or production readiness.
