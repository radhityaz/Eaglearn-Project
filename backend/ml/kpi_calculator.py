"""
KPI Calculator for productivity metrics.
Aggregates gaze, pose, and stress data into productivity scores.
"""

import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class KPICalculator:
    """
    Calculates productivity KPIs from ML engine outputs.
    Aggregates gaze, pose, and stress metrics.
    """
    
    def __init__(self):
        """Initialize KPI calculator."""
        # Weights for overall productivity score
        self.weights = {
            'focus': 0.35,
            'engagement': 0.25,
            'stress': 0.20,
            'posture': 0.20
        }
        logger.info("KPI calculator initialized")
    
    def calculate_productivity_metrics(
        self,
        gaze_data: List[Dict],
        pose_data: List[Dict],
        stress_data: List[Dict],
        window_start: datetime,
        window_end: datetime
    ) -> Dict:
        """
        Calculate productivity metrics for a time window.
        
        Args:
            gaze_data: List of gaze measurements
            pose_data: List of pose measurements
            stress_data: List of stress measurements
            window_start: Window start time
            window_end: Window end time
            
        Returns:
            Dictionary with productivity metrics:
            {
                'focus_score': float,
                'engagement_score': float,
                'stress_score': float,
                'posture_score': float,
                'overall_productivity': float,
                'window_start': datetime,
                'window_end': datetime
            }
        """
        try:
            focus_score = self._calculate_focus_score(gaze_data)
            engagement_score = self._calculate_engagement_score(gaze_data, pose_data)
            stress_score = self._calculate_stress_score(stress_data)
            posture_score = self._calculate_posture_score(pose_data)
            overall_productivity = (
                self.weights['focus'] * focus_score +
                self.weights['engagement'] * engagement_score +
                self.weights['stress'] * stress_score +
                self.weights['posture'] * posture_score
            )
            return {
                'focus_score': float(focus_score),
                'engagement_score': float(engagement_score),
                'stress_score': float(stress_score),
                'posture_score': float(posture_score),
                'overall_productivity': float(overall_productivity),
                'window_start': window_start,
                'window_end': window_end
            }
        except Exception as e:
            logger.error(f"KPI calculation error: {str(e)}")
            return self._get_default_metrics(window_start, window_end)
    
    def _calculate_focus_score(self, gaze_data: List[Dict]) -> float:
        """
        Calculate focus score from gaze data.
        Higher score = more focused (gaze on screen center).
        """
        if not gaze_data:
            return 0.5
        
        distances = []
        for gaze in gaze_data:
            if gaze.get('confidence', 0) > 0.5:
                dx = gaze['gaze_x'] - 0.5
                dy = gaze['gaze_y'] - 0.5
                distance = (dx**2 + dy**2) ** 0.5
                distances.append(distance)
        
        if not distances:
            return 0.5
        
        avg_distance = np.mean(distances)
        focus_score = max(0.0, 1.0 - (avg_distance * 2.0))
        return float(focus_score)
    
    def _calculate_engagement_score(
        self,
        gaze_data: List[Dict],
        pose_data: List[Dict]
    ) -> float:
        """
        Calculate engagement score from gaze and pose data.
        Higher score = more engaged (looking at screen + good posture).
        """
        if not gaze_data and not pose_data:
            return 0.5
        
        # Gaze engagement: high confidence detections
        gaze_engagement = 0.5
        if gaze_data:
            high_conf = [g for g in gaze_data if g.get('confidence', 0) > 0.7]
            gaze_engagement = len(high_conf) / len(gaze_data)
        
        # Pose engagement: face detected and looking forward
        pose_engagement = 0.5
        if pose_data:
            good_poses = [
                p for p in pose_data 
                if abs(p.get('yaw', 0)) < 20 and abs(p.get('pitch', 0)) < 20
            ]
            pose_engagement = len(good_poses) / len(pose_data)
        
        engagement_score = (gaze_engagement + pose_engagement) / 2.0
        return float(engagement_score)
    
    def _calculate_stress_score(self, stress_data: List[Dict]) -> float:
        """
        Calculate stress score (inverted - lower stress = higher score).
        """
        if not stress_data:
            return 0.5
        
        stress_levels = [s['stress_level'] for s in stress_data if s.get('confidence', 0) > 0.5]
        if not stress_levels:
            return 0.5
        
        avg_stress = np.mean(stress_levels)
        stress_score = 1.0 - avg_stress
        return float(stress_score)
    
    def _calculate_posture_score(self, pose_data: List[Dict]) -> float:
        """
        Calculate posture score from pose data.
        Higher score = better posture.
        """
        if not pose_data:
            return 0.5
        
        good_postures = [p for p in pose_data if p.get('posture') == 'good']
        posture_score = len(good_postures) / len(pose_data)
        return float(posture_score)
    
    def _get_default_metrics(self, window_start: datetime, window_end: datetime) -> Dict:
        """Get default metrics when calculation fails."""
        return {
            'focus_score': 0.5,
            'engagement_score': 0.5,
            'stress_score': 0.5,
            'posture_score': 0.5,
            'overall_productivity': 0.5,
            'window_start': window_start,
            'window_end': window_end
        }


_kpi_calculator: Optional[KPICalculator] = None

def get_kpi_calculator() -> KPICalculator:
    """Get or create global KPI calculator instance."""
    global _kpi_calculator
    if _kpi_calculator is None:
        _kpi_calculator = KPICalculator()
    return _kpi_calculator
