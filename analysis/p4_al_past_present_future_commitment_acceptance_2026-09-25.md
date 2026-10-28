# P4-AL past-present-future commitment acceptance

## Decision

**PASS for the deterministic temporal mechanism. Real-person predictive
validity remains unproved.** The data, temporal definitions, upstream hashes,
failure boundary, and metrics were committed at `6a38ac4` before the new
implementation was executed. The frozen three-case gate passed on its first
execution; no informed correction was used.

## What “past, present, future” now means operationally

1. **Past** is a set of provenance-bearing observations with an
   `observed_turn` strictly earlier than the present. Supported, revoked, and
   unknown evidence remain distinct.
2. **Present** contains the current input digest, the exact P4-AG
   prediction/ledger identity, six competing response-action hypotheses, and
   an explicit split between known, inferred, and unknown. Candidate scores
   are action rankings, not probabilities of a person's private state.
3. **Future** is the next linked user-turn outcome. The selected operational
   action and all candidates are SHA-256 committed while the outcome remains
   locked. Support, contradiction, and unrelated/unknown are the only accepted
   outcome classes.
4. **Transition** occurs only after later evidence is identity-bound to the
   commitment. The observation becomes a provenance-bearing record available
   to a later turn; it is not promoted into a factual claim about private
   desire.

This is the smallest executable form of the proposed loop:

```text
past evidence (< t)
       ↓
present observable state + competing action hypotheses (t)
       ↓ SHA commitment; outcome unavailable
future linked outcome (> t)
       ↓ support / revoke / unknown
new provenance-bearing past evidence for the next cycle
```

## Frozen evidence

- strict past-before-present order: `3/3`
- future outcome absent before commitment unlock: `3/3`
- six present candidates: `3/3`
- stable commitment hash and exact prediction identity: `3/3`, `3/3`
- support / contradiction / unknown transitions: `1/1`, `1/1`, `1/1`
- unknown counted as success: `0`
- outcome converted into a next-cycle evidence record: `3/3`
- modified commitments rejected: `3/3`
- raw/private content, visible reply, model call, factual-memory write: `0/0/0/0`
- graph-ready past/present/future node appears before `utterance` in the
  contract test.

## Why this is academically stronger than an output-only demo

The claim is falsifiable at each boundary. A case fails if history is not
strictly earlier than the present, if future evidence appears before the
prediction hash, if the later result belongs to a different prediction, if an
unknown is counted as success, or if a committed prediction is changed after
the fact. This follows the already frozen M55 temporal-boundary and M56
commit-before-outcome principles while connecting them to the product's P4-AG
correction ledger.

It also preserves the P4-AK negative result. P4-AL does not relabel that chain
as passing; the P4-AK failure artifact is a content-addressed dependency of the
new contract.

## Current evidence hierarchy

The repository already contains a working temporal observatory and limited
public-video development evidence, but the levels remain separate:

- the original M1 synthetic instrument can display history, cutoff, hidden
  future, probability scores, calibration, and resource cost;
- B68 has four same-source development-proxy rows: system and baseline each
  had `1/4` top-1 hits, while the system had lower mean Brier (`1.01340` versus
  `1.17095`);
- B72 found the automatic-caption proxy inadequate for a system-advantage
  claim across eight rows and two sources;
- independently reviewed real temporal rows remain `0/30`; human reliability
  ledgers remain `0/18 + 0/18`.

Therefore the new defensible claim is a **tamper-evident temporal mechanism**,
not accurate prediction of Uruha or humans. The next product milestone must
deliver this three-slice node from an isolated real runtime/Safari session.
The next scientific milestone still needs a valid response target and
independent real temporal data before forecasting accuracy can be claimed.
