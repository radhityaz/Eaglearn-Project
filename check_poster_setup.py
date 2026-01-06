"""
POSTER++ Setup Checker
Mengecek apakah semua weights sudah terdownload dan siap dipakai
"""

import os
import sys
from pathlib import Path

# Colors for terminal output
class Colors:
    OK = '\033[92m'  # Green
    WARNING = '\033[93m'  # Yellow
    ERROR = '\033[91m'  # Red
    END = '\033[0m'  # Reset

def check_file_exists(filepath, description):
    """Check if file exists and print status"""
    exists = os.path.exists(filepath)

    if exists:
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        print(f"{Colors.OK}✓{Colors.END} {description}: {filepath}")
        print(f"  Size: {size_mb:.1f} MB")
    else:
        print(f"{Colors.ERROR}✗{Colors.END} {description}: {filepath}")
        print(f"  {Colors.WARNING}NOT FOUND{Colors.END}")

    return exists

def main():
    print("=" * 70)
    print("POSTER++ Setup Checker")
    print("=" * 70)
    print()

    # Check FER_POSTER directory
    poster_path = Path("FER_POSTER")
    if not poster_path.exists():
        print(f"{Colors.ERROR}ERROR: FER_POSTER directory not found!{Colors.END}")
        print("Please run: git clone https://github.com/zczcwh/FER_POSTER.git")
        sys.exit(1)

    print(f"{Colors.OK}✓{Colors.END} FER_POSTER directory found")
    print()

    # Check checkpoints
    print("-" * 70)
    print("Checking Checkpoints:")
    print("-" * 70)

    checkpoint_dir = poster_path / "checkpoint"
    checkpoint_dir.mkdir(exist_ok=True)

    checkpoints = [
        (checkpoint_dir / "rafdb_best.pth", "RAF-DB Best Model (Main)"),
        (checkpoint_dir / "affectnet_best.pth", "AffectNet Best Model (Optional)"),
    ]

    checkpoint_status = []
    for filepath, description in checkpoints:
        status = check_file_exists(filepath, description)
        checkpoint_status.append(status)

    print()

    # Check pre-trained backbones
    print("-" * 70)
    print("Checking Pre-trained Backbones:")
    print("-" * 70)

    pretrain_dir = poster_path / "models" / "pretrain"
    pretrain_dir.mkdir(parents=True, exist_ok=True)

    backbones = [
        (pretrain_dir / "ir50.pth", "IR50 Backbone (~100MB)"),
        (pretrain_dir / "mobilefacenet_model_best.pth.tar", "MobileFaceNet Backbone (~25MB)"),
    ]

    backbone_status = []
    for filepath, description in backbones:
        status = check_file_exists(filepath, description)
        backbone_status.append(status)

    print()
    print("=" * 70)

    # Summary
    all_checkpoints_ok = all(checkpoint_status)
    main_checkpoint_ok = checkpoint_status[0]  # rafdb_best.pth is critical
    all_backbones_ok = all(backbone_status)

    if main_checkpoint_ok and all_backbones_ok:
        print(f"{Colors.OK}✓✓✓ ALL CRITICAL FILES FOUND! ✓✓✓{Colors.END}")
        print()
        print("POSTER++ is ready to use! 🚀")
        print()
        print("Run the application:")
        print("  python app.py")
        print()
        print("Then open: http://localhost:8080")
        sys.exit(0)
    else:
        print(f"{Colors.WARNING}⚠ SETUP INCOMPLETE ⚠{Colors.END}")
        print()
        print("Missing files:")
        print()

        if not main_checkpoint_ok:
            print(f"{Colors.ERROR}1. RAF-DB Best Model (REQUIRED){Colors.END}")
            print("   Download from:")
            print("   https://drive.google.com/drive/folders/1jeCPTGjBL8YgKKB9YrI9TYZywme8gymv")
            print(f"   Save to: {checkpoints[0][0]}")
            print()

        if not all_backbones_ok:
            print(f"{Colors.ERROR}2. Pre-trained Backbones (REQUIRED){Colors.END}")
            print("   Download from:")
            print("   https://drive.google.com/drive/folders/1X9pE-NmyRwvBGpVzJOEvLqRPRfk_Siwq")
            print(f"   Save to: {pretrain_dir}/")
            print()

        if not checkpoint_status[1]:
            print(f"{Colors.WARNING}3. AffectNet Best Model (OPTIONAL){Colors.END}")
            print("   Download from:")
            print("   https://drive.google.com/drive/folders/1jeCPTGjBL8YgKKB9YrI9TYZywme8gymv")
            print(f"   Save to: {checkpoints[1][0]}")
            print()

        print("=" * 70)
        print()
        print("After downloading, run this script again to verify:")
        print("  python check_poster_setup.py")
        print()

        sys.exit(1)

if __name__ == "__main__":
    main()
