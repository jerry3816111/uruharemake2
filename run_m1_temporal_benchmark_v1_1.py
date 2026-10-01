#!/usr/bin/env python3
"""M1 V1.1 runner: frozen V1 plus a transport-only JSON compatibility adapter."""

import run_m1_temporal_benchmark as frozen_v1
from longitudinal_human_model.baselines_v1_1 import predict_baseline


# The frozen runner resolves this global at execution time.  No scoring,
# artifact, privacy, or failure behavior is changed.
frozen_v1.predict_baseline = predict_baseline


if __name__ == "__main__":
    raise SystemExit(frozen_v1.main())
