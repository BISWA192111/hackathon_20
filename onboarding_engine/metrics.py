"""
Metrics Calculation System
- Readiness score
- Coverage ratio
- Hours saved
- Optimization efficiency
"""

from typing import Dict, List, Optional
import json
from pathlib import Path


class MetricsCalculator:
    """Calculate performance metrics for the adaptive pathway"""
    
    def __init__(self, min_mastery: float = 0.75, catalog_path: Optional[str] = None):
        self.min_mastery = min_mastery
        resolved_catalog = Path(catalog_path) if catalog_path else Path("data/course_catalog.json")
        self.catalog = json.loads(resolved_catalog.read_text(encoding="utf-8"))
        self.module_map = {m['module_id']: m for m in self.catalog['modules']}
        self.skill_map = {s['skill_id']: s for s in self.catalog['skills']}
    
    def calculate_readiness_score(self, 
                                  current_skills: Dict[str, float],
                                  target_skills: Dict[str, float]) -> Dict:
        """
        Calculate readiness score (0-100)
        
        Args:
            current_skills: {skill_id: mastery_level (0-1)}
            target_skills: {skill_id: required_mastery (0-1)}
        
        Returns:
            Readiness metrics
        """
        if not target_skills:
            return {
                'readiness_score': 100.0,
                'status': 'ready',
                'assessment': 'No specific skills required'
            }
        
        # Calculate alignment for each target skill
        alignments = []
        for skill_id, required in target_skills.items():
            current = current_skills.get(skill_id, 0.0)
            alignment = min(current / required, 1.0) * 100 if required > 0 else 100.0
            alignments.append(alignment)
        
        readiness_score = sum(alignments) / len(alignments) if alignments else 0.0
        
        # Determine status
        if readiness_score >= 90:
            status = 'ready'
            assessment = 'Candidate is well-prepared for the role'
        elif readiness_score >= 70:
            status = 'mostly_ready'
            assessment = 'Candidate has most required skills, minor gaps exist'
        elif readiness_score >= 50:
            status = 'partially_ready'
            assessment = 'Candidate has foundational skills, significant training needed'
        else:
            status = 'not_ready'
            assessment = 'Candidate requires substantial training'
        
        return {
            'readiness_score': round(readiness_score, 2),
            'status': status,
            'assessment': assessment,
            'confidence': 0.95
        }
    
    def calculate_coverage_ratio(self,
                                  gap_skills: List[str],
                                  roadmap_modules: List[str]) -> Dict:
        """
        Calculate what percentage of skill gaps are covered by the roadmap
        
        Args:
            gap_skills: List of skill IDs that need to be learned
            roadmap_modules: List of module IDs in the recommended pathway
        
        Returns:
            Coverage metrics
        """
        if not gap_skills:
            return {
                'coverage_ratio': 1.0,
                'coverage_percentage': 100.0,
                'gaps_covered': 0,
                'gaps_total': 0,
                'assessment': 'All skill gaps are addressed'
            }
        
        # Collect all skills covered by roadmap modules
        covered_skills = set()
        for module_id in roadmap_modules:
            module = self.module_map.get(module_id, {})
            covered_skills.update(module.get('skills', []))
        
        # Calculate coverage
        gap_set = set(gap_skills)
        gaps_covered = len(gap_set.intersection(covered_skills))
        gaps_total = len(gap_set)
        coverage_ratio = gaps_covered / gaps_total if gaps_total > 0 else 0.0
        
        return {
            'coverage_ratio': round(coverage_ratio, 3),
            'coverage_percentage': round(coverage_ratio * 100, 1),
            'gaps_covered': gaps_covered,
            'gaps_total': gaps_total,
            'uncovered_gaps': list(gap_set - covered_skills),
            'assessment': self._coverage_assessment(coverage_ratio)
        }
    
    def calculate_time_efficiency(self,
                                   roadmap_modules: List[str],
                                   full_catalog_modules: List[str] = None) -> Dict:
        """
        Calculate training time optimization
        
        Args:
            roadmap_modules: Recommended learning pathway
            full_catalog_modules: All available modules (if None, uses all catalog)
        
        Returns:
            Time metrics
        """
        # Calculate optimized training time
        optimized_hours = sum(
            self.module_map.get(m_id, {}).get('duration_hours', 0)
            for m_id in roadmap_modules
        )
        
        # Calculate full curriculum time
        if full_catalog_modules:
            full_hours = sum(
                self.module_map.get(m_id, {}).get('duration_hours', 0)
                for m_id in full_catalog_modules
            )
        else:
            full_hours = sum(m.get('duration_hours', 0) for m in self.catalog['modules'])
        
        hours_saved = full_hours - optimized_hours
        efficiency = (hours_saved / full_hours * 100) if full_hours > 0 else 0.0
        
        return {
            'optimized_hours': round(optimized_hours, 1),
            'full_curriculum_hours': round(full_hours, 1),
            'hours_saved': round(hours_saved, 1),
            'efficiency_percentage': round(efficiency, 1),
            'modules_selected': len(roadmap_modules),
            'modules_total': len(self.catalog['modules']),
            'assessment': f'Training time reduced by {efficiency:.0f}%'
        }
    
    def calculate_residual_gap(self,
                               current_skills: Dict[str, float],
                               target_skills: Dict[str, float],
                               roadmap_modules: List[str]) -> Dict:
        """
        Calculate remaining skill gaps after completing the roadmap
        
        Args:
            current_skills: Current skill levels
            target_skills: Target skill levels
            roadmap_modules: Modules to be completed
        
        Returns:
            Residual gap analysis
        """
        # Project skills after completing roadmap
        # Assume each module brings learner from 0 to 0.9 proficiency on required skills
        projected_skills = current_skills.copy()
        
        for module_id in roadmap_modules:
            module = self.module_map.get(module_id, {})
            for skill_id in module.get('skills', []):
                # Learning assumes reaching 0.85 of target mastery
                target_mastery = target_skills.get(skill_id, 0.7)
                projected_skills[skill_id] = min(target_mastery * 0.85, 1.0)
        
        # Calculate residual gaps
        residual_gaps = []
        for skill_id, target_level in target_skills.items():
            projected = projected_skills.get(skill_id, 0.0)
            gap = max(target_level - projected, 0.0)
            if gap > 0.05:  # Only count gaps > 5%
                residual_gaps.append({
                    'skill_id': skill_id,
                    'skill_label': self.skill_map.get(skill_id, {}).get('label', 'Unknown'),
                    'target_level': target_level,
                    'projected_level': round(projected, 2),
                    'residual_gap': round(gap, 2)
                })
        
        # Sort by gap size (largest first)
        residual_gaps = sorted(residual_gaps, key=lambda x: x['residual_gap'], reverse=True)
        
        total_residual = sum(g['residual_gap'] for g in residual_gaps)
        
        return {
            'residual_gaps': residual_gaps,
            'total_residual_gap': round(total_residual, 2),
            'gaps_remain': len(residual_gaps),
            'expected_readiness': round(
                sum(min(projected_skills.get(s, 0.0) / target_skills.get(s, 1.0), 1.0)
                    for s in target_skills) / len(target_skills) * 100
                if target_skills else 100, 1
            ),
            'assessment': 'Roadmap addresses key gaps. Additional on-the-job learning recommended.'
        }
    
    def calculate_complete_metrics(self,
                                   current_skills: Dict[str, float],
                                   target_skills: Dict[str, float],
                                   gap_skills: List[str],
                                   roadmap_modules: List[str]) -> Dict:
        """Calculate all metrics and return comprehensive report"""
        
        return {
            'readiness': self.calculate_readiness_score(current_skills, target_skills),
            'coverage': self.calculate_coverage_ratio(gap_skills, roadmap_modules),
            'efficiency': self.calculate_time_efficiency(roadmap_modules),
            'residual_gaps': self.calculate_residual_gap(
                current_skills, target_skills, roadmap_modules
            )
        }
    
    @staticmethod
    def _coverage_assessment(ratio: float) -> str:
        """Generate assessment based on coverage ratio"""
        if ratio >= 0.95:
            return 'Excellent: Roadmap covers almost all skill gaps'
        elif ratio >= 0.80:
            return 'Good: Roadmap covers most critical skill gaps'
        elif ratio >= 0.60:
            return 'Adequate: Roadmap covers majority of gaps, some follow-up needed'
        else:
            return 'Limited: Roadmap addresses key gaps, significant self-learning required'
