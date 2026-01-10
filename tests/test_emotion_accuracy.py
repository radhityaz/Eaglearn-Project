"""
Emotion Detection Diagnostic Test
Shows exactly what DeepFace is detecting
"""

import cv2
from mediapipe_processors.deepface_emotion_detector import DeepFaceEmotionDetector
from config_loader import config


def main() -> int:
    print("=" * 60)
    print("🎭 DEEPFACE EMOTION DIAGNOSTIC TEST")
    print("=" * 60)

    detector = DeepFaceEmotionDetector(config)

    if not detector.available:
        print("\n❌ DeepFace NOT installed!")
        print("Run: pip install deepface tf-keras tensorflow")
        return 1

    print("\n✅ DeepFace is installed and ready!")
    print("\n" + "=" * 60)
    print("📸 INSTRUCTIONS:")
    print("=" * 60)
    print(
        """
This test will use your webcam to show exactly what DeepFace detects.

For each test, make a different face:
1. Neutral/flat face (relaxed)
2. Happy (smile)
3. Sad (frown)
4. Surprised (eyes wide, mouth open)
5. Angry (furrow brows)

Press SPACE to capture, ESC to quit
"""
    )

    print("=" * 60)
    print("Starting camera... (Press SPACE to capture, ESC to quit)")
    print("=" * 60)

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("\n❌ Cannot open webcam!")
        return 1

    try:
        cv2.namedWindow("Emotion Test")

        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Cannot read frame!")
                break

            cv2.imshow("Emotion Test", frame)
            key = cv2.waitKey(1) & 0xFF

            if key == 27:
                break
            if key == 32:
                print("\n" + "=" * 60)
                print("🔍 ANALYZING FACE...")
                print("=" * 60)

                result = detector.detect_emotion(frame)
                print(f"\nMethod: {result['method']}")

                if result["method"] == "deepface":
                    print("\n✅ DeepFace Results:")
                    print(f"Detected Emotion: {result.get('raw_emotion', 'N/A')}")

                    print("\n📊 All Emotion Scores:")
                    scores = result.get("emotion_scores", {})
                    sorted_scores = sorted(
                        scores.items(), key=lambda x: x[1], reverse=True
                    )

                    for emotion, score in sorted_scores:
                        bar = "█" * int(score / 10)
                        print(f"  {emotion:12s} {score:5.1f}% {bar}")

                    print(
                        f"\n🎯 Mapped to: {result['emotion']} "
                        f"(confidence: {result['emotion_confidence']:.1%})"
                    )
                else:
                    print(f"\n⚠️ Fallback: {result.get('warning', 'Unknown error')}")

                print("\n" + "=" * 60)
                print("Press SPACE to capture another, ESC to quit")
                print("=" * 60)
    finally:
        cap.release()
        cv2.destroyAllWindows()

    print("\n✅ Test complete!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
