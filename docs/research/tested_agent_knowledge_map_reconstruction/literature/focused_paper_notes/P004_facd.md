# P004 — [FACD](https://www.ijcai.org/proceedings/2025/648)

**Liu et al., IJCAI 2025. Reading depth: D2.**

## Contribution

Combines a dynamic collaborative response graph with a personalized response-sequence module to
improve early cognitive diagnosis. The paper compares multiple diagnosis models and selection
strategies and includes component, efficiency, pretraining-ratio, and early-step analyses.

## KnowAct transfer

Treat first-turn and first-five-turn reconstruction as primary outcomes and isolate state-update gains
from question-selection gains.

## Do not transfer

Collaborative historical-student information and binary response graphs are unavailable in the strict
KnowAct cold-start setting. The paper itself notes limited theory connecting diagnosis and selection.
