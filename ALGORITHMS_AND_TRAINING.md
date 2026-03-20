# Algorithms & Training Overview

## Current Implementation Summary

The system uses a **deterministic, transparent, heuristic-based approach** rather than relying on external LLMs in the critical path. This ensures explainability, reproducibility, and grounding in the curated course catalog.

---

## 1. SKILL EXTRACTION LOGIC

### 1.1 Primary Approach: Alias-Based Matching with Context Weighting

**Location**: `onboarding_engine/skills.py`, `onboarding_engine/enhanced_extractor.py`

#### Core Algorithm:

```
FOR EACH SKILL IN CATALOG:
  1. Extract aliases and labels from skill definition
  2. Search document text for exact and fuzzy matches
  3. Calculate mastery score based on:
     - Linguistic hints (e.g., "expert", "proficient", "basic")
     - Years of experience mentioned in context
     - Source type (resume vs. job description)
  4. Weight by document source and context
  5. Return ranked list with confidence scores
```

#### Key Components:

**A) Linguistic Hint Matching** (`SOURCE_LEVEL_HINTS`)
- Maps proficiency phrases to mastery scores (0.0-1.0)
- Resume hints: "expert" (0.97) > "proficient" (0.78) > "basic" (0.42)
- JD hints: "must have" (0.95) > "desired" (0.62) > "nice to have" (0.50)

**B) Years of Experience Scoring**
- Extracts years mentioned in context window (±90 chars around skill)
- 7+ years → 0.96 mastery
- 5+ years → 0.90 mastery
- 3+ years → 0.80 mastery
- 1+ year → 0.65 mastery

**C) Confidence Calculation**
- Base confidence: 0.6 (default)
- +0.15 if alias found in context window
- +0.10 if "experience" or "hands-on" mentioned
- +0.15 if JD requirements (must have/required/essential)
- Final: bounded to [0.0, 1.0]

**D) Mastery Base Score**
```
base_score = 0.3 (resume) or 0.5 (JD)
+ linguistic_hint_value (0.35-0.97)
+ years_of_experience_bonus (0-0.66)
+ alias_length_bonus (up to 0.18)
→ Final: 0.0-0.98
```

### 1.2 Enhanced Extraction: Fuzzy Matching (FuzzyWuzzy)

**Implementation**: `EnhancedSkillsExtractor.extract_with_confidence()`

- **Exact Pattern Matching**: Regex with word boundaries (confidence: 0.94)
- **Token-Set Ratio**: Multi-word aliases vs. token sequences (threshold: 0.90 → 0.85 confidence)
- **Token Fuzzy**: Single tokens (threshold: 0.92 → 0.80 confidence)

**Fuzzy Thresholds**:
- Match score ≥ 0.92 for single tokens
- Match score ≥ 0.90 for multi-word aliases

### 1.3 Context-Aware Filtering

Detected context (technical vs. operations) adjusts scores:
- +0.06 if skill category matches detected context
- -0.04 if skill category mismatches (unless "general")

**Context Detection Keywords**:
- **Technical**: python, sql, api, cloud, linux, testing, code, developer
- **Operations**: safety, inventory, equipment, quality, shift, sop, compliance

---

## 2. ADAPTIVE PATHING ALGORITHM

### 2.1 Overview: Weighted Marginal-Gain Module Selector

**Location**: `onboarding_engine/roadmap.py`, function `_select_modules_adaptive()`

This is a **greedy algorithm** that maximizes skill gap coverage while respecting:
- Module prerequisites (dependency graph)
- Role-specific audience tags (technical, operations, general)
- Module similarity to job description
- Time/effort constraints

### 2.2 Core Algorithm: Greedy Gap Coverage with Prerequisite Awareness

```
INITIALIZE:
  role_modules = modules tagged for {role_family}
  remaining_gaps = all skill gap items
  covered_weight = 0
  coverage_target = 90% of total gap weight
  max_steps = min(5, 10) based on gap_count

LOOP (up to max_steps iterations):
  FOR EACH candidate_module NOT yet selected:
    IF module addresses no remaining gaps:
      SKIP
    
    // Calculate margin-gain score
    new_skills = skills from module IN remaining_gaps
    marginal_gain = Σ gap_priority(skill) for skill in new_skills
    
    // Fetch prerequisite closure (all transitive prerequisites)
    closure = {prereq modules} not yet selected
    closure_hours = Σ duration of closure modules
    
    // Calculate total cost
    duration_cost = module.hours + (0.55 * closure_hours)
    
    // Blended scoring
    similarity_score = TF-IDF cosine similarity(JD, module_text)
    audience_bonus = 0.10 (if role_family in tags) 
                   + 0.04 (if "general" in tags) else 0.0
    
    total_score = (marginal_gain + 0.3*similarity + audience_bonus) 
                  / duration_cost
    
  SELECT module with highest total_score
  
  // Handle prerequisites automatically
  FOR each prereq in prerequisite_closure(selected):
    IF not already selected:
      ADD to roadmap with priority_score = 0.4 * parent_score
  
  UPDATE remaining_gaps, covered_weight
  ADD selection_trace for explainability
  
  IF covered_weight >= coverage_target:
    BREAK
```

### 2.3 Key Scoring Components

| Component | Weight | Formula | Range |
|-----------|--------|---------|-------|
| **Marginal Gap Gain** | 1.0 | Σ(gap × importance × category_weight) | 0.0-∞ |
| **Similarity** | 0.3 | TF-IDF cosine(JD, module) | 0.0-1.0 |
| **Audience Bonus** | - | 0.10 (role match) or 0.04 (general) | 0.0-0.10 |
| **Duration Cost** | denominator | hours + 0.55×closure_hours | 0.1-∞ |

**Gap Priority Formula**:
```
gap_priority = gap_size × importance_weight × category_weight

where:
  - gap_size ∈ [0, 1] (target_mastery - current_mastery)
  - importance_weight from JD signal strength
  - category_weight = 1.15 (technical)
                    = 1.08 (operations)
                    = 1.00 (other)
```

### 2.4 Prerequisite Graph Traversal

**Function**: `_prereq_closure()` - transitive closure of prerequisites
- Builds DAG of all prerequisite dependencies
- Graph-based DFS to find all transitive prerequisites
- Cost includes ALL prerequisites (not just direct)

### 2.5 Topological Ordering

**Function**: `_topological_order()` - respects dependency constraints
- Uses **Kahn's algorithm** (breadth-first topological sort)
- Maintains `indegree` counter for each module
- Ensures prerequisites always come before dependents
- Breaks ties using catalog's module_order (priority ranking)

### 2.6 Capstone Module Selection

**Function**: `_choose_capstone()`
- **Technical roles**: `M402` (Technical Project)
- **Operations roles**: `M403` (Operations Project)
- **General roles**: `M404` (General Project)

Automatically added if not already selected, with prerequisites.

### 2.7 Learning Mode Detection

For each roadmap step:
```
IF candidate_mastery >= 0.72:
  learning_mode = "fast-track"  (can compress delivery)
ELSE:
  learning_mode = "deep-dive"   (full coverage needed)
```

---

## 3. GAP ANALYSIS

### Skills Gap Map
**Function**: `_skill_gap_map()`

For each skill in the job description:
```
target_mastery = JD_signal_mastery × 1.15
current_mastery = resume_signal_mastery or 0.0
gap = max(0, target - current)

Stored attributes:
  - gap (float 0-1)
  - target (float 0-1)
  - current (float 0-1)
  - importance (weight from JD signal)
  - category_weight (technical/operations bonus)
```

### Module Mastery Assessment
**Function**: `_module_mastery()`

```
module_mastery = Σ(candidate_mastery for each skill in module) 
                 / number_of_skills

where candidate_mastery = signal.mastery from resume (or 0)
```

---

## 4. ROLE FAMILY DETERMINATION

**Logic**: Detected from JD signals > falls back to resume role_family

```
IF jd.role_family != "general":
  use jd.role_family
ELSE:
  use resume.role_family
```

**Categories**: technical, operations, general

---

## 5. TRAINING & DATA SOURCES

### 5.1 Skill Catalog (Primary)

**File**: `data/course_catalog.json`

Manually curated catalog containing:
- 50-100+ skills with IDs, labels, aliases, categories
- 400+ modules with:
  - Duration (hours)
  - Prerequisites (module dependencies)
  - Audience tags (technical, operations, general)
  - Skill-to-module mappings

### 5.2 O*NET Knowledge Base (Optional, Enhanced)

**Files Generated**:
- `data/onet_occupation_profiles.json` - O*NET occupation skills
- `data/onet_skill_vocabulary.json` - Cross-reference mapping
- `data/skill_statistics.json` - Job market frequency data

**Extraction From**: O*NET data files (Skills.xlsx, Occupations.xlsx, etc.)

**Purpose**:
- Skill frequency in job market (for market value scoring)
- Related occupations recommendation
- Cross-validation against catalog

### 5.3 Language Models: TF-IDF (Scikit-Learn)

**Usage**: Module-JD similarity scoring

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

corpus = [jd_text] + [module_text for each module]
vectorizer = TfidfVectorizer(stop_words="english")
matrix = vectorizer.fit_transform(corpus)
similarity = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
```

**Result**: Similarity scores for each module (0.0-1.0)

### 5.4 Fuzzy String Matching: FuzzyWuzzy

**Library**: `fuzzywuzzy`

**Methods Used**:
- `fuzz.token_set_ratio()` - multi-word alias matching
- `fuzz.ratio()` - single token matching

**Threshold**: 0.90-0.92 (normalized to 0.85-0.94 confidence)

---

## 6. NO EXTERNAL LLM IN CRITICAL PATH

**Design Decision**: All decisions driven by deterministic algorithms

- ✅ Skill extraction: Alias matching + heuristics
- ✅ Gap analysis: Simple arithmetic
- ✅ Module selection: Greedy marginal-gain algorithm
- ✅ Prerequisite ordering: Topological sort (Kahn)
- ❌ No ChatGPT, Claude, or Azure OpenAI for final recommendations

**Benefit**: Explainability, reproducibility, grounding in catalog

---

## 7. GROUNDING & HALLUCINATION PREVENTION

**Module**: `onboarding_engine/reasoning.py`

### 7.1 GroundingVerifier
- Verifies all modules in roadmap exist in catalog
- Tracks which modules are "grounded" vs. external
- Reports unknown modules to user

### 7.2 HallucinationPreventer
- Intercepts any module not in `catalog.modules`
- Prevents inclusion in final roadmap
- Falls back to role-relevant modules only

### 7.3 ReasoningTracer
Captures 5 key phases with trace information:

1. **Skill Extraction**: Source, confidence, evidence
2. **Gap Analysis**: Current vs. target, importance
3. **Module Selection**: Marginal gain, cost, similarity
4. **Prerequisite Processing**: Closure details
5. **Ranking & Ordering**: Final roadmap sequence

---

## 8. METRICS & QUALITY CHECKS

### 8.1 Per-Roadmap-Step Metrics

| Metric | Calculation | Use |
|--------|-----------|-----|
| **Readiness Score** | Module mastery from resume | Fast-track vs. deep-dive |
| **Demand Score** | Σ gaps addressed by module | Priority in roadmap |
| **Similarity Score** | TF-IDF cosine(JD, module) | JD relevance |
| **Priority Score** | (gain + sim + audience) / cost | Selection ranking |

### 8.2 AdvancedMetrics (Optional)

**Calculated attributes**:
- Coverage ratio (% gaps addressed)
- Readiness score (avg of module mastery)
- Hours saved (if using fast-track modes)
- Residual gap (% gaps NOT covered)
- Optimized duration (total hours in roadmap)

### 8.3 Quality Checks

- ✅ All modules in catalog?
- ✅ Unknown modules reported?
- ✅ Roadmap modules match audience tags for role?
- ✅ Prerequisites satisfied?

---

## 9. EXPLAINABILITY & EVIDENCE

### 9.1 Skill Evidence (Resume/JD)

For each extracted skill, the system stores:
```
{
  "skill_id": "SK001",
  "label": "Python",
  "mastery": 0.85,
  "confidence": 0.92,
  "evidence": [
    "5 years experience with Python",
    "Python mentioned in job description"
  ]
}
```

### 9.2 Module Selection Rationale

Each roadmap step includes:
```
"reason": "closes gaps in [SK001, SK003]; 
           depends on [M101]; 
           candidate already has partial mastery so delivery can be compressed; 
           priority score 0.87"
```

### 9.3 Reasoning Trace

Captured in `response.trace[]` array:
- Phase (skill_extraction, gap_analysis, module_selection, ranking)
- Description (human-readable summary)
- Details (JSON with confidence, evidence)

---

## 10. CURRENT LIMITATIONS & FUTURE IMPROVEMENTS

### Current Limitations
1. **No multi-word fuzzy matching** for skill aliases (only single-token or exact)
2. **Greedy vs. optimal**: Marginal-gain is fast but not guaranteed optimal
3. **No user feedback loop**: Confidence scores are static
4. **Limited market data**: O*NET stats may not reflect latest tech trends
5. **No active learning**: No retraining on user outcomes

### Potential Enhancements
1. **Knowledge Tracing**: Track skill mastery progression over time
2. **Bayesian Updates**: Update confidence based on user interaction
3. **Graph-based Re-ranking**: Use skill prerequisite graph to optimize order
4. **Collaborative Filtering**: Compare against similar user profiles
5. **A/B Testing Framework**: Test different algos against user outcomes
6. **Custom Alias Training**: Fine-tune fuzzy thresholds per domain

---

## 11. REPRODUCIBLE EXAMPLE

### Input
```
Resume: "5 years Python expert, SQL proficient, cloud novice"
JD: "Must have Python, required SQL, preferred Go, nice-to-have Rust"
```

### Extraction (Skills)
| Skill | Source | Mastery | Confidence | Evidence |
|-------|--------|---------|------------|----------|
| Python | Resume | 0.97 | 0.95 | "5 years" + "expert" |
| SQL | Resume | 0.78 | 0.92 | "proficient" |
| Cloud | Resume | 0.42 | 0.70 | "novice" |
| Python | JD | 0.95 | 0.98 | "must have" |
| SQL | JD | 0.92 | 0.96 | "required" |
| Go | JD | 0.68 | 0.85 | "preferred" |
| Rust | JD | 0.50 | 0.76 | "nice-to-have" |

### Gap Analysis
| Skill | Current | Target | Gap | Importance | Priority |
|-------|---------|--------|-----|-----------|----------|
| Python | 0.97 | 1.09 | 0.12 | 0.95 | Low |
| SQL | 0.78 | 1.06 | 0.28 | 0.92 | Medium |
| Cloud | 0.42 | 0.48 | 0.06 | 0.70 | Low |
| Go | 0.00 | 0.78 | 0.78 | 0.68 | High |
| Rust | 0.00 | 0.57 | 0.57 | 0.50 | Medium |

### Module Selection
If modules exist:
- `M101` (Go Fundamentals): gap_gain=0.78, duration=10h, score=0.078
- `M102` (Advanced SQL): gap_gain=0.28, duration=8h, score=0.035
- `M255` (Cloud Practitioner): gap_gain=0.06, duration=12h, score=0.005

**Ranking**: M101 > M102 > M255

---

## Summary Table: Algorithm Components

| Component | Type | Method | Library | Key Feature |
|-----------|------|--------|---------|-------------|
| Skill Extraction | Heuristic | Alias matching + linguistic hints | regex, fuzzywuzzy | Alias-based with mastery scoring |
| Context Detection | Heuristic | Keyword frequency | regex | Technical vs. operations classification |
| Module Similarity | ML | TF-IDF + cosine similarity | scikit-learn | JD relevance scoring |
| Module Selection | Greedy Algorithm | Marginal-gain selector | custom | Prerequisite-aware gap coverage |
| Prerequisite Resolution | Graph Algorithm | Topological sort (Kahn) | custom | DAG traversal for dependency order |
| Grounding Verification | Rule-based | Catalog membership check | custom | Hallucination prevention |
| Confidence Weighting | Heuristic | Multi-factor scoring | custom | Combines evidence sources |

---

**Last Updated**: March 2026  
**Maintainers**: Hackathon@IISC Team
