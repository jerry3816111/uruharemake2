#!/usr/bin/env python3
"""Versioned V47 action-candidate ontology with a precise pointing anchor."""

import json
import re
from pathlib import Path

from grounded_frame_isolation_v39 import load_v39_anchor_ontology


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "action_candidate_perception_v47_preregistration.json"


def load_v47_anchor_ontology(config_path=CONFIG_PATH):
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    ontology = load_v39_anchor_ontology()
    ontology[("motion", "point")] = [
        re.compile(pattern) for pattern in config["causal_change"]["candidate_patterns"]
    ]
    return ontology
