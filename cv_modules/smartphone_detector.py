import os
import cv2


class SmartphoneDetector:
    def __init__(self, model_path: str, score_threshold: float = 0.5):
        self.model_path = model_path
        self.score_threshold = float(score_threshold)
        self.net = None
        self.ready = False

        if not model_path or not os.path.exists(model_path):
            return

        try:
            self.net = cv2.dnn.readNetFromONNX(model_path)
            self.ready = True
        except Exception:
            self.net = None
            self.ready = False

    def set_threshold(self, score_threshold: float):
        self.score_threshold = float(score_threshold)

    def detect(self, frame_bgr):
        if not self.ready or self.net is None:
            return []

        h, w = frame_bgr.shape[:2]
        blob = cv2.dnn.blobFromImage(
            frame_bgr, scalefactor=1 / 255.0, size=(640, 640), swapRB=True, crop=False
        )
        self.net.setInput(blob)
        outputs = self.net.forward()

        detections = []

        out = outputs[0] if isinstance(outputs, (list, tuple)) else outputs
        if out is None:
            return []

        out = out.reshape(-1, out.shape[-1]) if out.ndim > 2 else out
        for row in out:
            if row.shape[0] < 6:
                continue
            cx, cy, bw, bh = row[0:4]
            obj = row[4]
            cls_scores = row[5:]
            if cls_scores.size == 0:
                continue
            cls_id = int(cls_scores.argmax())
            cls_score = float(cls_scores[cls_id])
            score = float(obj) * cls_score
            if score < self.score_threshold:
                continue

            x1 = int((cx - bw / 2) * w / 640)
            y1 = int((cy - bh / 2) * h / 640)
            x2 = int((cx + bw / 2) * w / 640)
            y2 = int((cy + bh / 2) * h / 640)
            x1 = max(0, min(w - 1, x1))
            y1 = max(0, min(h - 1, y1))
            x2 = max(0, min(w - 1, x2))
            y2 = max(0, min(h - 1, y2))

            detections.append(
                {
                    "bbox": (x1, y1, x2, y2),
                    "score": score,
                    "class_id": cls_id,
                }
            )

        detections.sort(key=lambda d: d["score"], reverse=True)
        return detections
