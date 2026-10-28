# Variable dictionary

| Symbol | Model variable | Required semantics |
|---|---|---|
| `H_0:t` | Observable history | Evidence dated no later than prediction time `t` |
| `X_t+1` | New event/context | Outcome-stripped information available at prediction time |
| `M_t` | Memory state | Episodic/semantic/interaction memories with time, provenance, strength, confidence, and validity |
| `E_t` | Estimated emotion state | Uncertain predictive variables, never private-emotion ground truth |
| `P` | Personality/tendencies | Slow-moving learned or interpretable behavioral tendencies |
| `R_t` | Relationship state | Per-entity familiarity, trust, affinity, conflict, role, frequency, confidence |
| `V_t` | Preferences/values | Time-valid likes, dislikes, priorities, and value tendencies |
| `G_t` | Goals/motivation | Context-dependent active objectives |
| `HAB_t` | Habits/priors | Repeated response and action tendencies |
| `K_t` | Context | Activity, topic, participants, platform, public/private scope, time |
| `U_t` | Uncertainty | Confidence and unknown space for every inferred state |
| `S_hat_t+1` | Estimated state | Inspectable combination of the variables above after transition |
| `Y_t+1` | Observable future behavior | Utterance, reaction, choice, action, or silence used as ground truth |

Primary prediction hierarchy: behavior/action class, attitude/direction, then natural-language realization. Exact wording is not the primary target.
