# P4-B synthetic runner: prospective direct-Bash target amendment

Status: **design only**. This is an explicit versioned correction to the
fake-only runner gate `9213150`, not a rewrite of that freeze or a PASS for
its failed source. The test-only red contract `83e31a7` and retained
counterexample `89713a8` remain history. This amendment must be reviewed
and committed before test/source changes. Nothing here authorizes real
Ollama, model/HTTP, T0+90, Safari or B Send.

## Counterexample and one changed variable

The frozen target was `os.execve('/bin/sh', ('/bin/sh','-c', script), {})`
while the post-EOF witness required `/bin/bash` immediately. The first
integrated source WIP failed at `fake_a_exec_image_mismatch` before O or
S_runner. Short-lived same-host OS probes observed `/bin/sh` first in
30/30 EOF-immediate trials, then `/bin/bash` 30/30 at about 3–13 ms,
with identical raw PID/start generation and argv. `KERN_PROCARGS2` and
`proc_pidpath` agreed in 5/5 independent cross-checks. Thus `/bin/sh`
is a real intermediate image, not an observer bug; the frozen one-image
assumption is false.

This amendment changes **only the exact synthetic A exec target path and
argv[0]** from `/bin/sh` to `/bin/bash`. It does not relax image checking,
add sleep/poll exceptions, change the shell script, alter O/S_runner
independence, change the 25 pipes/50 endpoints, modify six fault meanings,
or change any real-data/model/product authority. The expected OS
executable becomes the *same* `/bin/bash` path that is directly invoked.
On this host `/bin/bash` and `/bin/sh` are distinct files (observed
SHA-256 respectively `b46e8d4eac541d79f77000550b4254b47599df8dd8c52cc5b0f37cca1c3b02d4`
and `20c3a003f0bfd51c799e345be7598aa79cecce936ad7f2543e44551ccc70dcad`);
these hashes are local provenance, **not** an installed-Ollama binary
witness or a cross-host security signature.

## Exact replacement and unchanged gates

For `fault=null`, A calls exactly
`os.execve('/bin/bash', ('/bin/bash', '-c',
'/bin/cat <&0 3<&- & wait; read _ <&3; exit 0'), {})`.
The two negative literal scripts stay exactly as frozen, but their own
argv[0] is likewise `/bin/bash`:

- `duplicate_runner`: `/bin/cat <&0 3<&- & /bin/cat <&0 3<&- & wait; read _ <&3; exit 0`
- `retain_private_hold_fd_in_runner`: `/bin/cat <&0 & wait; read _ <&3; exit 0`

The other four faults use the normal script with direct-Bash argv.
The exact marker schema and fault enum are unchanged. A postexec witness
still requires the original unreaped direct-child PID/raw generation,
PPID/PGID, exact `/bin/bash` image and full fault-specific argv, two
independent full FD/type/pipe-handle maps at least 10 ms apart, and
the original five-second deadline. Any observed `/bin/sh`, other image,
wrong argv, extra PIPE/control handle, unexpected FD type or identity
drift now fails immediately. Status EOF alone is never proof. O and
S_runner must still independently enumerate/reobserve the exact one
cat child and watch a true NOTE_EXIT before staged release. No source
branch may silently fall back to `/bin/sh` if direct Bash fails.

An isolated, exact-script/private-fd0/fd3 direct-Bash probe found 10/10
immediate and 40-ms OS `/bin/bash` image/full argv, unchanged generation,
one child, runner-first/A-second staged release and A exit 0. This is
mechanical feasibility only: it does not exercise the 11-role supervisor,
O/S_runner IPC, all fault paths, FD budget or cleanup. The accepted A v2
`/bin/cat` marker/result must remain byte-for-byte behaviorally intact.

## Acceptance and stopping rule

After committing this design, change only the runner test contract's
exact expected A argv[0] to `/bin/bash` for normal and fault variants;
retain all OS, FD, event, non-parent, cleanup and false-authority
assertions. Show the new eight intended runner reds still fail on the
public stub and four invalid markers remain zero-fork PASS. Only then
adapt the uncommitted runner source, initially with the target/path
change and no new fallback. Run focused runner tests, repeat positive
isolated probes, affected operator regression with `-s`, independent
source review, diff/cost report and exact PR head check. Any further
image/FD/cleanup counterexample stays `REVIEW_REQUIRED`; at most one
evidence-backed correction batch remains under the current task, not an
unbounded sequence of target swaps.

The original `/bin/sh` source made one cooperative `os.execve` call but
the process performed two OS image transitions. Do not claim that old
attempt was a one-transition PASS. Direct Bash must be measured in the
integrated gate before even the **fake** runner lifecycle can pass;
real installed binary/model/listener, physical stop and product behavior
remain separate pending gates even if it does.
