# P4-B dotenv import-effect guard — zero-model result (2026-10-26)

## What changed

Before this edit, `uruha_brain_mac.py` called `load_dotenv()` unconditionally
after its imports and before its model/config globals. The fixed B child had
already validated its launch environment before Web/Brain import, but a later
`.env` read could add previously absent, unbound settings. No `.env` was found
at the worktree or inspected ancestors today; this was a reachable path, not
an observed B incident. The source manifest v5 already includes Brain.

Only Brain's dotenv call is now conditional: the presence of **any**
case-insensitive `URUHA_P4_B_` key suppresses it, even for malformed or
empty-valued intent. Without B intent, the existing dotenv call happens once.
The B bootstrap remains responsible for rejecting malformed intent. No model,
prompt, baseline, receipt, frozen research data, memory, or reply rule changed.

## Evidence

| Layer | Observation |
|---|---|
| Before/source contract | New focused AST test failed 2/2 before product edit because the decision helper did not exist and Brain still had a direct top-level `load_dotenv()` call. |
| After/source contract | 2/2 pass. Exact Brain function AST executed with a fake loader: valid B, malformed B, lowercase B, and unknown empty mixed-case B each made 0 loader calls and added 0 fake config; non-B made exactly 1 call. Static assertion requires the top-level helper call before `M31_SEMANTIC_VERIFIER_MODEL` config read and no residual direct top-level dotenv call. |
| Adjacent zero-model | `test_p4_b_brain_dotenv_import_effect.py`, product-source manifest, endpoint binding, child bootstrap, child-chain zero-provider, and controller seam: **201/201 pass in 218.41s**. |
| Syntax/whitespace | `py_compile` of changed Python files and `git diff --check`: pass. |
| Provider/Web/Safari | 0 model/provider, 0 Web/Safari, 0 DB, 0 deployment in this item. No actual full Brain import or visible response was claimed. |

The test executes source AST under a fake loader; it is not a fresh B child,
real Ollama process, full import-effect closure, or B Send. Installed packages,
already inherited environment values, a B marker removed before Brain import,
other external data assets, post-admission terminal behavior, token upper
bound, actual 20-second delivery, and A/human ratings remain separate gates.
The independently reviewed design/patch GO is scoped to this source/fake
change, not product readiness.

Next: review the exact scoped diff, commit/push PR #435 and verify exact head;
only then rerun one read-only committed HEAD source snapshot. If it fails,
retain the failure. Do not retry the failed real-Ollama probe or send B.
