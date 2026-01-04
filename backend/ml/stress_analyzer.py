"""
Audio Stress Analysis Engine using librosa.
Analyzes voice characteristics to detect stress levels.
"""

import numpy as np
import librosa
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class StressAnalyzer:
    """
    Audio stress analysis using voice features.
    Extracts MFCC, spectral features, and estimates stress level.
    """
    
    def __init__(self, sample_rate: int = 16000):
        """
        Initialize stress analyzer.
        
        Args:
            sample_rate: Audio sample rate in Hz (default: 16000)
        """
        self.sample_rate = sample_rate
        self.n_mfcc = 13  # Number of MFCC coefficients
        
        # Stress thresholds (calibrated from research)
        self.stress_thresholds = {
            'low': 0.33,
            'medium': 0.66,
            'high': 1.0
        }
        
        logger.info(f"Stress analyzer initialized (sample_rate={sample_rate})")
    
    def analyze(self, audio_data: np.ndarray) -> Dict:
        """
        Analyze audio data for stress indicators.
        
        Args:
            audio_data: Audio samples (1D numpy array)
            
        Returns:
            Dictionary with stress analysis results:
            {
                'stress_level': float,  # 0.0 to 1.0
                'stress_category': str,  # "low", "medium", "high"
                'confidence': float,  # 0.0 to 1.0
                'features': {
                    'pitch_mean': float,
                    'pitch_std': float,
                    'energy_mean': float,
                    'energy_std': float,
                    'speaking_rate': float,
                    'mfcc': list,  # 13 MFCC coefficients
                    'spectral_centroid': float,
                    'spectral_bandwidth': float,
                    'spectral_rolloff': float,
                    'zero_crossing_rate': float,
                    'hrv_estimate': float
                }
            }
        """
        try:
            # Validate audio data
            if len(audio_data) == 0:
                return self._get_default_result()
            
            # Extract audio features
            features = self._extract_features(audio_data)
            
            # Calculate stress level from features
            stress_level = self._calculate_stress_level(features)
            
            # Classify stress category
            stress_category = self._classify_stress(stress_level)
            
            # Calculate confidence
            confidence = self._calculate_confidence(audio_data, features)
            
            return {
                'stress_level': float(stress_level),
                'stress_category': stress_category,
                'confidence': float(confidence),
                'features': features
            }
            
        except Exception as e:
            logger.error(f"Stress analysis error: {str(e)}")
            return self._get_default_result()
    
    def _extract_features(self, audio_data: np.ndarray) -> Dict:
        """
        Extract audio features using librosa.
        
        Args:
            audio_data: Audio samples
            
        Returns:
            Dictionary of extracted features
        """
        # Ensure audio is float32
        audio_float = audio_data.astype(np.float32)
        
        # Extract MFCC (Mel-frequency cepstral coefficients)
        mfcc = librosa.feature.mfcc(
            y=audio_float,
            sr=self.sample_rate,
            n_mfcc=self.n_mfcc
        )
        mfcc_mean = np.mean(mfcc, axis=1)
        
        # Extract pitch (fundamental frequency)
        pitches, magnitudes = librosa.piptrack(
            y=audio_float,
            sr=self.sample_rate
        )
        pitch_values = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                pitch_values.append(pitch)
        
        pitch_mean = np.mean(pitch_values) if pitch_values else 0.0
        pitch_std = np.std(pitch_values) if pitch_values else 0.0
        
        # Extract energy (RMS)
        rms = librosa.feature.rms(y=audio_float)
        energy_mean = float(np.mean(rms))
        energy_std = float(np.std(rms))
        
        # Extract spectral features
        spectral_centroids = librosa.feature.spectral_centroid(
            y=audio_float,
            sr=self.sample_rate
        )
        spectral_centroid = float(np.mean(spectral_centroids))
        
        spectral_bandwidth = librosa.feature.spectral_bandwidth(
            y=audio_float,
            sr=self.sample_rate
        )
        spectral_bandwidth_mean = float(np.mean(spectral_bandwidth))
        
        spectral_rolloff = librosa.feature.spectral_rolloff(
            y=audio_float,
            sr=self.sample_rate
        )
        spectral_rolloff_mean = float(np.mean(spectral_rolloff))
        
        # Zero crossing rate
        zcr = librosa.feature.zero_crossing_rate(audio_float)
        zcr_mean = float(np.mean(zcr))
        
        # Estimate speaking rate (onset detection)
        onset_env = librosa.onset.onset_strength(y=audio_float, sr=self.sample_rate)
        tempo = librosa.beat.tempo(onset_envelope=onset_env, sr=self.sample_rate)
        speaking_rate = float(tempo[0]) if len(tempo) > 0 else 0.0
        
        # HRV estimate (simplified - based on pitch variability)
        hrv_estimate = float(pitch_std / (pitch_mean + 1e-6))
        
        return {
            'pitch_mean': float(pitch_mean),
            'pitch_std': float(pitch_std),
            'energy_mean': energy_mean,
            'energy_std': energy_std,
            'speaking_rate': speaking_rate,
            'mfcc': mfcc_mean.tolist(),
            'spectral_centroid': spectral_centroid,
            'spectral_bandwidth': spectral_bandwidth_mean,
            'spectral_rolloff': spectral_rolloff_mean,
            'zero_crossing_rate': zcr_mean,
            'hrv_estimate': hrv_estimate
        }
    
    def _calculate_stress_level(self, features: Dict) -> float:
        """
        Calculate stress level from audio features.
        Uses weighted combination of features.
        
        Args:
            features: Extracted audio features
            
        Returns:
            Stress level (0.0 to 1.0)
        """
        # Normalize features to 0-1 range
        # Higher pitch variation → higher stress
        pitch_stress = min(features['pitch_std'] / 100.0, 1.0)
        
        # Higher energy variation → higher stress
        energy_stress = min(features['energy_std'] / 0.1, 1.0)
        
        # Faster speaking rate → higher stress
        speaking_stress = min(features['speaking_rate'] / 200.0, 1.0)
        
        # Higher spectral centroid → higher stress (tense voice)
        spectral_stress = min(features['spectral_centroid'] / 5000.0, 1.0)
        
        # Higher HRV estimate → higher stress
        hrv_stress = min(features['hrv_estimate'] / 0.5, 1.0)
        
        # Weighted combination
        stress_level = (
            0.25 * pitch_stress +
            0.20 * energy_stress +
            0.20 * speaking_stress +
            0.20 * spectral_stress +
            0.15 * hrv_stress
        )
        
        return float(np.clip(stress_level, 0.0, 1.0))
    
    def _classify_stress(self, stress_level: float) -> str:
        """
        Classify stress level into categories.
        
        Args:
            stress_level: Stress level (0.0 to 1.0)
            
        Returns:
            Stress category: "low", "medium", "high"
        """
        if stress_level < self.stress_thresholds['low']:
            return "low"
        elif stress_level < self.stress_thresholds['medium']:
            return "medium"
        else:
            return "high"
    
    def _calculate_confidence(self, audio_data: np.ndarray, features: Dict) -> float:
        """
        Calculate confidence score based on audio quality.
        
        Args:
            audio_data: Raw audio samples
            features: Extracted features
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Check audio length (need sufficient data)
        min_samples = self.sample_rate * 0.5
        length_score = min(len(audio_data) / min_samples, 1.0)
        
        # Check energy level (not too quiet)
        energy_score = min(features['energy_mean'] / 0.01, 1.0)
        
        # Combined confidence
        confidence = (length_score + energy_score) / 2.0
        
        return float(np.clip(confidence, 0.0, 1.0))
    
    def _get_default_result(self) -> Dict:
        """Get default result when analysis fails."""
        return {
            'stress_level': 0.0,
            'stress_category': 'low',
            'confidence': 0.0,
            'features': {
                'pitch_mean': 0.0,
                'pitch_std': 0.0,
                'energy_mean': 0.0,
                'energy_std': 0.0,
                'speaking_rate': 0.0,
                'mfcc': [0.0] * self.n_mfcc,
                'spectral_centroid': 0.0,
                'spectral_bandwidth': 0.0,
                'spectral_rolloff': 0.0,
                'zero_crossing_rate': 0.0,
                'hrv_estimate': 0.0
            }
        }


# Global stress analyzer instance
_stress_analyzer: Optional[StressAnalyzer] = None


def get_stress_analyzer() -> StressAnalyzer:
    """Get or create global stress analyzer instance."""
    global _stress_analyzer
    if _stress_analyzer is None:
        _stress_analyzer = StressAnalyzer(sample_rate=16000)
    return _stress_analyzer