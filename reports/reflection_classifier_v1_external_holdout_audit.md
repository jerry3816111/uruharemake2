# Reflection Classifier V1 External Holdout Construction Audit

Status: **PASS**

- Cases: 32
- Classes: {"interpretive": 8, "none": 8, "procedural": 8, "semantic": 8}
- Languages: {"cmn": 6, "eng": 15, "jpn": 11}
- Licenses: {"CC BY 2.0 FR": 32}
- Exact authored-development overlap: 0
- Classifier/model calls during construction: 0

## Checks

- selected_source_and_dataset_ids_match_in_order: PASS
- case_ids_are_unique: PASS
- sentence_ids_are_unique: PASS
- case_count_matches_preregistration: PASS
- class_balance_matches_preregistration: PASS
- language_balance_matches_preregistration: PASS
- all_source_rows_approved: PASS
- all_source_rows_have_provenance: PASS
- dataset_text_is_exact_source_text: PASS
- no_exact_development_text_overlap: PASS
- construction_used_no_classifier_or_model: PASS

## Evidence boundary

Tatoeba supplies exact sentence text and source metadata only. Reflection labels are project operational labels. A construction pass authorizes a separately frozen matched evaluation only; it is not a classifier result and does not authorize runtime memory writes or broad human-likeness claims.
