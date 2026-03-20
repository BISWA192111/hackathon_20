# AI-Adaptive Onboarding Engine (Full Stack, Python-First)

This project is now a full-stack system with:

- `FastAPI` backend for parsing, skill-gap analysis, adaptive roadmap generation, and reasoning trace.
- Separate web frontend (`HTML/CSS/JS`) that calls backend APIs and visualizes outputs.
- Deterministic, grounded recommendation logic constrained to a local course catalog.

## Core Features (Hackathon Requirements)

- Intelligent Parsing:
  - Resume and JD parsing from `PDF`, `DOCX`, and `TXT`.
  - Skill and experience signal extraction with confidence and mastery.
- Dynamic Mapping:
  - Skill-gap computation (`target - current`) and adaptive module sequencing.
  - Graph-based prerequisite ordering with role-family aware capstone routing.
- Functional Interface:
  - Web UI to upload files or paste text.
  - Roadmap, metrics, skill gaps, and reasoning trace visualization.
- Grounding and Reliability:
  - Every recommendation is from `data/course_catalog.json`.
  - API returns quality checks confirming grounding.
- Reasoning Trace:
  - Stage-by-stage trace included in every analysis response.
- Cross-Domain Scalability:
  - Supports technical and operations role families with shared/general modules.
- Resume or Diagnostic:
  - Optional diagnostic self-assessment can be blended into candidate capabilities.

## Architecture

```text
Frontend (frontend/index.html + frontend/static/*.js,*.css)
    -> calls REST APIs
FastAPI Backend (backend/main.py)
    -> orchestrates parsing + extraction + adaptive pathing
Onboarding Engine (onboarding_engine/*.py)
    -> deterministic skill-gap and roadmap logic
Grounded Catalog (data/course_catalog.json)
```

## Repository Layout

```text
.
├── app.py
├── backend/
│   ├── main.py
│   └── schemas.py
├── frontend/
│   ├── index.html
│   └── static/
│       ├── app.js
│       └── styles.css
├── onboarding_engine/
│   ├── catalog.py
│   ├── engine.py
│   ├── parsing.py
│   ├── roadmap.py
│   ├── skills.py
│   └── types.py
├── data/
│   ├── course_catalog.json
│   └── demo_cases.json
├── requirements.txt
├── Dockerfile
└── presentation_outline.md
```

## Local Setup

1. Create virtual environment:

```bash
python -m venv .venv
```

2. Activate:

```bash
# Windows
.venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run backend + frontend server (same process):

```bash
python app.py
```

5. Open:

```text
http://localhost:8000
```

## Docker

```bash
docker build -t adaptive-onboarding .
docker run -p 8000:8000 adaptive-onboarding
```

## API Endpoints

- `GET /api/v1/health`
- `GET /api/v1/catalog`
- `GET /api/v1/demo/{technical|operations}`
- `POST /api/v1/analyze/text`
  - JSON body:
    - `resume_text` (string)
    - `jd_text` (string)
    - `diagnostic` (optional list): `[{ "skill_id": "...", "self_rating": 0.75, "confidence": 0.7 }]`
- `POST /api/v1/analyze/files`
  - multipart/form-data:
    - `resume_file`
    - `jd_file`
    - `diagnostic_json` (optional JSON string list)

## Adaptive Logic Summary

1. Parse documents into normalized text.
2. Extract known skills using catalog aliases.
3. Estimate mastery and confidence from local context and experience hints.
4. Blend optional diagnostic self-ratings into resume profile.
5. Compute role-aware skill gaps from JD demand versus candidate mastery.
6. Score modules using:
   - gap coverage
   - semantic relevance (TF-IDF similarity)
   - audience fit
   - prerequisite depth
7. Build final roadmap with topological sort on prerequisites.
8. Return metrics, trace, and grounding checks.

## Suggested Slide Citations

- O*NET skill taxonomy: https://www.onetcenter.org/db_releases.html
- Kaggle resume dataset: https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset/data
- Kaggle job descriptions dataset: https://www.kaggle.com/datasets/kshitizregmi/jobs-and-job-description

## Demo Guidance

- Use `Load Technical Demo` and `Load Operations Demo`.
- Run one case with no diagnostic and one with diagnostic rows enabled.
- Highlight:
  - hours saved
  - coverage ratio
  - reasoning trace
  - grounding checks
