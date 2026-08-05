# V2.2 9B Capacity Screen Result

**Decision: semantic extraction improved, but the operational contract failed.**

- Projected target support: 5/8 -> 7/8
- Projected false support: 0/8
- Invalid long-record outputs: 6/32
- Complete-session latency multiplier: 1.77x
- Projection latency multiplier: 1.64x

The 9B model improved evidence recognition, but it treated turns inside one long memory as separate source records and emitted nonexistent indices. Model size alone is therefore insufficient.
