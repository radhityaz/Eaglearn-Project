"""
Real-time Camera Feed Test
Verifies:
- Camera opens successfully
- Face detection works
- Emotion detection with new backend
- Performance metrics
"""

import cv2
import time
from collections import deque

print("=" * 60)
print("REAL-TIME CAMERA FEED TEST")
print("=" * 60)
print()

# Initialize camera
print("🔷 Step 1: Opening camera...")
backend = cv2.CAP_DSHOW
cap = cv2.VideoCapture(0, backend)

if not cap.isOpened():
    print("❌ Failed to open with DirectShow, trying default...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Cannot open camera!")
        exit(1)

print("✅ Camera opened successfully")
print(f"   Backend: {'DirectShow' if backend == cv2.CAP_DSHOW else 'Default'}")
print(
    f"   Resolution: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}"
)
print()

# Initialize MediaPipe Face Detection
print("🔷 Step 2: Initializing Face Detection...")
try:
    import mediapipe as mp

    mp_face_detection = mp.solutions.face_detection
    face_detection = mp_face_detection.FaceDetection(
        model_selection=0, min_detection_confidence=0.5
    )
    print("✅ MediaPipe Face Detection initialized")
except Exception as e:
    print(f"❌ MediaPipe init failed: {e}")
    cap.release()
    exit(1)
print()

# Initialize DeepFace (lazy load on first use)
print("🔷 Step 3: Initializing DeepFace Emotion Detection...")
try:
    from deepface import DeepFace

    print("✅ DeepFace imported")
    print("⚠️  Note: Model will load on first emotion detection (may take 5-10s)")
except Exception as e:
    print(f"❌ DeepFace import failed: {e}")
    print("   Continuing without emotion detection...")
    DeepFace = None
print()

# Test settings
test_duration = 15  # seconds
frame_times = deque(maxlen=30)
face_detected_count = 0
emotion_detected_count = 0
emotion_results = []

print("=" * 60)
print(f"Starting {test_duration}-second test...")
print("Press 'q' to quit early")
print("=" * 60)
print()

start_time = time.time()
last_emotion_time = 0
emotion_interval = 2.0  # Detect emotion every 2 seconds

try:
    while True:
        loop_start = time.time()
        ret, frame = cap.read()

        if not ret:
            print("❌ Failed to read frame")
            break

        # Mirror flip
        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Face detection
        detection_results = face_detection.process(frame_rgb)
        face_detected_this_frame = False

        if detection_results.detections:
            face_detected_this_frame = True
            face_detected_count += 1

            # Draw face boxes
            for detection in detection_results.detections:
                bbox = detection.location_data.relative_bounding_box
                h, w = frame.shape[:2]
                x = int(bbox.xmin * w)
                y = int(bbox.ymin * h)
                bw = int(bbox.width * w)
                bh = int(bbox.height * h)

                # Draw rectangle
                cv2.rectangle(frame, (x, y), (x + bw, y + bh), (0, 255, 0), 2)

        # Emotion detection (throttled)
        current_time = time.time()
        if (
            DeepFace is not None
            and face_detected_this_frame
            and current_time - last_emotion_time > emotion_interval
        ):
            try:
                # Use SSD backend for CPU (faster)
                result = DeepFace.analyze(
                    frame_rgb,
                    actions=["emotion"],
                    enforce_detection=False,
                    detector_backend="ssd",  # CPU-optimized
                )

                if isinstance(result, list):
                    result = result[0]

                emotion = result.get("dominant_emotion", "neutral")
                confidence = result.get("emotion", {}).get(emotion, 0) / 100.0

                emotion_detected_count += 1
                emotion_results.append((emotion, confidence))
                last_emotion_time = current_time

                # Display emotion
                cv2.putText(
                    frame,
                    f"Emotion: {emotion}",
                    (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 0),
                    2,
                )
                cv2.putText(
                    frame,
                    f"Confidence: {confidence:.0%}",
                    (10, 115),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2,
                )

                print(f"   🎭 Emotion: {emotion} ({confidence:.1%})")

            except Exception as e:
                print(f"   ⚠️ Emotion detection error: {str(e)[:50]}")

        # Calculate FPS
        frame_time = time.time() - loop_start
        frame_times.append(frame_time)
        fps = 1.0 / (sum(frame_times) / len(frame_times)) if frame_times else 0

        # Draw stats
        cv2.putText(
            frame,
            f"FPS: {fps:.1f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )
        cv2.putText(
            frame,
            f"Faces: {face_detected_count}",
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

        # Display frame
        cv2.imshow("Camera Feed Test", frame)

        # Check elapsed time
        elapsed = current_time - start_time
        if elapsed >= test_duration:
            print(f"\n⏱️  {test_duration}-second test completed!")
            break

        # Check for quit
        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("\n⏹️  Test stopped by user")
            break

except KeyboardInterrupt:
    print("\n⏹️  Test interrupted")
finally:
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    face_detection.close()

    # Summary
    print()
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    total_time = time.time() - start_time
    avg_fps = sum(frame_times) / len(frame_times) if frame_times else 0
    avg_fps_display = 1.0 / avg_fps if avg_fps > 0 else 0

    print(f"⏱️  Duration: {total_time:.1f}s")
    print(f"📊 Average FPS: {avg_fps_display:.1f}")
    print(f"👤 Faces detected: {face_detected_count} frames")
    print(f"🎭 Emotions detected: {emotion_detected_count} times")

    if emotion_results:
        print()
        print("Emotion Breakdown:")
        emotion_counts = {}
        for emotion, conf in emotion_results:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

        for emotion, count in sorted(emotion_counts.items(), key=lambda x: -x[1]):
            print(f"   {emotion}: {count}x")

    print()
    if avg_fps_display >= 20:
        print("✅ Performance is GOOD (>= 20 FPS)")
    elif avg_fps_display >= 15:
        print("⚠️  Performance is OKAY (15-20 FPS)")
    else:
        print("❌ Performance is POOR (< 15 FPS) - consider lowering resolution")

    print()
    print("=" * 60)
    print("Test completed successfully!")
    print("=" * 60)
