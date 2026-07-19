# V87.2 Post-hoc Scope-Oracle Diagnosis

- Formal decision remains: `inconclusive_effect_between_preregistered_gates`
- Formal scope mismatches: 1
- Mismatches with zero projected markers: 1
- Mismatches unchanged between conditions: 1
- Mismatches matching normalized oracle: 1
- Oracle false positive supported: **YES**

## Root Cause

The V87 scope oracle hashed raw must_avoid values, while the production gate strips surrounding whitespace in both control and treatment. One unchanged marker therefore produced a hash mismatch even though projection removed nothing and did not alter the decision.

This diagnosis does not override V87.2 or authorize production use.
