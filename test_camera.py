#!/usr/bin/env python3
"""
Simple camera test to verify everything works
"""

import cv2
import numpy as np

print("=" * 60)
print("CAMERA AND DETECTION TEST")
print("=" * 60)
print("\nThis will test:")
print("1. ✓ OpenCV is installed")
print("2. ✓ NumPy is installed")  
print("3. ? Camera is working")
print("4. ? Can detect circles")
print()

# Test camera
print("Testing camera...")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ ERROR: Could not open camera!")
    print("\nTroubleshooting:")
    print("- Check if camera is plugged in")
    print("- Try: ls /dev/video*")
    print("- Try changing cv2.VideoCapture(0) to (1) or (2)")
    exit(1)

print("✅ Camera opened successfully!")

# Get camera properties
width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
fps = cap.get(cv2.CAP_PROP_FPS)

print(f"   Resolution: {int(width)}x{int(height)}")
print(f"   FPS: {int(fps)}")

# Try to capture a frame
ret, frame = cap.read()

if not ret or frame is None:
    print("❌ ERROR: Could not capture frame!")
    exit(1)

print("✅ Successfully captured frame!")
print(f"   Frame shape: {frame.shape}")

# Test green detection
print("\nTesting green circle detection...")
hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
lower_green = np.array([35, 50, 50])
upper_green = np.array([85, 255, 255])
mask = cv2.inRange(hsv, lower_green, upper_green)

contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

if contours:
    print(f"✅ Found {len(contours)} potential green objects!")
    print("   (This could be anything green in view)")
else:
    print("⚠️  No green objects detected in current frame")
    print("   (This is OK - try holding a green object to the camera)")

print("\n" + "=" * 60)
print("READY TO RUN THE DETECTOR!")
print("=" * 60)
print("\nNow run:")
print("  python3 green_circle_detector.py")
print("\nWhat you'll see when it WORKS:")
print("  ✓ A window opens showing camera feed")
print("  ✓ Green circles drawn around detected targets")
print("  ✓ Red dot at center of each circle")
print("  ✓ Position coordinates displayed")
print("  ✓ FPS counter in top-left")
print("\nControls:")
print("  - Press 'q' to quit")
print("  - Press 'm' to toggle mask view")
print("  - Press '+' or '-' to adjust detection sensitivity")
print()

# Cleanup
cap.release()
print("Test complete!")

