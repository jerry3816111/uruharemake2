# P4-B synthetic runner: retained /bin/sh → /bin/bash startup counterexample

Status: **REVIEW_REQUIRED for the frozen runner v1 source**, not acceptance.
The runner design `9213150` and test-only red contract `83e31a7` remain
unchanged. A source-only WIP in `p4_b_non_b_parity_live_operator.py` has not
been staged, committed or pushed. The first focused integrated run failed
at `fake_a_exec_image_mismatch` before O enumeration or S_runner watching;
there is no runner-gate PASS to report.

## Smallest counterexample and cause

The exact frozen call is
`os.execve('/bin/sh', ('/bin/sh','-c', frozen_script), {})`, with private
fd0/fd3 pipes and zero-data CLOEXEC status EOF. The design assumed the
first post-EOF OS image would be `/bin/bash` because the earlier isolated
feasibility probe sampled the stable state after about 40 ms. In an
integrated immediate observation, the first image was `/bin/sh`; the
frozen witness rejected it as a known wrong image. No release, O/S_runner
admission, model call or positive receipt followed.

Read-only, short-lived local OS probes separated the sampling race from
parser error:

- With identical exact `execve`, fd0/fd3 and empty environment, 10/10
  trials observed a transient `/bin/sh` image (130 such snapshots), then
  two final `/bin/bash` snapshots each (20 total), with the same raw
  PID/start generation and exact argv. All trial processes exited 0.
- A separate 30-trial EOF-immediate probe saw `/bin/sh` first **30/30**
  about 0.23–1.24 ms after EOF, then `/bin/bash` **30/30** about 3–13 ms
  later. The earlier stable-only 5/5 `/bin/bash` result was not false,
  but it did not capture the earlier stage.
- On 5/5 independent cross-checks, both `KERN_PROCARGS2` and
  `libproc.proc_pidpath` reported `/bin/sh` immediately and `/bin/bash`
  after about 20 ms; full argv and raw generation stayed identical.
  Thus this is a same-PID second OS image transition performed by the
  shell target, not a fabricated text field or a different process.

The frozen v1 runner design allowed startup VNODE FDs or exact procargs
unavailability to remain pending, but **did not** allow `/bin/sh` as an
intermediate image. The source must therefore continue to fail closed
under that design. A fixed sleep, silently changing the expected image,
or calling EOF itself an exec success would hide the counterexample.

## Decision and boundary

Keep the original freeze, red tests and failed first source run as history.
Two prospective corrections are technically possible: (a) explicitly
model `held bootstrap → /bin/sh → /bin/bash` with safe FD/identity checks
at both images, or (b) invoke the same fixed script through `/bin/bash`
directly. Since this gate's variable is the **runner lifecycle**, not the
shell launcher's second image transition, choose (b) for a separately
reviewed amendment. An isolated 10/10 direct-`/bin/bash` probe with the
same script/private fd0/fd3 found exact `/bin/bash` image/argv both
immediately after EOF and after 40 ms, one cat child, the same raw
generation, and normal staged release. This is feasibility, not an
integrated result. The new target must be exact
`os.execve('/bin/bash', ('/bin/bash','-c', frozen_script), {})` with no
fallback to `/bin/sh`; any other image/argv, extra pipe, changed
generation or missing two final snapshots within five seconds fails.
The old `/bin/sh` process **did** undergo two OS image transitions;
do not retroactively describe it as a single-image gate.

That correction requires a separately reviewed, committed amendment and
test-only red/negative update **before** adapting the WIP source. The
current evidence is local synthetic process behavior only: 0 Ollama,
model bytes, target HTTP/TCP, Safari, B Send, production DB, real runner
identity, physical T0+90 stop or full-pipeline validation. The unrelated
`output/graduate_application_report/` directory and original dirty
checkout were untouched.
