# P4-B dotenv import-effect guard — prospective scoped freeze

## Before evidence and scope

At HEAD `2c967271c1327163e921d1d3fea11cdbb985fffb`, the fixed B child
validates its launch environment before Web import. `uruha_brain_mac.py` then
calls `load_dotenv()` unconditionally at module import, before its configuration
globals are read. `python-dotenv` may find a `.env` next to this module or in
an ancestor and add previously absent variables. The B receipt hashes only
the fixed B/isolation keys, not arbitrary later-added model/config keys. The
current worktree and inspected ancestors have no `.env`; this is a reachable
import-effect gap, not evidence of a past B Send or external call.

The first new variable is only `B-intent dotenv suppression`: when *any*
case-insensitive `URUHA_P4_B_` key exists, including malformed intent, Brain
must not invoke `load_dotenv`. For non-B imports it must retain exactly one
ordinary `load_dotenv()` call. Do not change B environment/receipt schema,
model selection, token counter, prompt, baseline, formal data, or frozen
historical source. The B child bootstrap remains the authority for malformed
intent and fails it closed separately.

Allowed changes: `uruha_brain_mac.py`, one focused source-contract test,
this freeze, one result note, and `CURRENT_TASK.md`. Source manifest v5 already
includes Brain and therefore must detect the changed committed bytes without
changing its file set or digest algorithm.

## Predeclared checks and limits

1. Focused red-before/green-after test executes the exact module-level dotenv
   decision from Brain's AST in isolation with a fake loader: valid B and
   malformed/lowercase B each call it zero times; non-B calls it once. Test
   also requires the function to be invoked once in the module import flow.
2. Run B manifest/binding/bootstrap/controller adjacent tests, Python compile,
   `git diff --check`, and a committed HEAD read-only 239-file snapshot after
   scoped commit. Any unexpected source drift or regression is retained as a
   failure; no assertion is relaxed to chase green.
3. Zero model, provider, Web, Safari, DB, download and external deployment.
   Tests are source/contract evidence only. The previously failed real Ollama
   identity probe is not retried.
4. Review changed paths and preserve unrelated `output/graduate_application_report/`.
   Commit/push only scoped files and verify PR #435 exact head.

This closes only one ambient import-time configuration route. It does not
prove third-party/data-asset closure, a same-model B prompt-token bound, B
terminal delivery, real daemon/runner identity, 20-second Safari Send, human
rating, or full-system readiness. Next choose the next necessary B Send gate
from those measured gaps; do not label this a new M or a product PASS.
