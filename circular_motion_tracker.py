#!/usr/bin/env python3
"""
Circular Motion Tracker
Tracks targets moving in circular paths and predicts when they'll reach shooting point
"""

import cv2
import numpy as np
import time
from collections import deque
import math

class CircleFitter:
    """
    Fits a circle to a set of points to find center and radius
    """
    @staticmethod
    def fit_circle_least_squares(points):
        """
        Fit a circle to points using least squares method
        Args:
            points: array of (x, y) coordinates
        Returns:
            (center_x, center_y, radius) or None if fitting fails
        """
        if len(points) < 3:
            return None
        
        points = np.array(points, dtype=float)
        x = points[:, 0]
        y = points[:, 1]
        
        # Use algebraic fit: (x - cx)^2 + (y - cy)^2 = r^2
        # Rearrange to: x^2 + y^2 = 2*cx*x + 2*cy*y + (r^2 - cx^2 - cy^2)
        
        n = len(points)
        
        # Build matrices for least squares
        A = np.column_stack([x, y, np.ones(n)])
        b = x**2 + y**2
        
        try:
            # Solve using least squares
            c, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
            
            cx = c[0] / 2
            cy = c[1] / 2
            r = np.sqrt(c[2] + cx**2 + cy**2)
            
            return (cx, cy, r)
        except:
            return None
    
    @staticmethod
    def fit_circle_algebraic(points):
        """
        Alternative circle fitting using algebraic method (Pratt method)
        More robust for noisy data
        """
        if len(points) < 3:
            return None
        
        points = np.array(points, dtype=float)
        
        # Center the data
        mean_x = np.mean(points[:, 0])
        mean_y = np.mean(points[:, 1])
        
        x = points[:, 0] - mean_x
        y = points[:, 1] - mean_y
        
        # Build design matrix
        z = x**2 + y**2
        A = np.column_stack([x, y, np.ones(len(points))])
        
        try:
            # Solve
            c, _, _, _ = np.linalg.lstsq(A, z, rcond=None)
            
            # Extract center and radius
            cx = c[0] / 2 + mean_x
            cy = c[1] / 2 + mean_y
            r = np.sqrt(c[2] + (c[0]**2 + c[1]**2) / 4)
            
            return (cx, cy, r)
        except:
            return None


class CircularMotionTracker:
    """
    Tracks circular motion and predicts intersection with shooting point
    """
    def __init__(self, history_duration=1.0, max_samples=30):
        self.history_duration = history_duration
        self.max_samples = max_samples
        
        # Position history
        self.positions = deque(maxlen=max_samples)
        self.timestamps = deque(maxlen=max_samples)
        
        # Circle parameters (calculated)
        self.center = None  # (cx, cy)
        self.radius = None
        self.angular_velocity = None  # degrees per second
        self.clockwise = True
        
        # Current state
        self.current_angle = None  # degrees (0° = right, 90° = down)
        self.is_fitted = False
        
        self.fitter = CircleFitter()
    
    def update(self, position, timestamp):
        """Add new position data"""
        self.positions.append(position)
        self.timestamps.append(timestamp)
        
        # Remove old samples
        while len(self.timestamps) > 1:
            age = timestamp - self.timestamps[0]
            if age > self.history_duration:
                self.positions.popleft()
                self.timestamps.popleft()
            else:
                break
        
        # Try to fit circle if we have enough data
        if len(self.positions) >= 5:
            self._fit_circle()
            self._calculate_angular_velocity()
    
    def _fit_circle(self):
        """Fit a circle to the tracked positions"""
        result = self.fitter.fit_circle_least_squares(list(self.positions))
        
        if result is not None:
            cx, cy, r = result
            
            # Validate the fit (radius should be reasonable)
            if 20 < r < 500:  # Reasonable radius range in pixels
                self.center = (cx, cy)
                self.radius = r
                self.is_fitted = True
                
                # Calculate current angle
                if len(self.positions) > 0:
                    last_pos = self.positions[-1]
                    self.current_angle = self._calculate_angle(last_pos)
            else:
                self.is_fitted = False
    
    def _calculate_angle(self, point):
        """
        Calculate angle of a point relative to circle center
        Returns angle in degrees (0° = right, 90° = down, -90° = up, ±180° = left)
        """
        if self.center is None:
            return None
        
        dx = point[0] - self.center[0]
        dy = point[1] - self.center[1]
        
        angle = np.degrees(np.arctan2(dy, dx))
        return angle
    
    def _calculate_angular_velocity(self):
        """Calculate angular velocity (degrees per second)"""
        if not self.is_fitted or len(self.positions) < 2:
            return
        
        # Calculate angles for all positions
        angles = []
        times = []
        
        for i, pos in enumerate(self.positions):
            angle = self._calculate_angle(pos)
            if angle is not None:
                angles.append(angle)
                times.append(self.timestamps[i])
        
        if len(angles) < 2:
            return
        
        # Calculate angular differences (handle wraparound at ±180°)
        angular_diffs = []
        time_diffs = []
        
        for i in range(1, len(angles)):
            angle_diff = angles[i] - angles[i-1]
            
            # Handle wraparound (e.g., from +179° to -179° is +2°, not -358°)
            if angle_diff > 180:
                angle_diff -= 360
            elif angle_diff < -180:
                angle_diff += 360
            
            angular_diffs.append(angle_diff)
            time_diffs.append(times[i] - times[i-1])
        
        if len(angular_diffs) > 0 and sum(time_diffs) > 0:
            # Calculate average angular velocity
            total_angle_change = sum(angular_diffs)
            total_time = sum(time_diffs)
            
            self.angular_velocity = total_angle_change / total_time
            
            # Determine direction (negative = clockwise in screen coords)
            self.clockwise = (self.angular_velocity < 0)
    
    def time_to_angle(self, target_angle):
        """
        Calculate time until target reaches a specific angle
        Args:
            target_angle: target angle in degrees
        Returns:
            time in seconds, or None if not enough data
        """
        if not self.is_fitted or self.angular_velocity is None or self.current_angle is None:
            return None
        
        if abs(self.angular_velocity) < 0.1:  # Too slow or stopped
            return None
        
        # Calculate angle difference
        angle_diff = target_angle - self.current_angle
        
        # Handle wraparound
        if angle_diff > 180:
            angle_diff -= 360
        elif angle_diff < -180:
            angle_diff += 360
        
        # Check if we're moving toward the target angle
        if self.clockwise and angle_diff > 0:
            angle_diff -= 360
        elif not self.clockwise and angle_diff < 0:
            angle_diff += 360
        
        # Calculate time
        time_to_target = angle_diff / self.angular_velocity
        
        # Return only positive times (future)
        return time_to_target if time_to_target > 0 else None
    
    def time_to_point(self, target_point):
        """
        Calculate time until target reaches a specific point
        Args:
            target_point: (x, y) pixel coordinates
        Returns:
            time in seconds, or None
        """
        if not self.is_fitted:
            return None
        
        # Calculate angle of target point
        target_angle = self._calculate_angle(target_point)
        
        if target_angle is None:
            return None
        
        return self.time_to_angle(target_angle)
    
    def predict_position(self, time_ahead):
        """
        Predict position after time_ahead seconds
        Args:
            time_ahead: seconds into the future
        Returns:
            (x, y) predicted position or None
        """
        if not self.is_fitted or self.angular_velocity is None or self.current_angle is None:
            return None
        
        # Calculate future angle
        future_angle = self.current_angle + self.angular_velocity * time_ahead
        
        # Convert angle back to cartesian coordinates
        angle_rad = np.radians(future_angle)
        x = self.center[0] + self.radius * np.cos(angle_rad)
        y = self.center[1] + self.radius * np.sin(angle_rad)
        
        return (int(x), int(y))
    
    def get_circle_points(self, num_points=100):
        """Get points along the fitted circle for visualization"""
        if not self.is_fitted:
            return None
        
        angles = np.linspace(0, 2*np.pi, num_points)
        points = []
        
        for angle in angles:
            x = int(self.center[0] + self.radius * np.cos(angle))
            y = int(self.center[1] + self.radius * np.sin(angle))
            points.append((x, y))
        
        return points
    
    def reset(self):
        """Clear all tracking data"""
        self.positions.clear()
        self.timestamps.clear()
        self.center = None
        self.radius = None
        self.angular_velocity = None
        self.current_angle = None
        self.is_fitted = False
    
    def is_ready(self):
        """Check if we have enough data for predictions"""
        return self.is_fitted and self.angular_velocity is not None


class CircularShootingSystem:
    """
    Complete system for detecting circular targets and shooting at fixed point
    """
    def __init__(self):
        # Camera setup
        self.camera = cv2.VideoCapture(0)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        
        # Detection parameters
        self.lower_green = np.array([35, 50, 50])
        self.upper_green = np.array([85, 255, 255])
        self.min_circle_radius = 5
        self.max_circle_radius = 100
        self.min_area = 50
        
        # Motion tracker
        self.tracker = CircularMotionTracker(history_duration=1.0, max_samples=30)
        
        # Shooting point (click to set)
        self.shooting_point = None
        self.shooting_point_set = False
        
        # Display settings
        self.show_circle_fit = True
        self.show_trajectory = True
        self.show_mask = False
        
        # Shooting parameters
        self.shoot_lead_time = 0.0  # Additional lead time in seconds (motor delay)
        self.min_shoot_time = 0.2   # Minimum time ahead to shoot
        self.max_shoot_time = 5.0   # Maximum time ahead to shoot
        
        # Setup mouse callback
        cv2.namedWindow('Circular Shooting System')
        cv2.setMouseCallback('Circular Shooting System', self._mouse_callback)
    
    def _mouse_callback(self, event, x, y, flags, param):
        """Handle mouse clicks to set shooting point"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.shooting_point = (x, y)
            self.shooting_point_set = True
            print(f"Shooting point set to: ({x}, {y})")
    
    def detect_green_circles(self, frame):
        """Detect green circles in frame"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_green, self.upper_green)
        
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detected_circles = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_area:
                continue
            
            (x, y), radius = cv2.minEnclosingCircle(contour)
            
            if radius < self.min_circle_radius or radius > self.max_circle_radius:
                continue
            
            perimeter = cv2.arcLength(contour, True)
            if perimeter > 0:
                circularity = 4 * np.pi * area / (perimeter * perimeter)
                if circularity > 0.6:
                    detected_circles.append({
                        'center': (int(x), int(y)),
                        'radius': int(radius),
                        'area': area
                    })
        
        return detected_circles, mask
    
    def draw_visualization(self, frame):
        """Draw all visualization elements"""
        output = frame.copy()
        
        # Draw fitted circle path
        if self.show_circle_fit and self.tracker.is_fitted:
            circle_points = self.tracker.get_circle_points()
            if circle_points:
                for i in range(len(circle_points) - 1):
                    cv2.line(output, circle_points[i], circle_points[i+1], (255, 200, 0), 1)
                
                # Draw center
                center = (int(self.tracker.center[0]), int(self.tracker.center[1]))
                cv2.circle(output, center, 5, (255, 0, 0), -1)
                cv2.circle(output, center, int(self.tracker.radius), (255, 200, 0), 2)
                
                cv2.putText(output, "CENTER", (center[0] + 10, center[1] - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
        # Draw current target position
        if len(self.tracker.positions) > 0:
            current = self.tracker.positions[-1]
            cv2.circle(output, current, 8, (0, 255, 0), 2)
            cv2.circle(output, current, 3, (0, 0, 255), -1)
        
        # Draw position history trail
        if len(self.tracker.positions) > 1:
            points = list(self.tracker.positions)
            for i in range(len(points) - 1):
                alpha = (i + 1) / len(points)
                color = (0, int(150 * alpha), int(255 * alpha))
                cv2.line(output, points[i], points[i + 1], color, 2)
        
        # Draw shooting point
        if self.shooting_point_set:
            cv2.circle(output, self.shooting_point, 15, (0, 0, 255), 3)
            cv2.line(output, (self.shooting_point[0] - 20, self.shooting_point[1]),
                    (self.shooting_point[0] + 20, self.shooting_point[1]), (0, 0, 255), 3)
            cv2.line(output, (self.shooting_point[0], self.shooting_point[1] - 20),
                    (self.shooting_point[0], self.shooting_point[1] + 20), (0, 0, 255), 3)
            cv2.putText(output, "SHOOT HERE", 
                       (self.shooting_point[0] + 20, self.shooting_point[1] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Draw trajectory prediction
        if self.show_trajectory and self.tracker.is_ready():
            for t in [0.5, 1.0, 1.5, 2.0]:
                pred_pos = self.tracker.predict_position(t)
                if pred_pos:
                    cv2.circle(output, pred_pos, 5, (255, 0, 255), 2)
                    cv2.putText(output, f"+{t}s", 
                              (pred_pos[0] + 10, pred_pos[1] - 10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)
        
        return output
    
    def draw_info_panel(self, frame):
        """Draw information panel"""
        output = frame.copy()
        
        # Info panel background
        cv2.rectangle(output, (5, 5), (450, 250), (0, 0, 0), -1)
        cv2.rectangle(output, (5, 5), (450, 250), (0, 255, 0), 2)
        
        y = 30
        h = 25
        
        # Status
        if self.tracker.is_ready():
            status = "TRACKING - READY TO SHOOT"
            color = (0, 255, 0)
        elif self.tracker.is_fitted:
            status = "CIRCLE FITTED - CALCULATING..."
            color = (0, 255, 255)
        else:
            status = "ACQUIRING TARGET DATA..."
            color = (0, 165, 255)
        
        cv2.putText(output, f"Status: {status}", (15, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        y += h
        
        # Samples
        samples = len(self.tracker.positions)
        cv2.putText(output, f"Samples: {samples}/30", (15, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y += h
        
        # Circle parameters
        if self.tracker.is_fitted:
            cv2.putText(output, f"Center: ({int(self.tracker.center[0])}, {int(self.tracker.center[1])})", 
                       (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y += h
            
            cv2.putText(output, f"Radius: {int(self.tracker.radius)} px", 
                       (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y += h
            
            if self.tracker.angular_velocity:
                direction = "CW" if self.tracker.clockwise else "CCW"
                cv2.putText(output, f"Speed: {abs(self.tracker.angular_velocity):.1f} °/s ({direction})", 
                           (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                y += h
                
                if self.tracker.current_angle is not None:
                    cv2.putText(output, f"Current angle: {self.tracker.current_angle:.1f}°", 
                               (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    y += h
        
        y += 5
        
        # Shooting info
        if self.shooting_point_set:
            cv2.putText(output, f"Shoot point: {self.shooting_point}", 
                       (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            y += h
            
            # Calculate time to shooting point
            if self.tracker.is_ready():
                time_to_shoot = self.tracker.time_to_point(self.shooting_point)
                
                if time_to_shoot is not None and time_to_shoot > 0:
                    cv2.putText(output, f"Time to target: {time_to_shoot:.2f} sec", 
                               (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    y += h
                    
                    # Should we shoot?
                    if self.min_shoot_time < time_to_shoot < self.max_shoot_time:
                        cv2.putText(output, ">>> READY TO FIRE! <<<", 
                                   (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                else:
                    cv2.putText(output, "Waiting for next pass...", 
                               (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 1)
        else:
            cv2.putText(output, "Click to set shooting point", 
                       (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 165, 0), 1)
        
        return output
    
    def run(self):
        """Main system loop"""
        print("=" * 60)
        print("CIRCULAR MOTION SHOOTING SYSTEM")
        print("=" * 60)
        print("\nFeatures:")
        print("  • Detects green circles")
        print("  • Tracks circular motion for 1 second")
        print("  • Calculates circle center and rotation speed")
        print("  • Predicts when target reaches shooting point")
        print("\nSetup:")
        print("  1. Move target in circular path")
        print("  2. Wait ~1 second for system to track")
        print("  3. Click on screen to set SHOOTING POINT")
        print("  4. System will calculate when to fire!")
        print("\nControls:")
        print("  q - Quit")
        print("  m - Toggle mask view")
        print("  c - Toggle circle visualization")
        print("  r - Reset tracking")
        print("  CLICK - Set shooting point")
        print()
        
        fps_time = time.time()
        fps_counter = 0
        fps_display = 0
        
        try:
            while True:
                loop_start = time.time()
                
                # Capture frame
                ret, frame = self.camera.read()
                if not ret:
                    print("Error: Could not read frame")
                    break
                
                # Detect circles
                circles, mask = self.detect_green_circles(frame)
                
                # Track the largest circle
                if circles:
                    circles.sort(key=lambda c: c['area'], reverse=True)
                    target = circles[0]
                    self.tracker.update(target['center'], time.time())
                else:
                    # No target detected - keep existing tracking data
                    pass
                
                # Draw visualization
                frame = self.draw_visualization(frame)
                frame = self.draw_info_panel(frame)
                
                # FPS
                fps_counter += 1
                if time.time() - fps_time > 1.0:
                    fps_display = fps_counter
                    fps_counter = 0
                    fps_time = time.time()
                
                cv2.putText(frame, f"FPS: {fps_display}", (frame.shape[1] - 100, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                
                # Show windows
                cv2.imshow('Circular Shooting System', frame)
                
                if self.show_mask:
                    cv2.imshow('Mask', mask)
                
                # Handle keyboard
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    break
                elif key == ord('m'):
                    self.show_mask = not self.show_mask
                    if not self.show_mask:
                        cv2.destroyWindow('Mask')
                elif key == ord('c'):
                    self.show_circle_fit = not self.show_circle_fit
                    print(f"Circle visualization: {'ON' if self.show_circle_fit else 'OFF'}")
                elif key == ord('r'):
                    self.tracker.reset()
                    print("Tracker reset")
                
                # Maintain timing
                elapsed = time.time() - loop_start
                if elapsed < 0.033:
                    time.sleep(0.033 - elapsed)
        
        except KeyboardInterrupt:
            print("\nStopping...")
        
        finally:
            self.camera.release()
            cv2.destroyAllWindows()
            print("System stopped.")


def main():
    system = CircularShootingSystem()
    system.run()


if __name__ == "__main__":
    main()

