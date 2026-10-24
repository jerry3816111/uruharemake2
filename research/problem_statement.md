# Problem statement

The project investigates whether longitudinal observable history available before a prediction time can be converted into an interpretable, parameterized computational model of an individual's public behavior. The model must estimate explicit uncertain state, produce a calibrated probability distribution over behavior in an unseen future event, and expose the memories and state variables that actually affected that distribution.

The central comparison is not “does the reply sound like Uruha?” It is whether a hybrid explicit-state system predicts future observable behavior better than strong LLM and RAG baselines under strict temporal holdout, while preserving provenance, calibration, reproducibility, ablation, and intervention evidence.

一ノ瀬うるは is the first public-observable case study and person-specific parameterization. The architecture must remain person-independent. No model state is treated as private mental-state truth, biological identity, consciousness, or a complete copy of the real person.
