"""
Emotion Detection Module
Analyzes facial expressions to detect emotions
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)


class EmotionDetector:
    """Detects emotions from facial metrics"""

    # Define 9 emotions with multi-factor scoring system
    EMOTIONS = [
        'neutral', 'happy', 'sad', 'angry', 'surprised',
        'confused', 'content', 'stressed', 'drowsy'
    ]

    def __init__(self, config):
        """
        Initialize emotion detector

        Args:
            config: Config object from config_loader
        """
        self.config = config
        logger.info("✅ EmotionDetector initialized")

    def detect_emotion(self, face_metrics, state):
        """
        Detect emotion from facial metrics

        Args:
            face_metrics: dict from FaceMeshProcessor
            state: SessionState object

        Returns:
            dict: Emotion detection results including:
                - emotion: str (primary emotion)
                - emotion_confidence: float (0-1)
                - emotion_scores: dict (all emotion scores)
        """
        # Extract metrics
        mar = face_metrics.get('mouth_aspect_ratio', 0)
        frown_degree = face_metrics.get('frown_degree', 0)
        lip_tension = face_metrics.get('lip_tension', 0)
        eyebrow_furrow = face_metrics.get('eyebrow_furrow', 0)
        eyebrow_raise = face_metrics.get('eyebrow_raise', 0)
        ear = face_metrics.get('eye_aspect_ratio', 0)
        yawning_duration = face_metrics.get('yawning_duration', 0)
        head_roll = face_metrics.get('head_roll', 0)

        # Initialize emotion scores
        emotion_scores = {
            'neutral': 0.5,
            'happy': 0.0,
            'sad': 0.0,
            'angry': 0.0,
            'surprised': 0.0,
            'confused': 0.0,
            'content': 0.0,
            'stressed': 0.0,
            'drowsy': 0.0
        }

        # 1. DROWSY DETECTION (highest priority)
        is_yawning = mar > self.config.get('emotion', 'yawning_mar_threshold', default=0.6)
        if is_yawning or yawning_duration > self.config.get('emotion', 'yawning_duration_threshold', default=0.5):
            emotion_scores['drowsy'] = 0.95

        # 2. HAPPY DETECTION - Multiple indicators
        if mar > 0.28:
            emotion_scores['happy'] += 0.4  # Open mouth (smile/laugh)
        elif mar > 0.22:
            emotion_scores['happy'] += 0.2

        if frown_degree < -0.005:
            emotion_scores['happy'] += 0.4  # Upward mouth corners
        elif frown_degree < -0.002:
            emotion_scores['happy'] += 0.2
            emotion_scores['content'] += 0.3

        if 0.22 < ear < 0.28:
            emotion_scores['happy'] += 0.2  # Eyes slightly crinkled

        # 3. SURPRISED DETECTION
        if eyebrow_raise > 0.12:
            emotion_scores['surprised'] += 0.5
        elif eyebrow_raise > 0.08:
            emotion_scores['surprised'] += 0.3

        if ear > 0.28:
            emotion_scores['surprised'] += 0.3  # Wide eyes
        elif ear > 0.24:
            emotion_scores['surprised'] += 0.2

        if 0.18 < mar < 0.25 and frown_degree > -0.002:
            emotion_scores['surprised'] += 0.2  # Slight mouth opening

        # 4. CONFUSED DETECTION
        if eyebrow_raise > 0.08 and ear <= 0.24:
            emotion_scores['confused'] += 0.5  # Raised eyebrows but not surprised

        if abs(head_roll) > self.config.get('emotion', 'head_tilt_threshold', default=8):
            emotion_scores['confused'] += 0.2  # Head tilt

        if 0.02 < eyebrow_furrow < 0.08:
            emotion_scores['confused'] += 0.2  # Slight furrow

        # 5. ANGRY DETECTION - STRICT requirements (use config thresholds)
        angry_frown_threshold = self.config.get('emotion', 'angry_frown_threshold', default=0.012)
        angry_frown_secondary = self.config.get('emotion', 'angry_frown_threshold', default=0.010)
        angry_eyebrow_threshold = self.config.get('emotion', 'angry_eyebrow_furrow_threshold', default=0.08)
        angry_lip_threshold = self.config.get('emotion', 'angry_lip_tension_threshold', default=0.60)
        angry_ear_min = self.config.get('emotion', 'angry_ear_min', default=0.12)
        angry_ear_max = self.config.get('emotion', 'angry_ear_max', default=0.18)

        if frown_degree > angry_frown_threshold:
            emotion_scores['angry'] += 0.4  # Significant frown
        elif frown_degree > angry_frown_secondary:
            emotion_scores['angry'] += 0.2

        if eyebrow_furrow < angry_eyebrow_threshold and frown_degree > angry_frown_secondary:
            emotion_scores['angry'] += 0.3  # Furrowed eyebrows

        if lip_tension > angry_lip_threshold and frown_degree > angry_frown_secondary:
            emotion_scores['angry'] += 0.3  # Tense lips

        if angry_ear_min < ear < angry_ear_max:
            emotion_scores['angry'] += 0.2  # Eyes narrowed (stricter range)

        # 6. SAD DETECTION
        if frown_degree > 0.008:
            emotion_scores['sad'] += 0.4  # Downward mouth corners
        elif frown_degree > 0.004:
            emotion_scores['sad'] += 0.2

        if mar < 0.18 and frown_degree > 0.004:
            emotion_scores['sad'] += 0.3  # Closed mouth

        if eyebrow_raise > 0.04 and frown_degree > 0.004:
            emotion_scores['sad'] += 0.2  # Eyebrows slightly raised

        if ear < 0.22 and frown_degree > 0.004:
            emotion_scores['sad'] += 0.1  # Eyes slightly closed

        # 7. STRESSED DETECTION
        stress_level = face_metrics.get('stress_level', 0)
        if stress_level > self.config.get('emotion', 'stress_high_threshold', default=0.7):
            emotion_scores['stressed'] += 0.5
        elif stress_level > self.config.get('emotion', 'stress_medium_threshold', default=0.5):
            emotion_scores['stressed'] += 0.3

        if lip_tension > 0.65:
            emotion_scores['stressed'] += 0.3

        if hasattr(state, 'blink_rate') and state.blink_rate > 0:
            if state.blink_rate < 8 or state.blink_rate > 35:
                emotion_scores['stressed'] += 0.2  # Abnormal blink rate

        # 8. CONTENT DETECTION (slight happiness)
        # Already handled in happy detection section

        # 9. NEUTRAL BASELINE
        if (0.18 < mar < 0.25 and -0.003 < frown_degree < 0.004 and
            0.20 < ear < 0.28 and eyebrow_raise < 0.08):
            emotion_scores['neutral'] = 0.8

        # Select emotion with highest score
        best_emotion = max(emotion_scores, key=emotion_scores.get)
        best_score = emotion_scores[best_emotion]

        # Apply minimum threshold
        min_confidence = self.config.get('emotion', 'min_confidence', default=0.3)
        if best_score < min_confidence:
            best_emotion = 'neutral'
            best_score = 0.5

        # Calculate confidence
        score_difference = best_score - sorted(emotion_scores.values())[-2]
        emotion_confidence = np.clip(0.4 + score_difference + (best_score * 0.3), 0.4, 0.95)

        logger.debug(f"Emotion Scores: {emotion_scores} -> Winner: {best_emotion} ({best_score:.2f})")

        return {
            'emotion': best_emotion,
            'emotion_confidence': emotion_confidence,
            'emotion_scores': emotion_scores
        }
