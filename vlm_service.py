"""
Vision Language Model Service
Lightweight local VLM for enhanced context analysis
"""

import logging
import numpy as np
import torch
import cv2
from PIL import Image
from threading import Lock, Thread
from transformers import AutoProcessor, AutoTokenizer, AutoModelForVision2Seq
import time
import os

logger = logging.getLogger(__name__)


class LocalVLMService:
    """Lightweight Vision Language Model for context analysis"""

    def __init__(
        self,
        model_name="HuggingFaceTB/SmolVLM-500M-Instruct",
        device=None,
        async_load=True,
        warmup=True,
        status_callback=None,
        ready_criteria=None,
    ):
        """
        Initialize VLM service with SmolVLM 2 (optimized for CPU < 1GB)

        Args:
            model_name: Model to use (SmolVLM 2 is lightweight and fast)
        """
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.tokenizer = None
        self.processor = None
        self.last_analysis_time = 0
        self.analysis_cooldown = 5.0  # Analyze every 5 seconds max
        self.status = "created"
        self.status_since = time.time()
        self.last_error = None
        self.metrics = {
            "load_ms": None,
            "warmup_ms": None,
            "last_infer_ms": None,
            "last_tokens_per_s": None,
            "format_ok_rate": None,
        }
        self._lock = Lock()
        self._status_callback = status_callback
        self._inference_lock = Lock()
        self._suspend_until = 0.0
        self._warmup_enabled = bool(warmup)
        self._loader_thread = None
        self._loader_started_at = None

        default_ready_criteria = {
            "max_warmup_infer_ms_gpu": 3000,
            "max_warmup_infer_ms_cpu": 8000,
            "min_tokens_per_s_gpu": 5.0,
            "min_tokens_per_s_cpu": 1.0,
            "required_keys": [
                "cognitive_load",
                "engagement_type",
                "task_inference",
                "intervention_needed",
                "suggested_action",
                "confidence",
                "reasoning",
            ],
        }
        self.ready_criteria = {**default_ready_criteria, **(ready_criteria or {})}
        self.retry_cfg = {
            "enabled": True,
            "initial_seconds": 10.0,
            "max_seconds": 300.0,
            "max_attempts_per_hour": 12,
        }
        self.retry_attempts = 0
        self.last_retry_at = 0.0
        self._backoff_next = self.retry_cfg["initial_seconds"]

        logger.info(f"🤖 Initializing VLM: {model_name} on {self.device}")

        if async_load:
            self._set_status("loading")
            self._loader_started_at = time.time()
            self._loader_thread = Thread(
                target=self._load_and_warmup_worker, daemon=True, name="vlm_loader"
            )
            self._loader_thread.start()
            self._start_load_watchdog()
        else:
            self._set_status("loading")
            self._load_and_warmup_worker()

    def _set_status(self, status, error=None):
        with self._lock:
            if self.status == status and (error is None):
                return
            self.status = status
            self.status_since = time.time()
            if error is not None:
                self.last_error = str(error)
        try:
            if callable(self._status_callback):
                self._status_callback(self.get_status())
        except Exception:
            pass

    def get_status(self):
        with self._lock:
            return {
                "status": self.status,
                "status_since": self.status_since,
                "device": self.device,
                "model_name": self.model_name,
                "loaded": bool(self.model is not None and self.processor is not None),
                "ready": self.is_ready(),
                "last_error": self.last_error,
                "metrics": dict(self.metrics),
                "retry_attempts": self.retry_attempts,
                "last_retry_at": self.last_retry_at,
                "backoff_next_seconds": self._backoff_next,
                "loader_alive": bool(
                    self._loader_thread and self._loader_thread.is_alive()
                ),
                "loader_started_at": self._loader_started_at,
            }

    def is_ready(self):
        with self._lock:
            return (
                self.status == "ready"
                and self.model is not None
                and self.processor is not None
            )

    def suspend_inference(self, seconds, reason=None):
        with self._lock:
            self._suspend_until = max(self._suspend_until, time.time() + float(seconds))
        if reason:
            self._set_status("suspended", error=reason)
        else:
            self._set_status("suspended")

    def mark_error(self, error):
        self._set_status("error", error=error)

    def _start_load_watchdog(self):
        try:
            timeout_s = float(os.getenv("EAGLEARN_VLM_LOAD_TIMEOUT_SECONDS", "600"))
        except Exception:
            timeout_s = 600.0

        def watcher():
            try:
                start = float(self._loader_started_at or time.time())
                while True:
                    with self._lock:
                        st = str(self.status or "")
                        loaded = bool(
                            self.model is not None and self.processor is not None
                        )
                    if st in ("ready", "error") or loaded:
                        return
                    if (time.time() - start) >= timeout_s:
                        self._set_status("error", error="load_timeout")
                        return
                    time.sleep(1.0)
            except Exception:
                return

        Thread(target=watcher, daemon=True, name="vlm_watchdog").start()

    def _load_model(self):
        start = time.time()
        self._set_status("loading_processor")
        logger.info("[VLM] Loading processor/tokenizer...")
        self.processor = AutoProcessor.from_pretrained(
            self.model_name, trust_remote_code=True
        )
        self.tokenizer = getattr(
            self.processor, "tokenizer", None
        ) or AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)

        self._set_status("loading_model")
        logger.info("[VLM] Loading model weights...")
        kwargs = {
            "device_map": "auto",
            "trust_remote_code": True,
        }
        if self.device == "cuda":
            kwargs["torch_dtype"] = torch.float16
        else:
            kwargs["torch_dtype"] = torch.float16

        self.model = AutoModelForVision2Seq.from_pretrained(self.model_name, **kwargs)

        with self._lock:
            self.metrics["load_ms"] = int((time.time() - start) * 1000)
        logger.info(f"[VLM] Load complete in {self.metrics['load_ms']}ms")

    def _load_and_warmup_worker(self):
        try:
            self._load_model()
            self._set_status("loaded")

            if self._warmup_enabled:
                self._set_status("warming_up")
                ok = self._warmup_and_validate()
                if ok:
                    self._set_status("ready")
                else:
                    self._set_status("loaded")
            else:
                self._set_status("ready")
        except Exception as e:
            logger.error(f"❌ Failed to load VLM: {e}")
            with self._lock:
                self.model = None
                self.processor = None
                self.tokenizer = None
            self._set_status("error", error=e)

    def _warmup_and_validate(self):
        start = time.time()
        dummy = np.zeros((224, 224, 3), dtype=np.uint8)
        focus_metrics = {
            "focus_percentage": 50,
            "focus_status": "unknown",
            "emotion": "neutral",
            "typing": False,
            "mental_effort": 0.0,
        }
        pose_context = "unknown"
        analysis, infer_ms, tps, format_ok = self._single_infer(
            dummy, focus_metrics, pose_context, max_new_tokens=32
        )

        with self._lock:
            self.metrics["warmup_ms"] = int((time.time() - start) * 1000)
            self.metrics["last_infer_ms"] = infer_ms
            self.metrics["last_tokens_per_s"] = tps
            self.metrics["format_ok_rate"] = 1.0 if format_ok else 0.0

        max_ms = (
            self.ready_criteria["max_warmup_infer_ms_gpu"]
            if self.device == "cuda"
            else self.ready_criteria["max_warmup_infer_ms_cpu"]
        )
        min_tps = (
            self.ready_criteria["min_tokens_per_s_gpu"]
            if self.device == "cuda"
            else self.ready_criteria["min_tokens_per_s_cpu"]
        )

        if analysis is None:
            return False
        if infer_ms is None or infer_ms > max_ms:
            return False
        if tps is None or tps < min_tps:
            return False
        return bool(format_ok)

    def _single_infer(self, frame, focus_metrics, pose_context, max_new_tokens=50):
        if self.model is None or self.processor is None:
            return None, None, None, False

        prompt = self._create_context_prompt(focus_metrics, pose_context)
        if frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)
        rgb_frame = (
            cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if len(frame.shape) == 3 else frame
        )
        pil_image = Image.fromarray(rgb_frame)

        start = time.time()
        generated_text = None
        try:
            with torch.no_grad():
                inputs = self.processor(
                    text=prompt, images=pil_image, return_tensors="pt"
                )
                if hasattr(inputs, "to"):
                    inputs = inputs.to(self.device)
                else:
                    inputs = {
                        k: (v.to(self.device) if hasattr(v, "to") else v)
                        for k, v in inputs.items()
                    }

                gen_kwargs = {
                    "max_new_tokens": int(max_new_tokens),
                    "do_sample": False,
                    "num_beams": 1,
                    "temperature": 0.1,
                    "use_cache": True,
                }
                if getattr(self.tokenizer, "eos_token_id", None) is not None:
                    gen_kwargs["pad_token_id"] = self.tokenizer.eos_token_id

                generated_ids = self.model.generate(**inputs, **gen_kwargs)
                if hasattr(self.tokenizer, "batch_decode"):
                    generated_text = self.tokenizer.batch_decode(
                        generated_ids, skip_special_tokens=True
                    )[0]
                else:
                    generated_text = str(generated_ids)
        except Exception as e:
            self.mark_error(e)
            return None, None, None, False

        elapsed = time.time() - start
        infer_ms = int(elapsed * 1000)

        try:
            token_count = (
                int(getattr(generated_ids, "shape", [0, 0])[-1])
                if generated_ids is not None
                else 0
            )
            tokens_per_s = (
                float(token_count / max(elapsed, 1e-3)) if token_count else None
            )
        except Exception:
            tokens_per_s = None

        analysis = self._parse_vlm_response(generated_text or "")
        required_keys = set(self.ready_criteria.get("required_keys") or [])
        format_ok = isinstance(analysis, dict) and required_keys.issubset(
            set(analysis.keys())
        )
        return analysis, infer_ms, tokens_per_s, format_ok

    def warmup_retry(self, cfg=None):
        try:
            if cfg:
                self.retry_cfg.update(cfg)
            if not self.retry_cfg.get("enabled", True):
                return False
            now = time.time()
            if self.status not in ("loaded", "suspended", "error"):
                return False
            # basic rate limit per hour
            if (now - self.last_retry_at) < self._backoff_next:
                return False
            if self.retry_attempts >= int(
                self.retry_cfg.get("max_attempts_per_hour", 12)
            ):
                return False

            self._set_status("warming_up")
            ok = self._warmup_and_validate()
            self.last_retry_at = now
            self.retry_attempts += 1
            if ok:
                self._backoff_next = self.retry_cfg["initial_seconds"]
                self._set_status("ready")
                return True
            else:
                self._backoff_next = min(
                    self._backoff_next * 2.0,
                    float(self.retry_cfg.get("max_seconds", 300.0)),
                )
                self._set_status("loaded")
                return False
        except Exception as e:
            self._backoff_next = min(
                self._backoff_next * 2.0,
                float(self.retry_cfg.get("max_seconds", 300.0)),
            )
            self._set_status("loaded", error=e)
            return False

    def analyze_context(self, frame, focus_metrics, pose_context):
        """
        Analyze frame with VLM for enhanced context understanding

        Args:
            frame: Current video frame (numpy array)
            focus_metrics: Current focus metrics dict
            pose_context: Current pose context string

        Returns:
            dict: Enhanced analysis with insights
        """
        if not self.is_ready():
            return self._fallback_analysis(focus_metrics, pose_context)

        current_time = time.time()
        if current_time - self.last_analysis_time < self.analysis_cooldown:
            return None  # Skip to avoid overload
        if current_time < self._suspend_until:
            return None

        try:
            if not self._inference_lock.acquire(blocking=False):
                return None
            try:
                analysis, infer_ms, tps, format_ok = self._single_infer(
                    frame, focus_metrics, pose_context, max_new_tokens=50
                )
            finally:
                self._inference_lock.release()

            self.last_analysis_time = current_time

            with self._lock:
                self.metrics["last_infer_ms"] = infer_ms
                self.metrics["last_tokens_per_s"] = tps
                self.metrics["format_ok_rate"] = 1.0 if format_ok else 0.0

            return analysis

        except Exception as e:
            logger.error(f"❌ VLM analysis error: {e}")
            return self._fallback_analysis(focus_metrics, pose_context)

    def _create_context_prompt(self, focus_metrics, pose_context):
        """Create context-aware prompt for VLM"""
        return f"""Analyze this person's cognitive state:

Current metrics:
- Focus: {focus_metrics.get("focus_percentage", 0):.0f}%
- Status: {focus_metrics.get("focus_status", "unknown")}
- Emotion: {focus_metrics.get("emotion", "unknown")}
- Pose: {pose_context}
- Typing: {focus_metrics.get("typing", False)}
- Mental Effort: {focus_metrics.get("mental_effort", 0):.2f}

Provide analysis in JSON format:
{{
    "cognitive_load": "low|medium|high",
    "engagement_type": "deep_work|casual|distracted|fatigued",
    "task_inference": "coding|reading|watching|thinking",
    "intervention_needed": true/false,
    "suggested_action": "string",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}"""

    def _parse_vlm_response(self, response_text):
        """Parse VLM response into structured data"""
        try:
            # Extract JSON from response
            import re

            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                import json

                return json.loads(json_match.group())
        except Exception as e:
            logger.warning(f"Failed to parse VLM response: {e}")

        # Fallback structured response
        return {
            "cognitive_load": "medium",
            "engagement_type": "casual",
            "task_inference": "unknown",
            "intervention_needed": False,
            "suggested_action": "Continue monitoring",
            "confidence": 0.5,
            "reasoning": response_text[:100] + "..."
            if len(response_text) > 100
            else response_text,
        }

    def _fallback_analysis(self, focus_metrics, pose_context):
        """Fallback analysis when VLM is unavailable"""
        # Rule-based fallback
        focus_score = focus_metrics.get("focus_percentage", 50)

        # Simple heuristic
        if focus_score > 80 and pose_context == "thinking":
            engagement = "deep_work"
            cognitive = "high"
            task = "coding"
        elif focus_score > 70 and pose_context == "typing":
            engagement = "casual"
            cognitive = "medium"
            task = "coding"
        elif focus_score < 50:
            engagement = "distracted"
            cognitive = "low"
            task = "unknown"
        else:
            engagement = "casual"
            cognitive = "medium"
            task = "unknown"

        return {
            "cognitive_load": cognitive,
            "engagement_type": engagement,
            "task_inference": task,
            "intervention_needed": focus_score < 40,
            "suggested_action": "Adjust focus" if focus_score < 40 else "Continue",
            "confidence": 0.6,
            "reasoning": "Rule-based analysis",
        }

    def get_insights_summary(self, analysis):
        """Get human-readable insights from VLM analysis"""
        if not analysis:
            return "Analyzing..."

        insights = []

        # Cognitive load
        load = analysis.get("cognitive_load", "medium")
        load_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(load, "⚪")
        insights.append(f"Cognitive Load: {load_emoji} {load.title()}")

        # Engagement
        engagement = analysis.get("engagement_type", "casual")
        engagement_emoji = {
            "deep_work": "🎯",
            "casual": "💻",
            "distracted": "📱",
            "fatigued": "😴",
        }.get(engagement, "👤")
        insights.append(
            f"Engagement: {engagement_emoji} {engagement.replace('_', ' ').title()}"
        )

        # Task
        task = analysis.get("task_inference", "unknown")
        task_emoji = {
            "coding": "💻",
            "reading": "📖",
            "watching": "👀",
            "thinking": "🤔",
        }.get(task, "❓")
        insights.append(f"Task: {task_emoji} {task.title()}")

        # Action needed
        if analysis.get("intervention_needed", False):
            action = analysis.get("suggested_action", "Take a break")
            insights.append(f"⚠️ Suggestion: {action}")

        return " | ".join(insights)

    def cleanup(self):
        """Cleanup model resources"""
        if self.model:
            del self.model
        if self.tokenizer:
            del self.tokenizer
        if self.processor:
            del self.processor

        torch.cuda.empty_cache() if self.device == "cuda" else None
        logger.info("🧹 VLM resources cleaned up")
