"""
Data Processing and Model Training Pipeline
- Extract skills from job descriptions
- Train TF-IDF model for skill-job matching
- Enhance course catalog with real data
- Create grounding verification system
"""

import pandas as pd
import json
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle

# ============================================================================
# 1. LOAD DATASETS
# ============================================================================

print("=" * 80)
print("LOADING DATASETS")
print("=" * 80)

# Load job descriptions
df_jobs = pd.read_csv('job_title_des.csv/job_title_des.csv')
print(f"\n✓ Loaded {len(df_jobs)} job postings")
print(f"  Columns: {df_jobs.columns.tolist()}")

# Rename columns for consistency
df_jobs = df_jobs.rename(columns={
    'Job Title': 'job_title',
    'Job Description': 'job_description',
    'Unnamed: 0': 'id'
})

# Load existing course catalog
with open('data/course_catalog.json', 'r') as f:
    catalog = json.load(f)

print(f"✓ Loaded course catalog with {len(catalog['skills'])} skills and {len(catalog['modules'])} modules")

# ============================================================================
# 2. EXTRACT SKILLS FROM JOB DESCRIPTIONS
# ============================================================================

print("\n" + "=" * 80)
print("TRAINING TF-IDF MODEL")
print("=" * 80)

# Get existing skills and their aliases
skills_dict = {skill['skill_id']: skill for skill in catalog['skills']}
all_aliases = {}
for skill in catalog['skills']:
    all_aliases[skill['skill_id']] = [skill['label']] + skill.get('aliases', [])

print(f"\n✓ Extracted {len(skills_dict)} skills with aliases")

# Prepare training data
job_descriptions = df_jobs['job_description'].fillna('').values
print(f"✓ Prepared {len(job_descriptions)} job descriptions for training")

# Train TF-IDF vectorizer (keep for skill matching)
vectorizer = TfidfVectorizer(
    max_features=500,
    stop_words='english',
    ngram_range=(1, 2),
    min_df=5
)
tfidf_matrix = vectorizer.fit_transform(job_descriptions)

# Save vectorizer
with open('data/tfidf_vectorizer.pkl', 'wb') as f:
    pickle.dump(vectorizer, f)

print(f"✓ Trained TF-IDF vectorizer with vocabulary size: {len(vectorizer.get_feature_names_out())}")

# ============================================================================
# 3. BUILD SKILL OCCURRENCE STATISTICS
# ============================================================================

print("\n" + "=" * 80)
print("ANALYZING SKILL OCCURRENCES")
print("=" * 80)

# Count skill mentions in job descriptions
skill_occurrences = {}
for skill_id, aliases in all_aliases.items():
    count = 0
    for desc in job_descriptions:
        desc_lower = desc.lower()
        if any(alias.lower() in desc_lower for alias in aliases):
            count += 1
    skill_occurrences[skill_id] = {
        'count': count,
        'frequency': count / len(job_descriptions)
    }

# Sort by frequency
sorted_skills = sorted(skill_occurrences.items(), key=lambda x: x[1]['frequency'], reverse=True)

print(f"\nTop 15 most common skills in job descriptions:")
for i, (skill_id, info) in enumerate(sorted_skills[:15], 1):
    skill_name = skills_dict[skill_id]['label']
    freq = info['frequency'] * 100
    print(f"  {i:2d}. {skill_name:30s} - {freq:5.1f}% of jobs")

# ============================================================================
# 4. CREATE JOB-SKILL MAPPING
# ============================================================================

print("\n" + "=" * 80)
print("CREATING JOB-SKILL MAPPING")
print("=" * 80)

job_skill_mapping = []
for idx, row in df_jobs.iterrows():
    job_title = row['job_title']
    job_desc = row['job_description'].lower() if pd.notna(row['job_description']) else ''
    
    # Extract skills for this job
    found_skills = []
    for skill_id, aliases in all_aliases.items():
        if any(alias.lower() in job_desc for alias in aliases):
            found_skills.append(skill_id)
    
    job_skill_mapping.append({
        'job_id': idx,
        'job_title': job_title,
        'skills': found_skills,
        'num_skills': len(found_skills)
    })

# Analyze skill distribution
skill_counts = [m['num_skills'] for m in job_skill_mapping]
print(f"\nSkill distribution across jobs:")
print(f"  Average skills per job: {np.mean(skill_counts):.1f}")
print(f"  Median skills per job: {np.median(skill_counts):.1f}")
print(f"  Min skills per job: {np.min(skill_counts)}")
print(f"  Max skills per job: {np.max(skill_counts)}")

# ============================================================================
# 5. BUILD SKILL-PREREQUISITE GRAPH
# ============================================================================

print("\n" + "=" * 80)
print("ANALYZING SKILL CO-OCCURRENCE")
print("=" * 80)

# Count how often skills appear together
skill_pairs = {}
for mapping in job_skill_mapping:
    skills = mapping['skills']
    for i, s1 in enumerate(skills):
        for s2 in skills[i+1:]:
            key = tuple(sorted([s1, s2]))
            skill_pairs[key] = skill_pairs.get(key, 0) + 1

# Get top correlations (skills that appear together frequently)
top_pairs = sorted(skill_pairs.items(), key=lambda x: x[1], reverse=True)[:10]
print(f"\nTop skill co-occurrences in jobs:")
for i, ((s1, s2), count) in enumerate(top_pairs, 1):
    name1 = skills_dict[s1]['label']
    name2 = skills_dict[s2]['label']
    print(f"  {i:2d}. {name1:20s} + {name2:20s} - {count} jobs")

# ============================================================================
# 6. SAVE TRAINING DATA AND MODELS
# ============================================================================

print("\n" + "=" * 80)
print("SAVING TRAINING DATA AND MODELS")
print("=" * 80)

# Save skill statistics
skill_stats = {
    'occurrences': skill_occurrences,
    'job_skill_mapping': job_skill_mapping,
    'skill_pairs': {str(k): v for k, v in skill_pairs.items()},
    'total_jobs': len(df_jobs),
    'total_skills': len(skills_dict)
}

with open('data/skill_statistics.json', 'w') as f:
    json.dump(skill_stats, f, indent=2)

print("✓ Saved skill_statistics.json")

# Save enhanced dataset
df_jobs_enhanced = df_jobs.copy()
df_jobs_enhanced['detected_skills'] = [m['skills'] for m in job_skill_mapping]
df_jobs_enhanced.to_csv('data/jobs_with_skills.csv', index=False)

print("✓ Saved jobs_with_skills.csv")

# ============================================================================
# 7. CREATE GROUNDING DATABASE
# ============================================================================

print("\n" + "=" * 80)
print("CREATING GROUNDING DATABASE")
print("=" * 80)

# Build module vocabulary for grounding checks
grounding_db = {
    'modules': {},
    'skills': {},
    'job_families': {}
}

# Index modules
for module in catalog['modules']:
    grounding_db['modules'][module['module_id']] = {
        'title': module['title'],
        'skills': module['skills'],
        'difficulty': module['difficulty'],
        'duration_hours': module['duration_hours']
    }

# Index skills
for skill in catalog['skills']:
    grounding_db['skills'][skill['skill_id']] = {
        'label': skill['label'],
        'category': skill['category'],
        'aliases': skill['aliases']
    }

# Infer job families from job titles
job_families_map = {}
for job in df_jobs['job_title'].unique():
    job_lower = job.lower()
    if any(tech_term in job_lower for tech_term in ['engineer', 'developer', 'analyst', 'scientist', 'architect', 'tech']):
        family = 'technical'
    elif any(ops_term in job_lower for ops_term in ['operator', 'supervisor', 'technician', 'worker', 'specialist']):
        family = 'operations'
    else:
        family = 'general'
    job_families_map[job] = family

grounding_db['job_families'] = job_families_map

with open('data/grounding_db.json', 'w') as f:
    json.dump(grounding_db, f, indent=2)

print(f"✓ Saved grounding_db.json with {len(grounding_db['modules'])} modules")
print(f"✓ Indexed {len(grounding_db['skills'])} skills for grounding verification")

print("\n" + "=" * 80)
print("DATA PIPELINE COMPLETE")
print("=" * 80)
print(f"\nGenerated files:")
print(f"  - data/tfidf_vectorizer.pkl       (Model)")
print(f"  - data/skill_statistics.json      (Statistics)")
print(f"  - data/jobs_with_skills.csv       (Enriched data)")
print(f"  - data/grounding_db.json          (Grounding verification)")
