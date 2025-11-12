#!/usr/bin/env python3
"""
Green Circle Detector
Detects small green circular targets moving in the camera view
"""

import cv2
import numpy as np
import time

class GreenCircleDetector:
    def __init__(self):
        # Initialize camera
        self.camera = cv2.VideoCapture(0)
        
        # Set camera resolution
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        
        # Green color range in HSV
        # These are starting values - you may need to calibrate
        self.lower_green = np.array([35, 50, 50])   # Lower bound for green
        self.upper_green = np.array([85, 255, 255]) # Upper bound for green
        
        # Circle detection parameters
        self.min_circle_radius = 5    # Minimum radius in pixels
        self.max_circle_radius = 100  # Maximum radius in pixels
        self.min_area = 50            # Minimum contour area
        
        # Display settings
        self.show_mask = True
        self.show_contours = True
        
    def detect_green_circles(self, frame):
        """
        Detect green circles in the frame
        Returns: list of (x, y, radius) tuples
        """
        # Convert to HSV color space
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Create mask for green color
        mask = cv2.inRange(hsv, self.lower_green, self.upper_green)
        
        # Apply morphological operations to clean up the mask
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)  # Remove noise
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel) # Fill holes
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detected_circles = []
        
        for contour in contours:
            # Filter by area
            area = cv2.contourArea(contour)
            if area < self.min_area:
                continue
            
            # Get the minimum enclosing circle
            (x, y), radius = cv2.minEnclosingCircle(contour)
            
            # Filter by radius
            if radius < self.min_circle_radius or radius > self.max_circle_radius:
                continue
            
            # Check circularity (how round is it?)
            perimeter = cv2.arcLength(contour, True)
            if perimeter > 0:
                circularity = 4 * np.pi * area / (perimeter * perimeter)
                
                # Only accept shapes that are reasonably circular
                if circularity > 0.6:  # 1.0 is perfect circle
                    detected_circles.append({
                        'center': (int(x), int(y)),
                        'radius': int(radius),
                        'area': area,
                        'circularity': circularity,
                        'contour': contour
                    })
        
        return detected_circles, mask
    
    def draw_detections(self, frame, circles):
        """
        Draw detected circles on the frame
        """
        output = frame.copy()
        
        for circle in circles:
            center = circle['center']
            radius = circle['radius']
            
            # Draw the circle
            cv2.circle(output, center, radius, (0, 255, 0), 2)
            
            # Draw the center point
            cv2.circle(output, center, 3, (0, 0, 255), -1)
            
            # Add label with information
            label = f"R:{radius} C:{circle['circularity']:.2f}"
            cv2.putText(output, label, 
                       (center[0] - 30, center[1] - radius - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            
            # Draw crosshair
            cv2.line(output, (center[0] - 10, center[1]), 
                    (center[0] + 10, center[1]), (0, 255, 0), 1)
            cv2.line(output, (center[0], center[1] - 10), 
                    (center[0], center[1] + 10), (0, 255, 0), 1)
        
        return output
    
    def run(self):
        """
        Main detection loop
        """
        print("Green Circle Detector Started!")
        print("Controls:")
        print("  q - Quit")
        print("  m - Toggle mask view")
        print("  c - Toggle contour view")
        print("  + - Increase min radius")
        print("  - - Decrease min radius")
        print()
        
        fps_time = time.time()
        fps_counter = 0
        fps_display = 0
        
        try:
            while True:
                # Capture frame
                ret, frame = self.camera.read()
                if not ret:
                    print("Error: Could not read frame from camera")
                    break
                
                # Detect green circles
                circles, mask = self.detect_green_circles(frame)
                
                # Draw detections
                output = self.draw_detections(frame, circles)
                
                # Calculate FPS
                fps_counter += 1
                if time.time() - fps_time > 1.0:
                    fps_display = fps_counter
                    fps_counter = 0
                    fps_time = time.time()
                
                # Add info overlay
                info_text = [
                    f"FPS: {fps_display}",
                    f"Circles detected: {len(circles)}",
                    f"Min radius: {self.min_circle_radius}px",
                    f"Max radius: {self.max_circle_radius}px"
                ]
                
                y_offset = 30
                for i, text in enumerate(info_text):
                    cv2.putText(output, text, (10, y_offset + i * 25),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                
                # Display circle details
                if circles:
                    for i, circle in enumerate(circles[:3]):  # Show first 3
                        detail = f"Circle {i+1}: pos=({circle['center'][0]}, {circle['center'][1]})"
                        cv2.putText(output, detail, (10, 150 + i * 25),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # Show frames
                cv2.imshow('Green Circle Detection', output)
                
                if self.show_mask:
                    cv2.imshow('Mask', mask)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    break
                elif key == ord('m'):
                    self.show_mask = not self.show_mask
                    if not self.show_mask:
                        cv2.destroyWindow('Mask')
                elif key == ord('c'):
                    self.show_contours = not self.show_contours
                elif key == ord('+') or key == ord('='):
                    self.min_circle_radius += 1
                    print(f"Min radius: {self.min_circle_radius}")
                elif key == ord('-'):
                    self.min_circle_radius = max(1, self.min_circle_radius - 1)
                    print(f"Min radius: {self.min_circle_radius}")
                
        except KeyboardInterrupt:
            print("\nStopping...")
        
        finally:
            # Cleanup
            self.camera.release()
            cv2.destroyAllWindows()
            print("Camera released and windows closed.")


def main():
    detector = GreenCircleDetector()
    detector.run()


if __name__ == "__main__":
    main()

