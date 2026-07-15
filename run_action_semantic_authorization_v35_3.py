#!/usr/bin/env python3
"""Rerun V35.2 with ontology entries limited to proposed calls."""

import argparse
import json
from pathlib import Path

from run_action_semantic_authorization_v35 import run as run_v35
from run_action_semantic_authorization_v35_1 import SYSTEM_PROMPT_V35_1
from run_action_semantic_authorization_v35_2 import ACTION_CATALOG_V35_2


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "reports" / "action_semantic_authorization_v35_3_development_raw.json"


def run(output=DEFAULT_OUTPUT):
    return run_v35(
        output,
        system_prompt=SYSTEM_PROMPT_V35_1,
        study_variant="v35_3",
        action_catalog=ACTION_CATALOG_V35_2,
        action_catalog_mode="proposed_only",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run(args.output)
    print(
        json.dumps(
            {"rows": len(report["rows"]), "completed_at": report["completed_at"]},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
