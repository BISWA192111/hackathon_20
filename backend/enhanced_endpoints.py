"""Enhanced backend endpoints backed by enriched extraction artifacts."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from onboarding_engine.enhanced_extractor import EnhancedSkillsExtractor

class SkillAnalysisRequest(BaseModel):
    """Request for detailed skill analysis"""
    skills: List[str]
    target_role: Optional[str] = None

class OccupationInsightRequest(BaseModel):
    """Request for occupation insights"""
    skills: List[str]
    role_family: Optional[str] = None

async def analyze_skills_enhanced(
    payload: SkillAnalysisRequest,
    extractor: Optional[EnhancedSkillsExtractor] = None,
) -> Dict[str, Any]:
    """
    Provides enhanced skill analysis using all training data
    - Skill frequencies from job market
    - Related occupations from O*NET
    - Skill recommendations
    - Market competitiveness score
    """
    if extractor is None:
        extractor = EnhancedSkillsExtractor()
    
    # Get skill frequencies (how common are these in the job market)
    skill_market_data = {}
    for skill_id in payload.skills:
        freq = extractor.get_skill_frequency(skill_id)
        skill_market_data[skill_id] = freq
    
    # Find related occupations
    related_occupations = extractor.find_related_occupations(payload.skills, limit=15)
    if not related_occupations and payload.target_role:
        fallback = extractor._find_occupations_by_title(payload.target_role, limit=10)  # noqa: SLF001
        related_occupations = [
            {
                "code": str(item.get("code", idx)),
                "title": item.get("title", "Unknown"),
                "family": item.get("family", "general"),
                "match_count": 0,
                "score": 0.0,
            }
            for idx, item in enumerate(fallback)
        ]
    
    # Get recommendations
    recommendations = extractor.enhance_skill_profile(
        {s: 1.0 for s in payload.skills},
        target_role=payload.target_role
    )
    
    # Calculate market value
    market_value_score = calculate_market_value(skill_market_data)
    
    return {
        'skills': payload.skills,
        'market_analysis': skill_market_data,
        'related_occupations': related_occupations,
        'recommendations': recommendations,
        'market_value_score': market_value_score,
        'insights': generate_skill_insights(skill_market_data, related_occupations)
    }

async def get_occupation_insights(
    payload: OccupationInsightRequest,
    extractor: Optional[EnhancedSkillsExtractor] = None,
) -> Dict[str, Any]:
    """
    Provides insights about occupations matching given skills
    - Occupations with detailed profiles
    - Skill gaps to target occupations
    - Career pathways
    - Industry trends
    """
    if extractor is None:
        extractor = EnhancedSkillsExtractor()
    
    # Determine role family
    role_family = payload.role_family or determine_role_family(payload.skills)
    
    # Get relevant O*NET occupations
    occupations = extractor.find_related_occupations(payload.skills, limit=20)
    
    # Filter by role family if specified
    if payload.role_family:
        occupations = [o for o in occupations if o['family'] == payload.role_family][:10]
    
    # For each occupation, calculate skill gaps
    gaps = []
    for occ in occupations:
        gaps.append({"occupation": occ["title"], "gap_analysis": calculate_occupation_gap(payload.skills, occ)})
    
    return {
        'role_family': role_family,
        'current_skills': payload.skills,
        'matching_occupations': occupations,
        'gap_analysis': gaps,
        'career_pathways': generate_career_pathways(occupations, payload.skills)
    }

def calculate_market_value(skill_market_data: Dict) -> float:
    """
    Calculate how valuable these skills are in the job market (0-100)
    Higher score = more in-demand skills
    """
    commonality_scores = {
        'very_common': 100,
        'common': 85,
        'moderate': 60,
        'rare': 40
    }
    
    scores = []
    for skill_id, freq_data in skill_market_data.items():
        commonality = freq_data['commonality']
        scores.append(commonality_scores.get(commonality, 50))
    
    if not scores:
        return 50.0
    
    return round(sum(scores) / len(scores), 1)

def determine_role_family(skills: List[str]) -> str:
    """Determine if skills align with technical, operations, etc."""
    technical_keywords = ['python', 'sql', 'git', 'api', 'cloud', 'linux', 'testing', 'data']
    ops_keywords = ['compliance', 'safety', 'quality_control', 'inventory', 'equipment']
    
    tech_count = sum(1 for s in skills if any(kw in s.lower() for kw in technical_keywords))
    ops_count = sum(1 for s in skills if any(kw in s.lower() for kw in ops_keywords))
    
    if tech_count > ops_count:
        return 'technical'
    elif ops_count > tech_count:
        return 'operations'
    return 'general'

def calculate_occupation_gap(current_skills: List[str], occupation: Dict) -> Dict:
    """Calculate skill gaps between current and target occupation"""
    return {
        "occupation": occupation.get("title", "Unknown"),
        "current_skills_match": occupation.get("match_count", 0),
        "total_required": occupation.get("skills_count", occupation.get("match_count", 0)),
        "coverage_percentage": round(occupation.get("score", 0) * 100, 1),
    }

def generate_skill_insights(market_data: Dict, occupations: List[Dict]) -> List[str]:
    """Generate human-readable insights"""
    insights = []
    
    if occupations:
        top_occ = occupations[0] if occupations else None
        if top_occ:
            insights.append(f"Your skills are well-matched for {top_occ['title']} roles")
    
    # Assess commonality
    common_count = sum(1 for d in market_data.values() if d['commonality'] in ['very_common', 'common'])
    rare_count = sum(1 for d in market_data.values() if d['commonality'] == 'rare')
    
    if common_count > len(market_data) * 0.6:
        insights.append("You have highly marketable, in-demand skills")
    
    if rare_count > 0:
        insights.append(f"You have {rare_count} specialized skill(s) that differentiate you")
    
    return insights

def generate_career_pathways(occupations: List[Dict], current_skills: List[str]) -> List[Dict]:
    """Generate possible career pathways"""
    if not occupations:
        return []
    
    pathways = []
    for i, occ in enumerate(occupations[:5]):  # Top 5 matching occupations
        opportunity_level = "High" if occ['score'] > 0.7 else "Medium" if occ['score'] > 0.4 else "Low"
        pathways.append({
            'pathway_number': i + 1,
            'target_occupation': occ['title'],
            'opportunity_level': opportunity_level,
            'match_percentage': round(occ['score'] * 100, 1),
            'role_family': occ['family']
        })
    
    return pathways
