# PersonaEval batch-size diagnostic

- This is a post-hoc mechanism diagnostic, not a formal rescore.
- Only batch size changed from 4 to 1; labels were not loaded.
- Diagnosed failed repeat rows: `2`
- Batch-composition effect supported: `1`
- Persistent output-contract failure: `1`
- Formal score and authorization remain unchanged.

- `drama_00286`: batch-effect=`True`, persistent-contract-failure=`False`
- `literary_15150`: batch-effect=`False`, persistent-contract-failure=`True`
