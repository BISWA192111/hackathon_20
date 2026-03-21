#  AI-Adaptive Onboarding Engine

A full-stack, deterministic onboarding system that generates personalized learning roadmaps by analyzing resume + job description and extracting skill gaps. **No external LLMs in the critical path** — all recommendations are grounded in a curated course catalog.

##  Key Features

### Intelligent Skill Extraction
- **Resume/JD Parsing**: PDF, DOCX, TXT file support with graceful fallbacks
- **Alias-Based Matching**: Fuzzy matching (FuzzyWuzzy) for skill name variations
- **Confidence Scoring**: Multi-factor mastery estimation using:
  - Linguistic hints ("expert" → 0.97, "basic" → 0.42)
  - Years of experience extraction
  - Context-aware relevance weighting

### Adaptive Pathing Algorithm
- **Greedy Gap Coverage**: Weighted marginal-gain module selector
- **Prerequisite Graph**: Respects module dependencies (transitive closure)
- **Role-Specific Routing**: Technical, operations, or general role awareness
- **Topological Ordering**: Valid prerequisite sequence (Kahn's algorithm)

### Explainability & Grounding
- **Reasoning Trace**: Every decision logged with rationale and confidence
- **Hallucination Prevention**: Only recommends modules from catalog
- **Quality Checks**: Validates dependencies, audience tags, and coverage
- **Transparent Scoring**: Full breakdown of gap priority, similarity, cost factors

### Professional UI
- **Modern Web Interface**: White background, professional color scheme (blue/yellow/red)
- **Interactive Elements**: Demo buttons, diagnostic self-assessment, AI chat panel
- **Responsive Design**: Mobile-friendly, works on all screen sizes
- **Real-Time Feedback**: Status messages, visual loading states, progress indicators
- **Drag & Drop Support**: Easy file uploads with validation

### Optional Enhancements
- **O*NET Knowledge Base**: Job market skill frequency & occupation mapping
- **TF-IDF Similarity**: Module-JD relevance scoring (scikit-learn)
- **Persistence**: Supabase-backed run storage & comparison
- **AI Assistant**: Question-answering with intelligent response detection

## 📐 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (Web UI)                        │
│  HTML/CSS/JS - Professional white theme with AI chat panel   │
├─────────────────────────────────────────────────────────────┤
│                   FastAPI Backend Server                      │
│  /api/v1/analyze/text     - Text analysis endpoint           │
│  /api/v1/analyze/files    - File upload & parsing            │
│  /api/v1/assistant/*      - AI Q&A endpoints                 │
│  /api/v1/skills/*         - Enhanced skill analysis          │
└──────────────────┬────────────────────────┬──────────────────┘
                   │                        │
       ┌───────────▼────────┐    ┌──────────▼────────┐
       │ Onboarding Engine  │    │   Enhanced        │
       │  - Skill Extract   │    │   Extractor       │
       │  - Gap Analysis    │    │  - O*NET mapping  │
       │  - Adaptive Pathing│    │  - Market insights│
       │  - Reasoning Trace │    │                   │
       └────────┬───────────┘    └───────────────────┘
                │
       ┌────────▼──────────┐
       │ Data & Catalog    │
       │ - course_catalog  │
       │ - onet_profiles   │
       │ - skill_stats     │
       └───────────────────┘
```

**Layer Breakdown**:

1. **Frontend Layer** (`frontend/`)
   - `index.html`: Semantic structure with upload areas, diagnostic tables, roadmap display
   - `static/styles.css`: Professional white theme, responsive grid layout
   - `static/app.js`: ~1,000 lines; handles file upload, AI chat, analysis rendering

2. **API Layer** (`backend/`)
   - `main.py`: FastAPI app with 13+ endpoints
   - `schemas.py`: Request/response Pydantic models
   - `enhanced_endpoints.py`: Optional enriched skill analysis

3. **Engine Layer** (`onboarding_engine/`)
   - `engine.py`: Main orchestrator
   - `skills.py`: Alias-based extraction with mastery scoring
   - `roadmap.py`: Adaptive module selection (greedy marginal-gain)
   - `catalog.py`: Skill/module definitions
   - `enhanced_extractor.py`: O*NET artifact integration
   - `reasoning.py`: Reasoning trace & grounding verification

4. **Data Layer** (`data/`)
   - `course_catalog.json`: ~50-100 skills, ~400 modules
   - `onet_occupation_profiles.json`: Optional O*NET enrichment
   - `skill_statistics.json`: Job market frequency data

##  Algorithms & Training

### Skill Extraction
- **Method**: Alias-based matching with multi-factor scoring
- **Libraries**: `regex`, `fuzzywuzzy` (token_set_ratio), context detection
- **Mastery Factors**:
  - Linguistic hints ("expert" = 0.97, "basic" = 0.42)
  - Years of experience extraction (+0.65 for 1yr, +0.96 for 7yr)
  - Source type (resume vs. JD with different hint mappings)
- **Confidence**: Combines exact match bonus, fuzzy match score, contextual relevance
- **Result**: Skills ranked by mastery & confidence (0.0-1.0)

### Adaptive Pathing (Weighted Marginal-Gain Algorithm)
```
FOR EACH iteration (max 10):
  FOR EACH candidate module:
    Calculate: Score = (Gap_Gain + 0.3×Similarity + Audience_Bonus) / Duration_Cost
  SELECT module with highest score
  ADD transitive prerequisites automatically
  UPDATE remaining gaps
  IF 90% gap coverage reached: BREAK
```

**Scoring Components**:
- **Gap Gain**: Σ(gap × importance × category_weight)
- **Similarity**: TF-IDF cosine similarity between JD and module text
- **Audience Bonus**: +0.10 (role match) or +0.04 (general)
- **Duration Cost**: module_hours + 0.55×prerequisite_closure_hours

**Graph Algorithms**:
- **Prerequisite Closure**: DFS to find all transitive dependencies
- **Topological Sort**: Kahn's algorithm for valid prerequisite ordering

### Data Sources
1. **Course Catalog** (Primary): Manually curated skills & modules
2. **O*NET** (Optional): Job market data, skill frequencies, occupation mapping
3. **Text Processing**: TF-IDF vectorizer for module-JD similarity

### Quality Assurance
-  **Hallucination Prevention**: Only recommends catalog modules
-  **Dependency Validation**: Topological ordering respects prerequisites
-  **Reasoning Trace**: Every decision logged with confidence & evidence
-  **Role Filtering**: Modules must match audience tags

**For detailed algorithm documentation, see** [ALGORITHMS_AND_TRAINING.md](ALGORITHMS_AND_TRAINING.md)

##  Run Locally

### Prerequisites
- Python 3.8+
- pip

### Quick Start

1. **Create and activate virtual environment**:

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux
```

2. **Install dependencies**:

```bash
pip install -r requirements.txt
```

**Key packages**:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pypdf` - PDF text extraction
- `python-docx` - DOCX file parsing
- `scikit-learn` - TF-IDF vectorization
- `fuzzywuzzy` - Fuzzy string matching
- `pandas` - Data processing
- `supabase` - Optional database (for run persistence)

3. **Configure Supabase** (optional but recommended for persistence):

```bash
# Windows
set SUPABASE_URL=https://<project-ref>.supabase.co
set SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
set SUPABASE_RUNS_TABLE=onboarding_runs

# macOS/Linux
export SUPABASE_URL=https://<project-ref>.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
export SUPABASE_RUNS_TABLE=onboarding_runs
```

Or create `.env` file with these variables.

Apply SQL schema: Run [supabase/schema.sql](c:/Users/USER/Hackathon@IISC/supabase/schema.sql) in your Supabase SQL editor.

4. **Start the server**:

```bash
python app.py
```

Server will start on `http://localhost:8000`

5. **Open in browser**:

```
http://localhost:8000
```

### Using the Web Interface

1. **Upload Resume & JD**: Click on upload areas or drag-drop PDF/DOCX/TXT files
2. **Self-Assessment** (Optional): Add diagnostic skills with confidence ratings
3. **Load Demo**: Use demo buttons to test with sample data
4. **Generate Roadmap**: Click "Generate Learning Roadmap" button
5. **View Results**: See skill gaps, learning roadmap, metrics, and reasoning
6. **Ask AI**: Open AI chat to ask questions about the roadmap

##  Docker

```bash
docker build -t adaptive-onboarding .
docker run -p 8000:8000 \
  -e SUPABASE_URL=https://<project-ref>.supabase.co \
  -e SUPABASE_SERVICE_ROLE_KEY=<service-role-key> \
  -e SUPABASE_RUNS_TABLE=onboarding_runs \
  adaptive-onboarding
```

##  Docker

```bash
# Build image
docker build -t adaptive-onboarding .

# Run container
docker run -p 8000:8000 \
  -e SUPABASE_URL=https://<project-ref>.supabase.co \
  -e SUPABASE_SERVICE_ROLE_KEY=<service-role-key> \
  -e SUPABASE_RUNS_TABLE=onboarding_runs \
  adaptive-onboarding
```

##  API Endpoints

### Health & Config
- `GET /api/v1/health` - Server status
- `GET /api/v1/catalog` - Skill & module definitions

### Analysis
- `POST /api/v1/analyze/text` - Analyze resume + JD (text input)
- `POST /api/v1/analyze/files` - Analyze resume + JD (file upload)
- `GET /api/v1/demo/{technical|operations}` - Load demo data

### Enhanced Analysis (Optional O*NET)
- `POST /api/v1/skills/analyze-enhanced` - Detailed skill analysis with market data
- `POST /api/v1/occupations/insights` - Occupation recommendations

### AI Assistant QA
- `POST /api/v1/assistant/enhance-roadmap` - AI chatbot responses to questions
- `POST /api/v1/assistant/suggest` - Coaching suggestions

### Storage & History
- `GET /api/v1/runs?limit=20` - List previous analyses
- `GET /api/v1/runs/{run_id}` - Retrieve specific analysis
- `POST /api/v1/runs/compare` - Compare two analyses

##  Request/Response Examples

### Text Analysis Request
```json
{
  "candidate_name": "Jane Doe",
  "resume_text": "5 years Python expert, SQL proficient...",
  "jd_text": "Senior Developer: must have Python, required SQL...",
  "diagnostic": [
    {"skill_id": "python", "self_rating": 0.85, "confidence": 0.9}
  ]
}
```

### File Upload Request (multipart/form-data)
```
resume_file: <PDF or DOCX file>
jd_file: <PDF or DOCX file>
candidate_name: "Jane Doe" (optional)
diagnostic_json: [{"skill_id": "python", ...}] (optional)
```

### AI Assistant Question
```json
{
  "user_message": "What's the priority order for learning these modules?",
  "context": {
    "roadmap": [...],
    "gaps": [...],
    "role": "technical"
  }
}
```

### Response Structure
```json
{
  "recommended_role_family": "technical",
  "metrics": {
    "coverage_ratio": 0.92,
    "readiness_score": 0.68,
    "optimized_hours": 45.5,
    "residual_gap": 0.08
  },
  "gaps": [
    {"skill_id": "python", "skill": "Python", "gap": 0.15, "importance": 0.95}
  ],
  "roadmap": [
    {
      "module_id": "M101",
      "title": "Python Fundamentals",
      "phase": "foundation",
      "estimated_hours": 12.0,
      "priority_score": 0.87,
      "reason": "closes gaps in python; priority score 0.87"
    }
  ],
  "trace": [
    {"phase": "skill_extraction", "description": "...", "confidence": 0.92}
  ],
  "quality_checks": {
    "roadmap_modules_in_catalog": true,
    "unknown_modules": []
  }
}
```

##  Configuration

### Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `SUPABASE_URL` | Database endpoint | `https://proj.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Auth token | `eyJhbGc...` |
| `SUPABASE_RUNS_TABLE` | Table name | `onboarding_runs` |
| `AZURE_OPENAI_CHAT_URL` | OpenAI endpoint | `https://...openai.azure.com/` |
| `AZURE_OPENAI_API_KEY` | OpenAI key | `...` |
| `AZURE_OPENAI_TIMEOUT_SECONDS` | Timeout | `30` |

**Note**: Azure OpenAI is optional. If unavailable, assistant uses deterministic fallback responses.

##  Troubleshooting

### "ModuleNotFoundError: No module named 'pypdf'"
→ Run: `pip install -r requirements.txt` or `pip install pypdf`

### File upload not working
→ Check browser console (F12) for errors  
→ Ensure files are < 5MB  
→ Supported formats: PDF, DOCX, DOC, TXT

### Server won't start on port 8000
→ Check if port is already in use: `netstat -ano | findstr :8000` (Windows)  
→ Kill process or change port in `app.py`

### "unable to upload docs" message
→ Verify file type (PDF/DOCX/TXT only)  
→ Check file size (max 5MB)  
→ Browser might need refresh

### No AI responses in chat
→ Check if Azure OpenAI is configured (optional)  
→ System falls back to deterministic responses if Azure unavailable

##  Performance Notes

- **Skill Extraction**: ~100-500ms per resume (depends on length)
- **Adaptive Pathing**: ~50-200ms (graph algorithms)
- **Module Ordering**: ~10-50ms (topological sort)
- **Total Analysis**: ~300-1000ms typical

TF-IDF vectorization is the bottleneck when computing module-JD similarity.

##  Documentation

- [ALGORITHMS_AND_TRAINING.md](ALGORITHMS_AND_TRAINING.md) - Deep dive into algorithms
- [presentation_outline.md](presentation_outline.md) - 5-slide presentation deck
- `supabase/schema.sql` - Database schema for persistence

## 📄 License & Attribution

- **O*NET Data**: Public domain via onetcenter.org
- **Fuzzy Matching**: FuzzyWuzzy (MIT License)
- **ML**: scikit-learn (BSD License)
- **Web Framework**: FastAPI (MIT License)


