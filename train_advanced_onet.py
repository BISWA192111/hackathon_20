"""
Advanced O*NET Data Extraction and Analysis
- Correctly parse O*NET file structures
- Create rich skill taxonomy
- Map real occupations to skills
- Train advanced matching models
"""

import pandas as pd
import json
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle
import warnings

warnings.filterwarnings('ignore')

print("=" * 100)
print("ADVANCED O*NET SKILL EXTRACTION AND ANALYSIS")
print("=" * 100)

ONET_PATH = Path('db_30_1_excel/db_30_1_excel')

# ============================================================================
# 1. LOAD AND EXPLORE O*NET FILES
# ============================================================================

print("\n[1] LOADING O*NET FILES WITH CORRECT STRUCTURE")
print("-" * 100)

# Load occupation data to understand structure
occupations = pd.read_excel(ONET_PATH / 'Occupation Data.xlsx')
print(f"✓ Occupation Data columns: {occupations.columns.tolist()[:10]}")

# Load skills
skills_df = pd.read_excel(ONET_PATH / 'Skills.xlsx')
print(f"✓ Skills columns: {skills_df.columns.tolist()[:10]}")

# Load knowledge
knowledge_df = pd.read_excel(ONET_PATH / 'Knowledge.xlsx')
print(f"✓ Knowledge columns: {knowledge_df.columns.tolist()[:10]}")

# Load technology skills
tech_df = pd.read_excel(ONET_PATH / 'Technology Skills.xlsx')
print(f"✓ Technology Skills columns: {tech_df.columns.tolist()[:10]}")

# ============================================================================
# 2. EXTRACT OCCUPATIONS AND TITLES
# ============================================================================

print("\n[2] EXTRACTING OCCUPATIONS AND TITLES")
print("-" * 100)

# Get occupation codes and titles
occ_data = {}

# Try different column names
code_col = None
title_col = None

for col in occupations.columns:
    if 'code' in col.lower() or 'occ' in col.lower():
        code_col = col
    if 'title' in col.lower():
        title_col = col

print(f"  Using Code Column: {code_col}")
print(f"  Using Title Column: {title_col}")

if code_col and title_col:
    for idx, row in occupations.iterrows():
        code = str(row[code_col]).strip()
        title = str(row[title_col]).strip()
        if code and code != 'nan':
            occ_data[code] = {'title': title}

print(f"✓ Extracted {len(occ_data)} occupations")

# Show samples
print(f"\nSample occupations:")
for i, (code, data) in enumerate(list(occ_data.items())[:10]):
    print(f"  {code}: {data['title']}")

# ============================================================================
# 3. EXTRACT SKILLS METADATA
# ============================================================================

print("\n[3] EXTRACTING SKILLS METADATA")
print("-" * 100)

skills_metadata = {}

# Identify skill ID and name columns
skill_id_col = None
skill_name_col = None

for col in skills_df.columns:
    if 'id' in col.lower() and 'element' not in col.lower():
        skill_id_col = col
    if 'name' in col.lower():
        skill_name_col = col

print(f"  Using Skill ID Column: {skill_id_col}")
print(f"  Using Skill Name Column: {skill_name_col}")

if skill_id_col and skill_name_col:
    for idx, row in skills_df.iterrows():
        skill_id = str(row[skill_id_col]).strip()
        skill_name = str(row[skill_name_col]).strip()
        if skill_id and skill_id != 'nan' and skill_name:
            if skill_id not in skills_metadata:
                skills_metadata[skill_id] = skill_name

print(f"✓ Extracted {len(skills_metadata)} unique skills")
print(f"\nSample skills:")
for i, (skill_id, name) in enumerate(list(skills_metadata.items())[:15]):
    print(f"  {skill_id:20s}: {name}")

# ============================================================================
# 4. BUILD OCCUPATION-SKILL MAPPING
# ============================================================================

print("\n[4] BUILDING OCCUPATION-SKILL MAPPING")
print("-" * 100)

# Initialize occupation skill profiles
for code in occ_data.keys():
    occ_data[code]['skills'] = []

# Map skills to occupations
code_col_skills = None
for col in skills_df.columns:
    if 'code' in col.lower() or 'occ' in col.lower():
        code_col_skills = col
        break

if code_col_skills and skill_id_col:
    skills_per_occ = {}
    for idx, row in skills_df.iterrows():
        occ_code = str(row[code_col_skills]).strip()
        skill_id = str(row[skill_id_col]).strip()
        
        if occ_code in occ_data and skill_id in skills_metadata:
            if occ_code not in skills_per_occ:
                skills_per_occ[occ_code] = []
            skills_per_occ[occ_code].append((skill_id, skills_metadata[skill_id]))
    
    print(f"✓ Mapped skills to occupations")
    print(f"  Occupations with skills: {len(skills_per_occ)}")
    
    # Show distribution
    skill_counts = [len(v) for v in skills_per_occ.values()]
    print(f"  Average skills per occupation: {np.mean(skill_counts):.1f}")
    print(f"  Median skills per occupation: {np.median(skill_counts):.1f}")
    
    print(f"\nSample occupation-skill mapping:")
    for i, (code, skills) in enumerate(list(skills_per_occ.items())[:3]):
        title = occ_data[code]['title']
        print(f"  {code}: {title}")
        for skill_id, skill_name in skills[:5]:
            print(f"    - {skill_name}")

# ============================================================================
# 5. CREATE SKILL FREQUENCY ANALYSIS
# ============================================================================

print("\n[5] ANALYZING SKILL FREQUENCIES")
print("-" * 100)

if 'skills_per_occ' in locals():
    # Count skill occurrences
    skill_frequency = {}
    for occ_code, skill_list in skills_per_occ.items():
        for skill_id, skill_name in skill_list:
            if skill_id not in skill_frequency:
                skill_frequency[skill_id] = {
                    'name': skill_name,
                    'occurrences': 0,
                    'occupation_codes': []
                }
            skill_frequency[skill_id]['occurrences'] += 1
            skill_frequency[skill_id]['occupation_codes'].append(occ_code)
    
    # Sort by frequency
    top_skills = sorted(skill_frequency.items(), 
                       key=lambda x: x[1]['occurrences'], 
                       reverse=True)
    
    print(f"✓ Analyzed {len(skill_frequency)} unique skills across occupations")
    print(f"\nTop 25 most common skills in O*NET:")
    for i, (skill_id, info) in enumerate(top_skills[:25], 1):
        freq_pct = info['occurrences'] / len(occ_data) * 100
        print(f"  {i:2d}. {info['name']:40s} - {info['occurrences']:4d} ({freq_pct:5.1f}%)")

# ============================================================================
# 6. CLASSIFY OCCUPATIONS BY ROLE FAMILY
# ============================================================================

print("\n[6] CLASSIFYING OCCUPATIONS BY ROLE FAMILY")
print("-" * 100)

role_keywords = {
    'technical': ['software', 'developer', 'engineer', 'programmer', 'architect', 'data', 'science', 'analyst', 'tech', 'it ', 'system', 'network', 'database', 'admin'],
    'operations': ['operator', 'supervisor', 'technician', 'worker', 'specialist', 'production', 'assembly', 'maintenance', 'coordinator'],
    'management': ['manager', 'director', 'executive', 'chief', 'president', 'officer', 'administrator', 'supervisor'],
    'sales': ['sales', 'representative', 'agent', 'business development'],
    'customer_service': ['customer', 'support', 'service', 'help', 'agent', 'representative'],
    'medical': ['nurse', 'doctor', 'physician', 'medical', 'therapist', 'dentist', 'surgeon'],
    'education': ['teacher', 'instructor', 'professor', 'educator', 'trainer'],
}

occ_families = {}
for code, data in occ_data.items():
    title_lower = data['title'].lower()
    best_family = 'general'
    best_matches = 0
    
    for family, keywords in role_keywords.items():
        matches = sum(1 for kw in keywords if kw in title_lower)
        if matches > best_matches:
            best_matches = matches
            best_family = family
    
    occ_families[code] = best_family

# Count by family
from collections import Counter
family_counts = Counter(occ_families.values())

print(f"Occupations by role family:")
for family, count in family_counts.most_common():
    pct = count / len(occ_data) * 100
    print(f"  {family:20s}: {count:4d} ({pct:5.1f}%)")

# ============================================================================
# 7. CREATE ENHANCED TRAINING DATA
# ============================================================================

print("\n[7] CREATING ENHANCED TRAINING DATA")
print("-" * 100)

# Create skill-occupation matrix for training
training_texts = []
training_metadata = []

if 'skills_per_occ' in locals():
    for occ_code, skill_list in skills_per_occ.items():
        # Create text from occupation title + skill names
        text_parts = [occ_data[occ_code]['title']]
        text_parts.extend([skill_name for _, skill_name in skill_list[:10]])  # Top 10 skills
        
        text = ' '.join(text_parts)
        training_texts.append(text)
        training_metadata.append({
            'code': occ_code,
            'title': occ_data[occ_code]['title'],
            'family': occ_families[occ_code],
            'num_skills': len(skill_list)
        })

print(f"✓ Created {len(training_texts)} training examples")

# Train TF-IDF model
if training_texts:
    vectorizer = TfidfVectorizer(
        max_features=1500,
        stop_words='english',
        ngram_range=(1, 2),
        min_df=3,
        max_df=0.8
    )
    tfidf_matrix = vectorizer.fit_transform(training_texts)
    
    with open('data/tfidf_onet_skills.pkl', 'wb') as f:
        pickle.dump(vectorizer, f)
    
    print(f"✓ Trained TF-IDF model on O*NET skills")
    print(f"  Vocabulary size: {len(vectorizer.get_feature_names_out())}")

# ============================================================================
# 8. SAVE COMPREHENSIVE TRAINING DATA
# ============================================================================

print("\n[8] SAVING COMPREHENSIVE TRAINING DATA")
print("-" * 100)

# Save occupation profiles
occ_profiles = []
if 'skills_per_occ' in locals():
    for occ_code, skill_list in skills_per_occ.items():
        occ_profiles.append({
            'code': occ_code,
            'title': occ_data[occ_code]['title'],
            'family': occ_families[occ_code],
            'skills': [{'id': sid, 'name': sname} for sid, sname in skill_list],
            'skill_count': len(skill_list)
        })

with open('data/onet_occupation_profiles.json', 'w') as f:
    json.dump(occ_profiles, f, indent=2)

print(f"✓ Saved {len(occ_profiles)} occupation profiles")

# Save skill vocabulary
with open('data/onet_skill_vocabulary.json', 'w') as f:
    json.dump({
        'total_skills': len(skills_metadata),
        'skill_frequency': {k: v['occurrences'] for k, v in skill_frequency.items()} if 'skill_frequency' in locals() else {},
        'top_skills': [{'id': k, 'name': v['name'], 'occurrences': v['occurrences']} 
                      for k, v in top_skills[:50]] if 'top_skills' in locals() else []
    }, f, indent=2)

print(f"✓ Saved skill vocabulary")

# Save training summary
summary = {
    'source': 'O*NET Database 30.1',
    'total_occupations_processed': len(occ_data),
    'total_unique_skills': len(skills_metadata),
    'occupations_with_skills': len(occ_profiles) if 'occ_profiles' in locals() else 0,
    'role_families': dict(family_counts),
    'models_trained': [
        'tfidf_onet_skills.pkl'
    ],
    'generated_files': [
        'data/onet_occupation_profiles.json',
        'data/onet_skill_vocabulary.json',
        'data/tfidf_onet_skills.pkl'
    ]
}

with open('data/onet_training_summary.json', 'w') as f:
    json.dump(summary, f, indent=2)

print(f"✓ Saved training summary")

# ============================================================================
# 9. FINAL REPORT
# ============================================================================

print("\n" + "=" * 100)
print("O*NET TRAINING COMPLETE")
print("=" * 100)

print(f"\nDATASET STATISTICS:")
print(f"  • Total occupations extracted: {len(occ_data)}")
print(f"  • Occupations with skills mapped: {len(occ_profiles)}")
print(f"  • Total unique skills: {len(skills_metadata)}")
print(f"  • Average skills per occupation: {np.mean([p['skill_count'] for p in occ_profiles]):.1f}")

print(f"\nROLE FAMILY DISTRIBUTION:")
for family, count in sorted(family_counts.items(), key=lambda x: x[1], reverse=True):
    pct = count / len(occ_data) * 100
    print(f"  • {family:20s}: {count:4d} ({pct:5.1f}%)")

print(f"\nMODELS AND DATA GENERATED:")
for file in summary['generated_files']:
    if Path(file).exists():
        size = Path(file).stat().st_size
        print(f"  ✓ {file:50s} ({size:>10,} bytes)")

print("\n" + "=" * 100)
print("Ready for next phase: Model evaluation and testing")
print("=" * 100)
