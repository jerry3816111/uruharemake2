# P4-B non-B early-A-death orphan window: read-only review (2026-10-27)

Decision: **real/live NO-GO remains; no new source or live authorization**.
The direct-Bash synthetic runner gate at `3fc07fe` is a bounded fake-only
PASS. This review concerns the failure path where A forks a runner and dies
before P, O or S_runner obtains that runner's initial OS identity. No such
instance was observed in the accepted positive probes; this is a prospective
counterexample, not a claim that a leaked process was seen.

## Exact gap

- `p4_b_non_b_parity_live_operator.py` initializes `known_runners` empty
  (line 2258), adds a generation only after P's `observe_process(child_pid)`
  succeeds (lines 2419–2431), and in `finally` checks disappearance only for
  this set (lines 2632–2645). `all(...)` over an empty set does not certify
  that no unknown descendant exists. A failure still returns a fake error,
  not a positive receipt; the defect is **unproven cleanup**, not a positive
  fake result.
- The existing `runner_exited_before_enumeration` negative identifies the
  runner before release. It does not test A dying before first identity.
- The frozen runner gate already calls this window unresolved and forbids
  borrowing its fake PASS for live physical-stop authorization
  (`research/p4_b_non_b_synthetic_runner_lifecycle_gate_freeze_2026-10-27.md`,
  lines 196–202). The real transition freeze prohibits signaling unknown
  descendants or a process group and permits runner PGID to differ from A.

## Native primitive check and limits

The local macOS SDK's `sys/event.h` and Apple's XNU `bsd/sys/event.h`
explicitly state that `NOTE_FORK` does not return the child's PID in the
delivered kevent and that `NOTE_TRACK`/`NOTE_CHILD` have not been supported
since macOS 10.5:
https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/event.h
Registering another kqueue watch therefore detects a fork but is not an
atomic descendant-identity or containment solution. After A dies and a
child is reparented, enumerating *current children of A* cannot be assumed
to recover the original runner; this is a risk inference, not an OS-path
observation made in this review. A shell-supplied `$!` receipt,
PID scan, pipe EOF or test oracle may help diagnose a cooperative synthetic
case but cannot by itself authorize signaling an unwitnessed real runner.
No native host-level containment mechanism has been proven in this review.

The local Docker client and Linux daemon respond, but only an unrelated
image is cached. A container/cgroup design is **an alternative to investigate,
not an accepted implementation**: it would change the frozen macOS binary,
process topology and likely model runtime/cost, and would need separate
architecture, fairness and physical-stop review. No image was downloaded or
container started here.

## Next single scoped check, not a live release

Prospectively freeze a zero-model negative control in the existing operator
test file: after the fixed synthetic A has actually forked one exact
`/bin/cat`, a test-side OS witness (not a product receipt) records that
generation, then causes A to die at a test-only barrier *before* the
operator's runner identity path receives it. The test must independently
verify the operator rejects the run, all P-owned direct children are
boundedly cleaned, and the original cat generation disappears after P
closes the private stdin writer. A survivor is a failed acceptance assertion;
only afterward may test-side cleanup in `finally` signal that exact, freshly
reverified generation. If identity cannot be reverified, do not send a blind
signal; record a cleanup failure for manual review. Test-side cleanup cannot
count as product proof. Use a new fixed test-only fault/fixture, no model,
HTTP, private DB or Safari, and
preserve the accepted normal/other fault contracts. First record the before
behavior, then decide whether a narrow source correction is needed; do not
turn a passing cooperative-cat negative into real Ollama authorization.

Even a perfect result on this check would prove only this controlled cat
failure path. Before a real attempt, a separately reviewed run-wide
containment or equally strong installed-runner stop witness must close the
unknown-descendant window and retain the original identity, resource,
model, port and T0+90 gates. If that cannot be demonstrated, keep
`REVIEW_REQUIRED` and move to independent product work rather than adding
normal-case repetitions or weakening the safety claim.
