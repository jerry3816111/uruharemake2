# V2.3 Single-record Carrier Result

**Decision: major carrier gain, but the frozen 100% contract gate failed.**

- Complete target support: 0/8 -> 6/8
- Projected target support: 7/8 -> 7/8
- Nonexistent source-index errors: 6 -> 0
- Valid rows: 26/32 -> 31/32
- Remaining invalid rows: 1/32

The remaining row used a literal quoted-empty placeholder instead of an empty string. It remains invalid under the frozen contract; no post-hoc pass is claimed.
