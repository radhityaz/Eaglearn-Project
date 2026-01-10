"""
User Calibration System
Stores and manages user-specific calibration data for gaze tracking
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Optional
import numpy as np

logger = logging.getLogger(__name__)


class CalibrationManager:
    """Manages user calibration data for improved gaze tracking"""

    def __init__(self, config):
        """
        Initialize calibration manager

        Args:
            config: Config object from config_loader
        """
        self.config = config
        self.calibration_file = config.get(
            "calibration", "calibration_file", default="user_calibration.json"
        )
        self.calibration_dir = os.path.join(os.path.dirname(__file__), "calibrations")
        os.makedirs(self.calibration_dir, exist_ok=True)

        self.current_calibration = self._load_default_calibration()
        self.calibration_points = []

        logger.info("[OK] CalibrationManager initialized")

    def _load_default_calibration(self) -> Dict:
        """Load default calibration values"""
        return self.config.get(
            "calibration",
            "default_calibration",
            default={
                "gaze_offset_x": 0,
                "gaze_offset_y": 0,
                "scale_factor": 1.0,
                "screen_width": 1920,
                "screen_height": 1080,
            },
        )

    def start_calibration(self, user_id: str = "default"):
        """
        Start a new calibration session

        Args:
            user_id: User identifier
        """
        self.current_user = user_id
        self.calibration_points = []
        logger.info(f"Starting calibration for user: {user_id}")

    def add_calibration_point(
        self, screen_x: int, screen_y: int, gaze_x: float, gaze_y: float
    ):
        """
        Add a calibration point (user looking at known screen position)

        Args:
            screen_x: Actual screen X coordinate
            screen_y: Actual screen Y coordinate
            gaze_x: Measured gaze X (-1 to 1)
            gaze_y: Measured gaze Y (-1 to 1)
        """
        self.calibration_points.append(
            {
                "screen_x": screen_x,
                "screen_y": screen_y,
                "gaze_x": gaze_x,
                "gaze_y": gaze_y,
                "timestamp": datetime.now().isoformat(),
            }
        )

        logger.debug(
            f"Added calibration point: screen=({screen_x}, {screen_y}), gaze=({gaze_x:.3f}, {gaze_y:.3f})"
        )

    def calculate_calibration(self) -> Dict:
        """
        Calculate calibration offsets from collected points

        Returns:
            dict: Calibration parameters
        """
        if len(self.calibration_points) < 4:
            logger.warning(
                "Need at least 4 calibration points for accurate calibration"
            )
            return self.current_calibration

        gaze_offset_x = sum(p["gaze_x"] for p in self.calibration_points) / len(
            self.calibration_points
        )
        gaze_offset_y = sum(p["gaze_y"] for p in self.calibration_points) / len(
            self.calibration_points
        )

        expected_screen_width = self.config.get(
            "eye_tracking", "screen_width", default=1920
        )
        expected_screen_height = self.config.get(
            "eye_tracking", "screen_height", default=1080
        )

        gaze_x_vals = np.array(
            [p["gaze_x"] for p in self.calibration_points], dtype=float
        )
        gaze_y_vals = np.array(
            [p["gaze_y"] for p in self.calibration_points], dtype=float
        )
        dx = gaze_x_vals - float(gaze_offset_x)
        dy = gaze_y_vals - float(gaze_offset_y)

        spread = float(np.sqrt(np.mean(dx * dx) + np.mean(dy * dy)))
        if spread <= 1e-6:
            scale_factor = 1.0
        else:
            scale_factor = 0.35 / spread
        scale_factor = float(np.clip(scale_factor, 0.5, 2.0))

        gaze_x_cal = (gaze_x_vals - float(gaze_offset_x)) * scale_factor
        gaze_y_cal = (gaze_y_vals - float(gaze_offset_y)) * scale_factor

        screen_x_vals = np.array(
            [p["screen_x"] for p in self.calibration_points], dtype=float
        )
        screen_y_vals = np.array(
            [p["screen_y"] for p in self.calibration_points], dtype=float
        )

        X = np.column_stack(
            [gaze_x_cal, gaze_y_cal, np.ones(len(self.calibration_points), dtype=float)]
        )
        try:
            wx, _, _, _ = np.linalg.lstsq(X, screen_x_vals, rcond=None)
            wy, _, _, _ = np.linalg.lstsq(X, screen_y_vals, rcond=None)

            pred_x = X @ wx
            pred_y = X @ wy

            rmse_x = float(np.sqrt(np.mean((pred_x - screen_x_vals) ** 2)))
            rmse_y = float(np.sqrt(np.mean((pred_y - screen_y_vals) ** 2)))

            screen_mapping = {
                "x": [float(v) for v in wx.tolist()],
                "y": [float(v) for v in wy.tolist()],
                "rmse_x": rmse_x,
                "rmse_y": rmse_y,
            }
        except Exception as e:
            logger.warning(f"⚠️ Regression calibration failed: {e}")
            screen_mapping = None

        self.current_calibration = {
            "gaze_offset_x": gaze_offset_x,
            "gaze_offset_y": gaze_offset_y,
            "scale_factor": scale_factor,
            "screen_width": expected_screen_width,
            "screen_height": expected_screen_height,
            "invert_y": bool(self.config.get("eye_tracking", "invert_y", default=False)),
            "user_id": getattr(self, "current_user", "default"),
            "calibrated_at": datetime.now().isoformat(),
            "num_points": len(self.calibration_points),
            "screen_mapping": screen_mapping,
        }

        logger.info(f"[OK] Calibration calculated: {self.current_calibration}")

        # Auto-save if enabled
        if self.config.get("calibration", "auto_save", default=True):
            self.save_calibration()

        return self.current_calibration

    def apply_calibration(self, gaze_x: float, gaze_y: float) -> tuple:
        """
        Apply calibration to gaze coordinates

        Args:
            gaze_x: Raw gaze X (-1 to 1)
            gaze_y: Raw gaze Y (-1 to 1)

        Returns:
            tuple: Calibrated (gaze_x, gaze_y)
        """
        # Apply offset
        calibrated_x = gaze_x - self.current_calibration.get("gaze_offset_x", 0)
        calibrated_y = gaze_y - self.current_calibration.get("gaze_offset_y", 0)

        # Apply scale factor
        scale_factor = self.current_calibration.get("scale_factor", 1.0)
        calibrated_x *= scale_factor
        calibrated_y *= scale_factor

        # Clamp to valid range
        calibrated_x = max(-1, min(1, calibrated_x))
        calibrated_y = max(-1, min(1, calibrated_y))

        return calibrated_x, calibrated_y

    def save_calibration(self, user_id: Optional[str] = None):
        """
        Save calibration to file

        Args:
            user_id: User identifier (uses current if None)
        """
        user_id = user_id or getattr(self, "current_user", "default")
        filepath = os.path.join(self.calibration_dir, f"{user_id}.json")

        try:
            with open(filepath, "w") as f:
                json.dump(self.current_calibration, f, indent=2)
            logger.info(f"[OK] Calibration saved to {filepath}")
        except Exception as e:
            logger.error(f"[ERROR] Error saving calibration: {e}")

    def load_calibration(self, user_id: str = "default") -> Optional[Dict]:
        """
        Load calibration from file

        Args:
            user_id: User identifier

        Returns:
            dict: Calibration data or None if not found
        """
        filepath = os.path.join(self.calibration_dir, f"{user_id}.json")

        try:
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    self.current_calibration = json.load(f)
                logger.info(f"Calibration loaded from {filepath}")
                return self.current_calibration
            else:
                logger.warning(f"No calibration found for user: {user_id}")
                return None
        except Exception as e:
            logger.error(f"Error loading calibration: {e}")
            return None

    def get_calibration_status(self) -> Dict:
        """
        Get current calibration status

        Returns:
            dict: Calibration status information
        """
        return {
            "calibrated": len(self.calibration_points) >= 4,
            "num_points": len(self.calibration_points),
            "current_user": getattr(self, "current_user", "default"),
            "calibration": self.current_calibration,
        }
