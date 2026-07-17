# Reflection Hybrid Classifier V4 Holdout Construction Audit

Status: **PASS**

- Cases: 32
- Classes: {"interpretive": 8, "none": 8, "procedural": 8, "semantic": 8}
- Languages: {"cmn": 6, "eng": 16, "jpn": 10}
- Prior Tatoeba ID overlap: 0
- Existing reflection text overlap: 0
- Evaluated Qwen calls during construction: 0

## Checks

- selected_source_and_dataset_ids_match_in_order: PASS
- case_ids_are_unique: PASS
- sentence_ids_are_unique: PASS
- no_prior_tatoeba_sentence_id_overlap: PASS
- no_existing_reflection_text_overlap: PASS
- case_count_matches_preregistration: PASS
- class_balance_matches_preregistration: PASS
- language_balance_matches_preregistration: PASS
- all_source_rows_approved: PASS
- all_source_rows_have_provenance: PASS
- all_source_licenses_match_preregistration: PASS
- dataset_text_is_exact_source_text: PASS
- construction_used_no_evaluated_qwen_inference: PASS

## Evidence boundary

Tatoeba supplies exact sentence text and source metadata. Codex assisted selection and project operational labeling; Tatoeba did not supply the labels. A construction pass authorizes only a separately frozen matched evaluation harness. It is not a model result and does not authorize runtime memory writes or broad human-likeness claims.
