# RightBrain V30 corrective amendment

## Why the first comparison is invalid

Manual output review found that the historical V10 reports counted non-Japanese CJK residue such as `頑张`, `冷蔍庫`, and `遜晚` as accepted. The current gate rejects all three as `nonstandard_cjk_surface`. Newly generated Base-only reports used the current gate, so the two conditions were not measured with the same ruler.

## Corrective action

The interim V10-versus-Base analysis is invalidated. The already generated Base-only reports are frozen by hash. V10 will now be regenerated with the same already committed V30 runner, current gate, cases, seeds, sampling settings, metrics, and thresholds.

No condition, case, metric, or decision rule is changed after seeing Base-only results.

## Evidence boundary

The corrected comparison remains diagnostic because the mismatch was discovered after one condition had run. It can reject a runtime change and guide the next experiment, but it cannot promote either model or prove greater human likeness.
