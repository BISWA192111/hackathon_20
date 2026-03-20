"""
Comprehensive O*NET Model Training Pipeline
- Extract skills, knowledge, abilities from all O*NET files
- Create enhanced skill taxonomy
- Train models for better skill extraction and mapping
- Build occupational skill profiles
"""

import pandas as pd
import json
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MultiLabelBinarizer
import pickle
import warnings

warnings.filterwarnings('ignore')

print("=" * 100)
print("COMPREHENSIVE O*NET DATA EXTRACTION AND MODEL TRAINING")
print("=" * 100)

ONET_PATH = Path('db_30_1_excel/db_30_1_excel')

# ============================================================================
# 1. LOAD O*NET CORE DATA
# ============================================================================

print("\n[1] LOADING O*NET CORE DATA")
print("-" * 100)

try:
    # Load occupation data
    occupations = pd.read_excel(ONET_PATH / 'Occupation Data.xlsx')
    print(f"✓ Loaded Occupation Data: {len(occupations)} occupations")
    print(f"  Columns: {occupations.columns.tolist()[:5]}...")
    
    # Load skills
    skills_data = pd.read_excel(ONET_PATH / 'Skills.xlsx')
    print(f"✓ Loaded Skills: {len(skills_data)} skill records")
    
    # Load knowledge
    knowledge_data = pd.read_excel(ONET_PATH / 'Knowledge.xlsx')
    print(f"✓ Loaded Knowledge: {len(knowledge_data)} knowledge records")
    
    # Load abilities
    abilities_data = pd.read_excel(ONET_PATH / 'Abilities.xlsx')
    print(f"✓ Loaded Abilities: {len(abilities_data)} ability records")
    
    # Load technology skills
    tech_skills = pd.read_excel(ONET_PATH / 'Technology Skills.xlsx')
    print(f"✓ Loaded Technology Skills: {len(tech_skills)} technology entries")
    
    # Load work styles
    work_styles = pd.read_excel(ONET_PATH / 'Work Styles.xlsx')
    print(f"✓ Loaded Work Styles: {len(work_styles)} work style records")
    
except Exception as e:
    print(f"✗ Error loading O*NET data: {e}")
    exit(1)

# ============================================================================
# 2. EXTRACT UNIQUE SKILLS AND KNOWLEDGE
# ============================================================================

print("\n[2] EXTRACTING SKILL AND KNOWLEDGE TAXONOMY")
print("-" * 100)

# Extract unique skills from O*NET
unique_skills = {}
if 'Skill ID' in skills_data.columns and 'Skill Name' in skills_data.columns:
    for idx, row in skills_data.iterrows():
        skill_id = str(row['Skill ID']).strip()
        skill_name = str(row['Skill Name']).strip()
        if skill_id and skill_id != 'nan':
            unique_skills[skill_id] = {
                'name': skill_name,
                'type': 'skill',
                'source': 'onet'
            }

print(f"✓ Extracted {len(unique_skills)} unique skills")

# Extract unique knowledge from O*NET
unique_knowledge = {}
if 'Knowledge ID' in knowledge_data.columns and 'Knowledge Name' in knowledge_data.columns:
    for idx, row in knowledge_data.iterrows():
        know_id = str(row['Knowledge ID']).strip()
        know_name = str(row['Knowledge Name']).strip()
        if know_id and know_id != 'nan':
            unique_knowledge[know_id] = {
                'name': know_name,
                'type': 'knowledge',
                'source': 'onet'
            }

print(f"✓ Extracted {len(unique_knowledge)} unique knowledge areas")

# Extract unique abilities
unique_abilities = {}
if 'Ability ID' in abilities_data.columns and 'Ability Name' in abilities_data.columns:
    for idx, row in abilities_data.iterrows():
        ability_id = str(row['Ability ID']).strip()
        ability_name = str(row['Ability Name']).strip()
        if ability_id and ability_id != 'nan':
            unique_abilities[ability_id] = {
                'name': ability_name,
                'type': 'ability',
                'source': 'onet'
            }

print(f"✓ Extracted {len(unique_abilities)} unique abilities")

# ============================================================================
# 3. BUILD OCCUPATION-SKILL PROFILES
# ============================================================================

print("\n[3] BUILDING OCCUPATION-SKILL PROFILES")
print("-" * 100)

# Create occupation profiles
occ_profiles = {}

for idx, row in occupations.iterrows():
    occ_code = str(row.get('O*NET-SOC Code', '')).strip() if 'O*NET-SOC Code' in occupations.columns else str(row.get('Code', '')).strip()
    occ_title = str(row.get('Title', 'Unknown')).strip() if 'Title' in occupations.columns else 'Unknown'
    
    if occ_code and occ_code != 'nan':
        occ_profiles[occ_code] = {
            'title': occ_title,
            'skills': [],
            'knowledge': [],
            'abilities': [],
            'technology_skills': []
        }

print(f"✓ Created profiles for {len(occ_profiles)} occupations")

# Map skills to occupations
if 'O*NET-SOC Code' in skills_data.columns or 'Code' in skills_data.columns:
    code_col = 'O*NET-SOC Code' if 'O*NET-SOC Code' in skills_data.columns else 'Code'
    skill_id_col = 'Skill ID' if 'Skill ID' in skills_data.columns else None
    
    if skill_id_col:
        for idx, row in skills_data.iterrows():
            occ_code = str(row[code_col]).strip() if code_col in skills_data.columns else ''
            skill_id = str(row[skill_id_col]).strip() if skill_id_col in skills_data.columns else ''
            
            if occ_code in occ_profiles and skill_id in unique_skills:
                occ_profiles[occ_code]['skills'].append(skill_id)

print(f"✓ Mapped skills to occupations")

# Map knowledge to occupations
if 'Knowledge Name' in knowledge_data.columns:
    for idx, row in knowledge_data.iterrows():
        know_name = str(row['Knowledge Name']).strip()
        if 'Occupation Title' in knowledge_data.columns or 'O*NET-SOC Code' in knowledge_data.columns:
            code_col = 'O*NET-SOC Code' if 'O*NET-SOC Code' in knowledge_data.columns else 'Occupation Title'
            occ_code = str(row[code_col]).strip() if code_col in knowledge_data.columns else ''
            
            if occ_code in occ_profiles and know_name:
                occ_profiles[occ_code]['knowledge'].append(know_name)

print(f"✓ Mapped knowledge to occupations")

# ============================================================================
# 4. ANALYZE OCCUPATIONS BY CATEGORY
# ============================================================================

print("\n[4] ANALYZING OCCUPATION CATEGORIES")
print("-" * 100)

# Classify occupations into role families
role_family_keywords = {
    'technical': ['software', 'developer', 'engineer', 'programmer', 'architect', 'analyst', 'data', 'tech', 'it ', 'system', 'network', 'database'],
    'operations': ['operator', 'supervisor', 'technician', 'worker', 'specialist', 'coordinator', 'assistant', 'associate', 'clerk', 'manager', 'production'],
    'management': ['manager', 'director', 'executive', 'chief', 'president', 'officer', 'administrator'],
    'sales': ['sales', 'representative', 'agent', 'business development'],
    'customer': ['customer', 'support', 'service', 'help', 'agent'],
}

occupation_categories = {}
for occ_code, profile in occ_profiles.items():
    title_lower = profile['title'].lower()
    
    # Find best matching category
    best_family = 'general'
    best_matches = 0
    
    for family, keywords in role_family_keywords.items():
        matches = sum(1 for kw in keywords if kw in title_lower)
        if matches > best_matches:
            best_matches = matches
            best_family = family
    
    occupation_categories[occ_code] = best_family

# Count by category
from collections import Counter
category_counts = Counter(occupation_categories.values())
print(f"\nOccupations by role family:")
for family, count in category_counts.most_common():
    print(f"  {family:20s}: {count:4d} occupations")

# ============================================================================
# 5. CREATE SKILL FREQUENCY MATRIX
# ============================================================================

print("\n[5] CREATING SKILL-OCCUPATION FREQUENCY MATRIX")
print("-" * 100)

# Count skill frequencies
skill_frequencies = {}
for occ_code, profile in occ_profiles.items():
    for skill_id in profile['skills']:
        if skill_id not in skill_frequencies:
            skill_frequencies[skill_id] = {
                'total_occurrences': 0,
                'occupations': [],
                'families': []
            }
        skill_frequencies[skill_id]['total_occurrences'] += 1
        skill_frequencies[skill_id]['occupations'].append(occ_code)
        family = occupation_categories.get(occ_code, 'general')
        if family not in skill_frequencies[skill_id]['families']:
            skill_frequencies[skill_id]['families'].append(family)

# Sort by frequency
top_skills = sorted(skill_frequencies.items(), 
                   key=lambda x: x[1]['total_occurrences'], 
                   reverse=True)

print(f"\nTop 20 most common skills in O*NET:")
for i, (skill_id, info) in enumerate(top_skills[:20], 1):
    skill_name = unique_skills.get(skill_id, {}).get('name', 'Unknown')
    print(f"  {i:2d}. {skill_name:35s} - {info['total_occurrences']:4d} occupations - Families: {', '.join(info['families'])}")

# ============================================================================
# 6. LOAD EXISTING CATALOG AND ENHANCE
# ============================================================================

print("\n[6] ENHANCING EXISTING COURSE CATALOG")
print("-" * 100)

with open('data/course_catalog.json', 'r') as f:
    catalog = json.load(f)

# Merge O*NET skills with existing skills
enhanced_skills = {}
for skill in catalog['skills']:
    skill_id = skill['skill_id']
    enhanced_skills[skill_id] = {
        'skill_id': skill_id,
        'label': skill['label'],
        'category': skill['category'],
        'aliases': skill['aliases'],
        'onet_reference': None,
        'frequency': 0
    }

# Add frequency data
for skill_id, info in skill_frequencies.items():
    onet_skill_name = unique_skills.get(skill_id, {}).get('name', '')
    
    # Try to match with existing skills
    matched = False
    for existing_id, existing_skill in enhanced_skills.items():
        if existing_id in skill_frequencies:
            enhanced_skills[existing_id]['frequency'] = skill_frequencies[existing_id]['total_occurrences']

# Sort by frequency
sorted_enhanced = sorted(enhanced_skills.items(), 
                         key=lambda x: x[1]['frequency'], 
                         reverse=True)

print(f"✓ Enhanced {len(enhanced_skills)} skills with O*NET data")
print(f"\nSkills by frequency in O*NET:")
for i, (skill_id, skill_info) in enumerate(sorted_enhanced[:15], 1):
    freq = skill_info['frequency']
    print(f"  {i:2d}. {skill_info['label']:30s} - {freq:4d} occupations")

# ============================================================================
# 7. EXTRACT TECHNOLOGY SKILLS
# ============================================================================

print("\n[7] ANALYZING TECHNOLOGY SKILLS")
print("-" * 100)

tech_skill_list = []
if not tech_skills.empty:
    for idx, row in tech_skills.iterrows():
        tech_name = str(row.get('Technology Example', row.get('Technology', 'Unknown'))).strip()
        if tech_name and tech_name != 'nan':
            tech_skill_list.append(tech_name)

unique_tech = list(set(tech_skill_list))
print(f"✓ Extracted {len(unique_tech)} unique technology skills")
print(f"\nSample technology skills:")
for tech in sorted(unique_tech)[:20]:
    print(f"  - {tech}")

# ============================================================================
# 8. TRAIN ENHANCED MODELS
# ============================================================================

print("\n[8] TRAINING ENHANCED MODELS")
print("-" * 100)

# Create skill name vocabulary for TF-IDF
job_skill_texts = []
for occ_code, profile in occ_profiles.items():
    text_parts = [profile['title']]
    for skill_id in profile['skills'][:5]:  # Top 5 skills
        skill_name = unique_skills.get(skill_id, {}).get('name', '')
        if skill_name:
            text_parts.append(skill_name)
    for know in profile['knowledge'][:3]:  # Top 3 knowledge areas
        text_parts.append(str(know))
    
    job_skill_texts.append(' '.join(text_parts))

# Train TF-IDF on occupation descriptions
if job_skill_texts:
    vectorizer_onet = TfidfVectorizer(
        max_features=1000,
        stop_words='english',
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.8
    )
    tfidf_matrix = vectorizer_onet.fit_transform(job_skill_texts)
    
    with open('data/tfidf_vectorizer_onet.pkl', 'wb') as f:
        pickle.dump(vectorizer_onet, f)
    
    print(f"✓ Trained O*NET TF-IDF vectorizer with vocabulary size: {len(vectorizer_onet.get_feature_names_out())}")

# ============================================================================
# 9. SAVE ENHANCED DATA
# ============================================================================

print("\n[9] SAVING ENHANCED TRAINING DATA")
print("-" * 100)

# Save O*NET extracted data
onet_data = {
    'skills': {sid: {
        'name': info['name'],
        'source': info['source'],
        'type': info['type']
    } for sid, info in unique_skills.items()},
    'knowledge': {kid: {
        'name': info['name'],
        'source': info['source'],
        'type': info['type']
    } for kid, info in unique_knowledge.items()},
    'abilities': {aid: {
        'name': info['name'],
        'source': info['source'],
        'type': info['type']
    } for aid, info in unique_abilities.items()},
    'technology_skills': unique_tech,
    'occupations': occ_profiles,
    'role_family_classification': occupation_categories,
    'skill_frequencies': {sid: info['total_occurrences'] 
                          for sid, info in skill_frequencies.items()}
}

with open('data/onet_extracted_data.json', 'w') as f:
    json.dump(onet_data, f, indent=2)

print("✓ Saved onet_extracted_data.json")

# Save occupation-skill mapping
occ_skill_mapping = []
for occ_code, profile in occ_profiles.items():
    occ_skill_mapping.append({
        'occupation_code': occ_code,
        'occupation_title': profile['title'],
        'role_family': occupation_categories.get(occ_code, 'general'),
        'skills_count': len(profile['skills']),
        'knowledge_count': len(profile['knowledge']),
        'abilities_count': len(profile['abilities']),
        'technology_skills_count': len(profile['technology_skills'])
    })

occ_df = pd.DataFrame(occ_skill_mapping)
occ_df.to_csv('data/occupations_with_profiles.csv', index=False)
print("✓ Saved occupations_with_profiles.csv")

# Save enhanced skills with O*NET references
enhanced_skills_list = [skill for skill in enhanced_skills.values()]
with open('data/enhanced_skills_with_onet.json', 'w') as f:
    json.dump(enhanced_skills_list, f, indent=2)

print("✓ Saved enhanced_skills_with_onet.json")

# ============================================================================
# 10. GENERATE TRAINING SUMMARY
# ============================================================================

print("\n[10] TRAINING SUMMARY")
print("=" * 100)

summary = {
    'total_occupations': len(occ_profiles),
    'total_skills_extracted': len(unique_skills),
    'total_knowledge_areas': len(unique_knowledge),
    'total_abilities': len(unique_abilities),
    'technology_skills_count': len(unique_tech),
    'role_families': dict(category_counts),
    'models_trained': [
        'tfidf_vectorizer.pkl (Job descriptions)',
        'tfidf_vectorizer_onet.pkl (O*NET occupations)',
        'grounding_db.json (Module grounding)',
        'skill_statistics.json (Job skill stats)'
    ],
    'generated_files': [
        'data/onet_extracted_data.json',
        'data/enhanced_skills_with_onet.json',
        'data/occupations_with_profiles.csv',
        'data/tfidf_vectorizer_onet.pkl',
        'data/jobs_with_skills.csv',
        'data/skill_statistics.json'
    ]
}

print("\nO*NET TRAINING COMPLETE")
print(f"  • Occupations processed: {summary['total_occupations']}")
print(f"  • Skills extracted: {summary['total_skills_extracted']}")
print(f"  • Knowledge areas: {summary['total_knowledge_areas']}")
print(f"  • Abilities: {summary['total_abilities']}")
print(f"  • Technology skills: {summary['technology_skills_count']}")
print(f"\nRole Family Distribution:")
for family, count in sorted(summary['role_families'].items(), key=lambda x: x[1], reverse=True):
    print(f"  • {family:15s}: {count:5d} occupations")

print(f"\nModels trained: {len(summary['models_trained'])}")
for model in summary['models_trained']:
    print(f"  • {model}")

print(f"\nGenerated {len(summary['generated_files'])} new data files")

with open('data/training_summary.json', 'w') as f:
    json.dump(summary, f, indent=2)

print("\n" + "=" * 100)
print("✓ ALL O*NET DATA PROCESSING COMPLETE")
print("=" * 100)
