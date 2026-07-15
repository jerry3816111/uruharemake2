# V52 precise target-mention development result

This is a matched comparison on consumed development data, not fresh generalization evidence.

| condition | parse | commitment | requested P/R | call exact | false actions | median / p95 |
|---|---:|---:|---:|---:|---:|---:|
| v51_event_map_control | 100.0% | 88.5% (54/61) | 100.0% / 94.3% | 95.8% (46/48) | 0 | 2.48s / 5.53s |
| precise_target_mentions_candidate | 100.0% | 90.2% (55/61) | 100.0% / 97.1% | 97.9% (47/48) | 0 | 2.46s / 5.78s |

- Mention coverage/fallback/overlap: `66/66` / `0` / `0`.
- Commitment delta: `+1` targets.
- Exact-call delta: `+1` cases.
- False-action delta: `+0` cases.
- Semantic fixes/regressions: `1` / `0`.
- Call fixes/regressions: `1` / `0`.
- Development gate passed: `True`.
- Decision: `authorize_fresh_v52_holdout_construction`.
- Interpretation: Separating exact target mentions from broad predicate evidence passed every locked development gate without encoding a commitment answer. The result authorizes only a separately frozen external or human-authored holdout.
- Runtime and physical VRM execution remain unchanged.
