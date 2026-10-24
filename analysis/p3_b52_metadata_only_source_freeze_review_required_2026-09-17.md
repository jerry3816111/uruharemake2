# P3-B52 metadata-only source freeze · REVIEW_REQUIRED

Date: 2026-09-17

## Outcome

**Source selected: no. Selection receipt: absent. Content/outcome access: zero. Model calls: zero.**

The selection mechanism itself passed its deterministic and adversarial tests, but both prospectively frozen live metadata transports failed before eligibility or ranking could run.

1. V1 flat playlist: the first sanitized row had no duration or publication date. It failed closed with `duration_seconds_not_integer; invalid_date:published_at`.
2. V2 full metadata with six allowlisted stdout columns: `yt-dlp` exited with status 1. The privacy boundary intentionally did not persist raw page data, titles, descriptions, or stderr diagnostics.

The V1 failure was committed before V2 was frozen and executed. V2 allowed exactly one additional attempt. There will be no automatic third retry, seed change, favorable candidate selection, content preview, or weakening of the eligibility rules.

## What is valid despite the failure

- Seven already tracked official-channel video IDs are frozen out of eligibility.
- The candidate date window, duration range, official channel, public completed-livestream requirement, seed, score, and winner rule were fixed before either respective attempt.
- Synthetic and adversarial evidence covers deterministic order independence, forbidden content/popularity fields, changed candidates, changed seed, empty sets, known sources, wrong channels, non-stream uploads, binding drift, V1 freeze, and V2 single-variable transport repair.
- The B51 temporal experiment remains unchanged; no M55/M56 artifact was edited or executed.

## Minimum counterexample

The official streams surface can enumerate at least one ID under the V1 transport, but that row lacks two required eligibility fields. The V2 extractor, which was supposed to resolve those fields while printing only allowlisted metadata, terminated before producing an authorized candidate set. Therefore the current obstacle is source-metadata transport, not the deterministic selector and not the forecasting model.

## Design-review options

### A. Official YouTube Data API

Use `search.list` or playlist items for IDs/dates and `videos.list` for duration/live metadata, writing only the same allowlisted fields. This is the cleanest structured transport but requires a user-supplied API credential/quota and a separately frozen V3. No key is currently available or requested.

### B. Sanitized external manifest

A trusted source coordinator supplies only the eight allowed candidate fields with a signed/hashable provenance record. This avoids platform extractor drift but adds a human data-preparation dependency and must not include titles or content.

### C. RSS-first source-ID freeze, recommended if no API credential is available

Use the official channel Atom feed only for channel ID, video ID, and published date. Select one ID with the unchanged seed and score, then perform a **post-selection, no-replacement** metadata eligibility check for duration and completed-livestream status. If that one source is ineligible or unavailable, retain failure; do not choose the next-ranked candidate. This preserves content blindness and avoids favorable case shopping, but it changes the order of eligibility versus selection and therefore requires a new preregistered V3 rather than an unrecorded retry.

## Claim boundary

B52 does not provide a fresh source, temporal row, prediction, outcome, or evidence that UruhaBrain beats a baseline. It provides a tested selector and a retained negative result showing that the current metadata transport is insufficient. The project remains at `0 formal model calls / 0 target outcome access / no formal result` for this gate.

