"""
Machine Learning engines for Eaglearn.
Includes gaze estimation, head pose estimation, audio stress analysis, and
integration pipeline utilities.
"""

from backend.ml.gaze_estimator import get_gaze_estimator
from backend.ml.stress_analyzer import get_stress_analyzer
from backend.ml.integration import IntegrationPipeline

__all__ = [
    "get_gaze_estimator",
    "get_stress_analyzer",
    "IntegrationPipeline",
]
