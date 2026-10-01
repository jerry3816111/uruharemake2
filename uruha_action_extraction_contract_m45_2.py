"""M45.2: constrain source metadata, accept legitimate one-kanji objects.

No semantic review bit is relaxed; M45/M45.1 frozen failures remain unchanged.
"""
from copy import deepcopy
import re
import uruha_actionable_help_delivery_m45 as base

_ORIGINAL_NATIVE = base._native_json
_ORIGINAL_STRUCTURAL = base.structural_action_check
_INSTALLED = False


def constrained_review_schema(payload):
    sources = [s for s in payload.get("sources") or []
               if s.get("kind") in {"current_user", "linked_previous_user"}
               and isinstance(s.get("id"), str) and isinstance(s.get("text"), str) and s["text"].strip()]
    if not sources:
        raise ValueError("No allowed source for review")
    schema = deepcopy(base.REVIEW_SCHEMA)
    # deepcopy preserves shared _TEXT aliases. Replace each field object rather
    # than attaching an enum that would accidentally constrain ALL text fields.
    schema["properties"]["source_id"] = {"type": "string", "enum": list(dict.fromkeys(s["id"] for s in sources))}
    schema["properties"]["source_span"] = {"type": "string", "enum": list(dict.fromkeys(s["text"] for s in sources))}
    return schema


def constrained_native(system, payload, schema, deadline, metrics):
    if schema is base.REVIEW_SCHEMA:
        schema = constrained_review_schema(payload)
        metrics["source_decoding_constraint_m45_2"] = {
            "source_count": len(schema["properties"]["source_id"]["enum"]),
            "quote_kind": "complete_allowed_user_clause",
            "semantic_checks_relaxed": False, "raw_dialogue_persisted": False}
    return _ORIGINAL_NATIVE(system, payload, schema, deadline, metrics)


def structural_check(proposal, sources):
    errors = _ORIGINAL_STRUCTURAL(proposal, sources)
    if isinstance(proposal, dict):
        obj = proposal.get("object_jp")
        if (isinstance(obj, str) and re.fullmatch(r"[一-龯]", obj)
                and obj in str(proposal.get("instruction_jp") or "")):
            errors = [e for e in errors if e != "invalid_object_jp"]
    return errors


def install_m45_2_extraction_contract():
    global _INSTALLED
    if _INSTALLED:
        return False
    base._native_json = constrained_native
    base.structural_action_check = structural_check
    _INSTALLED = True
    return True


def render_m45_2(result):
    from uruha_task_evidence_authorization_m45_1 import render_m45_1
    html = render_m45_1(result)
    if ((result.get("logic") or {}).get(base.LABEL) or {}).get("source_decoding_constraint_m45_2"):
        html = html.replace('<div class="m45-title">',
            '<div class="m45-note">M45.2：引用只能選本輪允許的原文，沒有放寬語意審核。</div><div class="m45-title">', 1)
    return html
