"""
Configuration Loader for Eaglearn
Loads and manages configuration from config.yaml
"""

import os
import yaml
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for Eaglearn"""

    def __init__(self, config_path: str = None):
        """
        Initialize configuration

        Args:
            config_path: Path to config.yaml file (default: ./config.yaml)
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')

        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"✅ Configuration loaded from {self.config_path}")
            return config
        except FileNotFoundError:
            logger.warning(f"⚠️ Config file not found at {self.config_path}, using defaults")
            return self._get_default_config()
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration if file not found"""
        return {
            'mediapipe': {
                'model_complexity': 0,
                'pose': {'model_complexity': 0},
                'face_detection': {'model_selection': 0},
                'face_mesh': {'refine_landmarks': True}
            },
            'performance': {
                'frame_skip_mode': 'adaptive',
                'frame_skip_base': 3,
                'adaptive_quality': {'enabled': True}
            },
            'camera': {
                'width': 640,
                'height': 480,
                'fps': 30
            },
            'focus': {
                'focused_threshold': 80,
                'distracted_threshold': 50
            },
            'eye_tracking': {
                'screen_width': 1920,
                'screen_height': 1080
            },
            'privacy': {
                'allow_pause': True,
                'local_processing_only': True
            },
            'logging': {
                'level': 'INFO',
                'log_interval': 30
            }
        }

    def get(self, *keys, default=None) -> Any:
        """
        Get configuration value using dot notation

        Args:
            *keys: Nested keys to traverse
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            config.get('mediapipe', 'pose', 'model_complexity')
            config.get('camera', 'width')
        """
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    # Convenience methods for common config values
    @property
    def pose_model_complexity(self) -> int:
        return self.get('mediapipe', 'pose', 'model_complexity', default=0)

    @property
    def face_detection_selection(self) -> int:
        return self.get('mediapipe', 'face_detection', 'model_selection', default=0)

    @property
    def face_mesh_refine_landmarks(self) -> bool:
        return self.get('mediapipe', 'face_mesh', 'refine_landmarks', default=True)

    @property
    def frame_skip_mode(self) -> str:
        return self.get('performance', 'frame_skip_mode', default='adaptive')

    @property
    def frame_skip_base(self) -> int:
        return self.get('performance', 'frame_skip_base', default=3)

    @property
    def adaptive_quality_enabled(self) -> bool:
        return self.get('performance', 'adaptive_quality', 'enabled', default=True)

    @property
    def target_fps(self) -> int:
        return self.get('performance', 'adaptive_quality', 'target_fps', default=25)

    @property
    def gpu_acceleration_enabled(self) -> bool:
        return self.get('performance', 'gpu_acceleration', 'enabled', default=True)

    @property
    def gpu_fallback_enabled(self) -> bool:
        return self.get('performance', 'gpu_acceleration', 'fallback_to_cpu', default=True)

    @property
    def selective_face_mesh_enabled(self) -> bool:
        return self.get('performance', 'selective_face_mesh', 'enabled', default=True)

    @property
    def face_stability_threshold(self) -> float:
        return self.get('performance', 'selective_face_mesh', 'stability_threshold', default=0.8)

    @property
    def camera_width(self) -> int:
        return self.get('camera', 'width', default=640)

    @property
    def camera_height(self) -> int:
        return self.get('camera', 'height', default=480)

    @property
    def camera_fps(self) -> int:
        return self.get('camera', 'fps', default=30)

    @property
    def focused_threshold(self) -> int:
        return self.get('focus', 'focused_threshold', default=80)

    @property
    def distracted_threshold(self) -> int:
        return self.get('focus', 'distracted_threshold', default=50)

    @property
    def privacy_allow_pause(self) -> bool:
        return self.get('privacy', 'allow_pause', default=True)

    @property
    def log_interval(self) -> int:
        return self.get('logging', 'log_interval', default=30)

    @property
    def visual_feedback_enabled(self) -> bool:
        return self.get('ui', 'visual_feedback', 'enabled', default=True)

    @property
    def show_gaze_point(self) -> bool:
        return self.get('ui', 'visual_feedback', 'show_gaze_point', default=True)

    def reload(self) -> None:
        """Reload configuration from file"""
        self.config = self._load_config()
        logger.info("🔄 Configuration reloaded")


# Global configuration instance
config = Config()
