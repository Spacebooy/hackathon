#!/usr/bin/env python3
"""
Green Color Calibration Tool
Use this to find the perfect HSV color range for your green circles
"""

import cv2
import numpy as np

def nothing(x):
    """Dummy callback for trackbars"""
    pass

def calibrate_green_detection():
    """
    Interactive calibration tool with sliders to adjust HSV values
    """
    print("=" * 60)
    print("GREEN COLOR CALIBRATION TOOL")
    print("=" * 60)
    print("\nInstructions:")
    print("1. Place your green circle target in view")
    print("2. Adjust the HSV sliders until ONLY the green circle is white in the mask")
    print("3. Press 'q' to quit and save the values")
    print("4. Press 's' to take a snapshot")
    print("\nTips:")
    print("- H (Hue): Controls the color (35-85 is green range)")
    print("- S (Saturation): Controls color intensity")
    print("- V (Value): Controls brightness")
    print()
    
    # Initialize camera
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Create window and trackbars
    window_name = 'Green Calibration'
    cv2.namedWindow(window_name)
    
    # Starting values for green
    cv2.createTrackbar('H_min', window_name, 35, 179, nothing)
    cv2.createTrackbar('H_max', window_name, 85, 179, nothing)
    cv2.createTrackbar('S_min', window_name, 50, 255, nothing)
    cv2.createTrackbar('S_max', window_name, 255, 255, nothing)
    cv2.createTrackbar('V_min', window_name, 50, 255, nothing)
    cv2.createTrackbar('V_max', window_name, 255, 255, nothing)
    
    # Morphology kernel size
    cv2.createTrackbar('Morph', window_name, 5, 15, nothing)
    
    print("Calibration window opened. Adjust sliders...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error reading from camera")
            break
        
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Get current trackbar values
        h_min = cv2.getTrackbarPos('H_min', window_name)
        h_max = cv2.getTrackbarPos('H_max', window_name)
        s_min = cv2.getTrackbarPos('S_min', window_name)
        s_max = cv2.getTrackbarPos('S_max', window_name)
        v_min = cv2.getTrackbarPos('V_min', window_name)
        v_max = cv2.getTrackbarPos('V_max', window_name)
        morph_size = cv2.getTrackbarPos('Morph', window_name)
        
        # Create mask
        lower = np.array([h_min, s_min, v_min])
        upper = np.array([h_max, s_max, v_max])
        mask = cv2.inRange(hsv, lower, upper)
        
        # Apply morphological operations
        if morph_size > 0:
            kernel = np.ones((morph_size, morph_size), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # Find contours for additional info
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Create result image
        result = cv2.bitwise_and(frame, frame, mask=mask)
        
        # Draw contours on original frame
        frame_with_contours = frame.copy()
        cv2.drawContours(frame_with_contours, contours, -1, (0, 255, 0), 2)
        
        # Add info text
        info_text = f"Contours found: {len(contours)}"
        cv2.putText(frame_with_contours, info_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Show the largest contour info
        if contours:
            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)
            (x, y), radius = cv2.minEnclosingCircle(largest)
            
            cv2.circle(frame_with_contours, (int(x), int(y)), int(radius), (255, 0, 0), 2)
            
            info = f"Largest: Area={int(area)}, Radius={int(radius)}"
            cv2.putText(frame_with_contours, info, (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # Stack images for display
        top_row = np.hstack([frame_with_contours, cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)])
        bottom_row = np.hstack([result, hsv])
        combined = np.vstack([top_row, bottom_row])
        
        # Add labels
        cv2.putText(combined, "Original + Contours", (10, 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(combined, "Mask", (650, 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(combined, "Filtered Result", (10, 500),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(combined, "HSV", (650, 500),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.imshow(window_name, combined)
        
        # Handle keyboard
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            # Print final values
            print("\n" + "=" * 60)
            print("CALIBRATED VALUES:")
            print("=" * 60)
            print(f"lower_green = np.array([{h_min}, {s_min}, {v_min}])")
            print(f"upper_green = np.array([{h_max}, {s_max}, {v_max}])")
            print(f"morph_kernel_size = {morph_size}")
            print("\nCopy these values into your green_circle_detector.py file!")
            print("=" * 60)
            break
            
        elif key == ord('s'):
            # Save snapshot
            filename = f"calibration_snapshot_{int(cv2.getTickCount())}.jpg"
            cv2.imwrite(filename, combined)
            print(f"Snapshot saved: {filename}")
    
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    calibrate_green_detection()

