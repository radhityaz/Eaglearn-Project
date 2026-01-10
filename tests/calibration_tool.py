"""
Automated Calibration Tool for Eaglearn Gaze Tracking
Membantu proses calibration dengan mudah
"""

import requests
import time

BASE_URL = "http://127.0.0.1:8080"


def print_header(text):
    """Print header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_step(step_num, text):
    """Print step"""
    print(f"\n[{step_num}] {text}")


def check_server():
    """Check if server is running"""
    try:
        response = requests.get(f"{BASE_URL}/api/metrics", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def start_calibration(user_id="default"):
    """Start calibration session"""
    print_step(1, "Starting Calibration Session...")

    response = requests.post(
        f"{BASE_URL}/api/calibration/start", json={"user_id": user_id}, timeout=5
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ {data.get('message', 'Calibration started')}")
        return True
    else:
        print(f"❌ Error: {response.text}")
        return False


def get_current_gaze():
    """Get current gaze coordinates from metrics"""
    try:
        response = requests.get(f"{BASE_URL}/api/metrics", timeout=2)
        if response.status_code == 200:
            data = response.json()
            return {
                "gaze_x": data.get("facial_metrics", {})
                .get("micro_expressions", {})
                .get("eye_gaze_x", 0),
                "gaze_y": data.get("facial_metrics", {})
                .get("micro_expressions", {})
                .get("eye_gaze_y", 0),
                "screen_x": data.get("eye_tracking", {}).get("screen_x", 0),
                "screen_y": data.get("eye_tracking", {}).get("screen_y", 0),
            }
    except Exception:
        pass
    return None


def add_calibration_point(screen_x, screen_y, label=""):
    """Add a calibration point"""
    print(f"\n  📍 {label}")
    print(f"     Screen Position: ({screen_x}, {screen_y})")
    print("     Please look at this position on your screen...")

    # Countdown
    for i in range(3, 0, -1):
        print(f"     {i}...", end=" ", flush=True)
        time.sleep(1)

    print("     Recording...")

    # Get current gaze
    gaze = get_current_gaze()
    if gaze:
        print(f"     Raw Gaze Detected: X={gaze['gaze_x']:.3f}, Y={gaze['gaze_y']:.3f}")

        # Add calibration point
        response = requests.post(
            f"{BASE_URL}/api/calibration/add-point",
            json={
                "screen_x": screen_x,
                "screen_y": screen_y,
                "gaze_x": gaze["gaze_x"],
                "gaze_y": gaze["gaze_y"],
            },
            timeout=5,
        )

        if response.status_code == 200:
            print("     ✅ Point recorded!")
            return True
        else:
            print(f"     ❌ Error: {response.text}")
            return False
    else:
        print("     ❌ Could not get gaze data")
        return False


def calculate_calibration():
    """Calculate and save calibration"""
    print_step(2, "Calculating Calibration Data...")

    response = requests.post(f"{BASE_URL}/api/calibration/calculate", timeout=5)

    if response.status_code == 200:
        data = response.json()
        calibration = data.get("calibration", {})
        print("✅ Calibration calculated successfully!")
        print("\n   Calibration Results:")
        print("   ─────────────────────────────────")
        print(f"   Gaze Offset X: {calibration.get('gaze_offset_x', 0):.4f}")
        print(f"   Gaze Offset Y: {calibration.get('gaze_offset_y', 0):.4f}")
        print(f"   Scale Factor:   {calibration.get('scale_factor', 1.0):.4f}")
        print(f"   Num Points:     {calibration.get('num_points', 0)}")
        print(f"   User ID:        {calibration.get('user_id', 'N/A')}")
        return True
    else:
        print(f"❌ Error: {response.text}")
        return False


def run_9_point_calibration():
    """Run standard 9-point calibration (3x3 grid)"""
    print_header("9-Point Gaze Calibration")

    screen_width = 1920
    screen_height = 1080

    # 9 calibration points (3x3 grid)
    calibration_points = [
        # Top row
        (0, 0, "Top-Left Corner"),
        (screen_width // 2, 0, "Top-Center"),
        (screen_width, 0, "Top-Right Corner"),
        # Middle row
        (0, screen_height // 2, "Middle-Left"),
        (screen_width // 2, screen_height // 2, "CENTER - Look Here!"),
        (screen_width, screen_height // 2, "Middle-Right"),
        # Bottom row
        (0, screen_height, "Bottom-Left Corner"),
        (screen_width // 2, screen_height, "Bottom-Center"),
        (screen_width, screen_height, "Bottom-Right Corner"),
    ]

    print("\nInstructions:")
    print("──────────────────────────────────────────────────────────")
    print("1. Make sure you're sitting comfortably in front of screen")
    print("2. Keep your head still during calibration")
    print("3. Follow the on-screen instructions")
    print("4. Look at EACH position when prompted")
    print("──────────────────────────────────────────────────────────")

    input("\nPress Enter when you're ready to start...")

    # Start calibration
    if not start_calibration("default"):
        print("\n❌ Failed to start calibration")
        return False

    # Collect calibration points
    success_count = 0
    for i, (x, y, label) in enumerate(calibration_points, 1):
        if add_calibration_point(x, y, f"Point {i}/9: {label}"):
            success_count += 1
        time.sleep(0.5)  # Brief pause between points

    print(f"\n✅ Successfully recorded {success_count}/9 points")

    # Calculate calibration
    if success_count >= 4:  # Minimum 4 points
        calculate_calibration()
        return True
    else:
        print(f"\n❌ Need at least 4 points for calibration (got {success_count})")
        return False


def test_gaze_tracking():
    """Test gaze tracking after calibration"""
    print_header("Testing Gaze Tracking")

    print("\n🧪 Testing gaze accuracy...")
    print("Look at different positions on screen and check accuracy")
    print("\nTest Positions:")

    test_positions = [
        (960, 540, "CENTER"),
        (480, 270, "Top-Left Quadrant"),
        (1440, 810, "Bottom-Right Quadrant"),
    ]

    for screen_x, screen_y, label in test_positions:
        print(f"\n  📍 {label}: ({screen_x}, {screen_y})")
        print("     Please look at this position...")

        for i in range(3, 0, -1):
            print(f"     {i}...", end=" ", flush=True)
            time.sleep(1)

        gaze = get_current_gaze()
        if gaze:
            detected_x = gaze["screen_x"]
            detected_y = gaze["screen_y"]

            # Calculate error
            error_x = abs(detected_x - screen_x)
            error_y = abs(detected_y - screen_y)
            error_total = (error_x**2 + error_y**2) ** 0.5

            print(f"     Detected: ({detected_x}, {detected_y})")
            print(
                f"     Error: X={error_x:.0f}px, Y={error_y:.0f}px, Total={error_total:.0f}px"
            )

            if error_total < 100:
                print("     ✅ Good accuracy!")
            elif error_total < 200:
                print("     ⚠️  Moderate accuracy (expected with iris-based tracking)")
            else:
                print("     ❌ Poor accuracy - recalibration recommended")


def main():
    """Main calibration workflow"""
    print_header("Eaglearn Gaze Tracking Calibration Tool")

    # Check server
    print("Checking if Eaglearn server is running...")
    if not check_server():
        print("\n❌ Error: Eaglearn server is not running!")
        print("\nPlease start the server first:")
        print("  python app.py")
        print("\nThen run this calibration tool again.")
        return

    print("✅ Server is running!\n")

    # Ask user what to do
    print("What would you like to do?")
    print("  1. Run 9-Point Calibration (Recommended)")
    print("  2. Test Current Gaze Tracking")
    print("  3. Both: Calibrate then Test")
    print("  4. Exit")

    choice = input("\nEnter choice (1-4): ").strip()

    if choice == "1":
        run_9_point_calibration()
    elif choice == "2":
        test_gaze_tracking()
    elif choice == "3":
        if run_9_point_calibration():
            print("\n" + "=" * 70)
            input("\nPress Enter to continue to testing...")
            test_gaze_tracking()
    else:
        print("Exiting...")
        return

    print("\n" + "=" * 70)
    print("  Done!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Calibration cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
