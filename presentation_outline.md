# 5-Slide Deck Outline

## 1. Solution Overview

- Problem: static onboarding wastes time and misses role-specific gaps.
- Solution: parse resume + JD, infer skill gap, and generate a catalog-grounded adaptive roadmap.
- Value proposition: less redundant training, faster role readiness, explainable recommendations.

## 2. Architecture & Workflow

- Frontend layer: standalone web app (HTML/CSS/JS) for upload, diagnostic entry, and roadmap visualization.
- API layer: FastAPI backend with analysis endpoints and reliability checks.
- Extraction layer: document parsing, skill alias matching, experience inference.
- Decision layer: gap scoring, prerequisite graph traversal, module ranking.
- Grounding layer: strict module retrieval from local course catalog.

## 3. Tech Stack & Models

- UI: Streamlit.
- Parsing: pypdf, python-docx.
- Scoring: heuristic NLP plus scikit-learn TF-IDF for module-JD similarity.
- Core model strategy: deterministic, transparent, no external LLM in the critical path.

## 4. Algorithms & Training

- Skill extraction: alias-based matching with local context, years-of-experience hints, and confidence weighting.
- Adaptive pathing: graph-based prerequisite ordering with greedy gap coverage.
- Original logic: module selection is driven by the local catalog only, so the engine cannot hallucinate training items.

## 5. Datasets & Metrics

- Default demo: no external dataset required.
- Optional references for citation: O*NET, Kaggle resume dataset, Kaggle job descriptions dataset.
- Metrics shown in the app: coverage ratio, readiness score, optimized hours, hours saved, residual gap.
