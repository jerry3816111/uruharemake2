# M34 Counterfactual Pragmatic Branch Ledger — Acceptance

Date: 2026-08-25  
Decision: **PASS — all frozen gates**

## What M34 adds

M34 makes one previously implicit part of the desired-response equation explicit and falsifiable:

`same current utterance + verified reversible interaction context -> candidate response branches -> selected branch + bounded alternative -> observable next-turn prediction -> support / contradiction / unknown -> non-rewriting revision`

The ledger separates the literal current signal from inferred communicative goals. It records only typed, reversible interaction evidence; it does not write a guessed emotion, need, or private intention as a factual long-term memory.

## Controlled intervention

- 8 isolated cases arranged as 4 counterfactual pairs in Chinese, English, and Japanese.
- Within each pair the current utterance is byte-identical.
- The intervention changes only the previously requested and subsequently supported response form.
- Every case then supplies one actual next turn that supports, contradicts, or leaves the selected branch uncertain.
- Reserve SHA-256: `e5b8bc9a8e219639d751fa78009ad6db201735b951c81053ac028fc2cbbc6d26`.
- Protocol SHA-256: `39ecbfe63e63a7287c2c08c9184f287d9e030726d1248da72c172e335bf31829`.
- Implementation was frozen first; freeze SHA-256: `c142d0af75e25f8d0eb461e608c2c0ae1b3684aba763c5b128e1af3f54cecbed`.
- The sealed reserve was executed exactly once and preserved at `analysis/m34_counterfactual_pragmatic_branch_reserve_raw_2026-08-25.json`.

## Frozen result

| Measure | Result |
|---|---:|
| Selected policy accuracy | 8/8 (100%) |
| Selected mode accuracy | 8/8 (100%) |
| Counterfactual pair divergence | 4/4 (100%) |
| Current-literal invariance | 4/4 (100%) |
| Verified context evidence trace | 8/8 (100%) |
| Candidate + bounded alternative trace | 8/8 (100%) |
| Observable next-turn prediction trace | 8/8 (100%) |
| Next-turn outcome verification | 8/8 (100%) |
| Contradiction replacement | 3/3 (100%) |
| Selected branch reaches visible surface | 8/8 (100%) |
| Visible Japanese replies | 16/16 (100%) |
| Unverified mental-fact writes | 0 |
| Raw dialogue/model-output writes to adaptive ledger | 0 |
| Median / p95 per four-turn case | 0.3503s / 0.3590s |

Observed outcomes were 3 supported, 3 contradicted with the expected replacement branch, and 2 uncertain topic-shift cases. No contradicted case rewrote its original evidence.

## Concrete Safari sequence

1. User: `下次我說思緒轉個不停，給我方法。`
2. User confirms: `沒錯。`
3. User: `今晚腦子又停不下來了。`
4. UruhaBrain: `最初の一個だけ決めよ。いま頭に浮かんでることをメモして、五分だけそこから離れればいい。`
5. User rejects that branch: `不是，我現在不要方法，只要聽我說。`
6. UruhaBrain: `あー、そこ読み違えた。方法は出さないから、そのまま話して。`

The graph showed `verified_reversible_context`, then `contradicted`, and finally `solve_regulation -> listen_presence`. The run used `/tmp/uruha-m34-safari.0UeQW1`; it did not write to the formal memory database.

Screenshots:

- `analysis/m34_safari_verified_branch_graph_2026-08-25.jpeg`
- `analysis/m34_safari_contradiction_revision_graph_2026-08-25.jpeg`
- `analysis/m34_safari_comparison_and_revision_2026-08-25.jpeg`
- `analysis/m34_safari_sealed_result_strip_2026-08-25.jpeg`

## Evidence boundary

This result supports a bounded engineering claim: UruhaBrain can use verified interaction history to distinguish different desired-response branches for the same current wording, expose an observable prediction, and revise after real feedback.

It does **not** establish access to private intent, human-equivalent understanding, mind reading, human preference, a complete human-brain equation, or superiority to a same-model direct-generation baseline. M35 must test the last comparison under controlled same-model conditions.
