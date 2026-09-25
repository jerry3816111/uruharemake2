# P4-AU first implementation batch: FAIL

The first implementation run against the already frozen 16-case dataset failed before product integration. It linked `4/6` fresh positives and incorrectly added the prior source in `3/9` controls. The dataset and gates remain unchanged.

The failure is useful because it identifies four distinct boundary problems rather than a score to tune:

- a direct Japanese user statement with an omitted pronoun was treated as not belonging to the user;
- M47 task refs were not split finely enough to separate action feedback from a new current task;
- a metalinguistic prior passed the P4-AH trigger because the existing P4-AT direct-source guard was not composed into P4-AU;
- the expired-receipt fixture changed a derived field that M44 correctly recomputed, so it was not actually expired.

One informed correction batch is authorized: compose those existing guards, split refs before classifying them, allow bounded Japanese subject ellipsis only for a direct non-third-party/non-meta user turn, and change the authoritative receipt `created_turn` in the fixture. No dataset, gate, prompt, M39/M45 check, candidate score, factual memory, or visible-language rule may change.
