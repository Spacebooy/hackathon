#!/usr/bin/env python3
"""
Proximity Shooter
Detects green circles and shoots when they get close to the crosshair
"""

import cv2
import numpy as np
import time

# Try to import RPi.GPIO for Raspberry Pi
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
    print("✓ RPi.GPIO loaded - Motor control ENABLED")
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠ RPi.GPIO not available - Motor control DISABLED (simulation mode)")


class MotorController:
    """
    Controls the torque motor to fire the nerf gun
    """
    def __init__(self, motor_pin=17, fire_duration=0.15):
        """
        Args:
            motor_pin: GPIO pin number (BCM mode)
            fire_duration: How long to activate motor (seconds)
        """
        self.motor_pin = motor_pin
        self.fire_duration = fire_duration
        self.enabled = GPIO_AVAILABLE
        
        if self.enabled:
            # Setup GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.motor_pin, GPIO.OUT)
            GPIO.output(self.motor_pin, GPIO.LOW)
            print(f"✓ Motor controller initialized on GPIO pin {self.motor_pin}")
        else:
            print("⚠ Motor controller in simulation mode")
    
    def fire(self):
        """Trigger the motor to fire"""
        if self.enabled:
            # Activate motor
            GPIO.output(self.motor_pin, GPIO.HIGH)
            time.sleep(self.fire_duration)
            GPIO.output(self.motor_pin, GPIO.LOW)
            print(f"  → Motor fired for {self.fire_duration}s")
        else:
            # Simulation mode
            print(f"  → [SIMULATION] Motor would fire for {self.fire_duration}s")
    
    def cleanup(self):
        """Cleanup GPIO"""
        if self.enabled:
            GPIO.output(self.motor_pin, GPIO.LOW)
            GPIO.cleanup()
            print("✓ Motor controller cleaned up")


class ProximityShooter:
    """
    Simple shooting system - fires when target gets close to shooting point
    """
    def __init__(self, motor_pin=17, fire_duration=0.15):
        """
        Args:
            motor_pin: GPIO pin for motor control (default: GPIO 17)
            fire_duration: How long to activate motor in seconds (default: 0.15s)
        """
        # Motor controller
        self.motor = MotorController(motor_pin=motor_pin, fire_duration=fire_duration)
        
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
        
        # Shooting parameters
        self.shooting_point = None  # (x, y) where to shoot
        self.shooting_point_set = False
        self.fire_distance = 30  # Fire when target within this many pixels
        
        # Firing state
        self.last_fire_time = 0
        self.fire_cooldown = 1.0  # Minimum time between shots (seconds)
        self.armed = True
        
        # Target tracking - simpler approach
        self.target_in_zone = False  # Is there currently a target in the "getting close" zone?
        self.zone_was_clear = True   # Was the zone clear on last frame?
        
        # Velocity tracking for lead compensation
        self.target_positions = []  # Recent positions
        self.target_timestamps = []  # Recent timestamps
        self.max_tracking_samples = 10  # Keep last 10 positions
        self.target_velocity = None  # (vx, vy) in pixels/second
        
        # Lead compensation settings
        self.motor_delay = 0.05  # Time for motor to fire (seconds)
        self.dart_speed = 15.0   # Nerf dart speed (m/s) - adjust based on your gun
        self.pixels_per_meter = 200  # Rough estimate - calibrate this!
        self.lead_compensation_enabled = True  # Toggle with 'l' key
        
        # Display settings
        self.show_mask = False
        self.show_distance_circle = True
        
        # Setup mouse callback
        cv2.namedWindow('Proximity Shooter')
        cv2.setMouseCallback('Proximity Shooter', self._mouse_callback)
        
        # Statistics
        self.shot_count = 0
        
    def _mouse_callback(self, event, x, y, flags, param):
        """Handle mouse clicks to set shooting point"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.shooting_point = (x, y)
            self.shooting_point_set = True
            print(f"\n🎯 Shooting point set to: ({x}, {y})")
            print(f"   Will fire when target within {self.fire_distance} pixels")
    
    def detect_green_circles(self, frame):
        """
        Detect all green circles in frame
        Returns: list of circles, mask
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_green, self.upper_green)
        
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        circles = []
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
                    circles.append({
                        'center': (int(x), int(y)),
                        'radius': int(radius),
                        'area': area
                    })
        
        return circles, mask
    
    def calculate_distance(self, point1, point2):
        """Calculate Euclidean distance between two points"""
        dx = point1[0] - point2[0]
        dy = point1[1] - point2[1]
        return np.sqrt(dx*dx + dy*dy)
    
    def update_velocity(self, position, timestamp):
        """Track target velocity for lead compensation"""
        self.target_positions.append(position)
        self.target_timestamps.append(timestamp)
        
        # Keep only recent samples
        if len(self.target_positions) > self.max_tracking_samples:
            self.target_positions.pop(0)
            self.target_timestamps.pop(0)
        
        # Calculate velocity if we have enough samples
        if len(self.target_positions) >= 3:
            positions = np.array(self.target_positions)
            timestamps = np.array(self.target_timestamps)
            
            # Time delta
            t = timestamps - timestamps[0]
            
            # Linear regression for velocity
            if len(t) > 1 and (t[-1] - t[0]) > 0:
                vx = (positions[-1, 0] - positions[0, 0]) / (t[-1] - t[0])
                vy = (positions[-1, 1] - positions[0, 1]) / (t[-1] - t[0])
                self.target_velocity = (vx, vy)
            else:
                self.target_velocity = (0, 0)
        else:
            self.target_velocity = None
    
    def calculate_lead_distance(self, current_pos):
        """
        Calculate how much lead distance we need
        Returns: distance in pixels to fire early
        """
        if not self.lead_compensation_enabled or self.target_velocity is None:
            return 0
        
        if self.shooting_point is None:
            return 0
        
        # Calculate distance to target
        distance_px = self.calculate_distance(current_pos, self.shooting_point)
        distance_m = distance_px / self.pixels_per_meter
        
        # Calculate dart travel time
        dart_travel_time = distance_m / self.dart_speed if self.dart_speed > 0 else 0
        
        # Total delay = motor delay + dart travel time
        total_delay = self.motor_delay + dart_travel_time
        
        # Calculate how far target moves during this delay
        vx, vy = self.target_velocity
        speed = np.sqrt(vx**2 + vy**2)  # pixels/second
        
        # Lead distance = speed * total_delay
        lead_distance = speed * total_delay
        
        return lead_distance
    
    def should_fire(self):
        """
        Check if we should fire:
        1. Cooldown has passed
        2. Zone was clear before (new target entering)
        """
        current_time = time.time()
        cooldown_passed = current_time - self.last_fire_time >= self.fire_cooldown
        return cooldown_passed and self.zone_was_clear
    
    def fire(self):
        """Trigger the shooting mechanism"""
        self.last_fire_time = time.time()
        self.shot_count += 1
        
        # Print visible fire line
        print("\n" + "=" * 60)
        print(f"🔥🔥🔥 FIRE! FIRE! FIRE! 🔥🔥🔥 (Shot #{self.shot_count})")
        print("=" * 60)
        
        # Trigger the motor
        self.motor.fire()
        
        # Cooldown notice
        print(f"⏱️  Cooldown: {self.fire_cooldown}s (next shot available at {time.time() + self.fire_cooldown:.2f})")
    
    def draw_shooting_point(self, frame):
        """Draw the shooting target point"""
        if not self.shooting_point_set:
            # Draw instruction
            h, w = frame.shape[:2]
            cv2.putText(frame, "Click to set shooting point", 
                       (w//2 - 150, h//2),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            return
        
        # Draw crosshair
        x, y = self.shooting_point
        size = 25
        
        # Lines
        cv2.line(frame, (x - size, y), (x + size, y), (0, 0, 255), 3)
        cv2.line(frame, (x, y - size), (x, y + size), (0, 0, 255), 3)
        
        # Center circle
        cv2.circle(frame, self.shooting_point, 8, (0, 0, 255), 2)
        
        # Label
        cv2.putText(frame, "SHOOT HERE", (x + 30, y - 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Fire distance circle
        if self.show_distance_circle:
            cv2.circle(frame, self.shooting_point, self.fire_distance, (255, 0, 0), 2)
            cv2.putText(frame, f"{self.fire_distance}px", (x + 35, y + 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
    
    def draw_circles(self, frame, circles):
        """Draw detected circles and check for firing"""
        closest_distance = float('inf')
        closest_circle = None
        warning_zone_distance = self.fire_distance * 2  # Yellow "getting close" zone (normal)
        
        # Track if any target is in the FIRE zone this frame (red zone)
        current_target_in_fire_zone = False
        
        for circle in circles:
            center = circle['center']
            radius = circle['radius']
            
            # Calculate distance to shooting point
            if self.shooting_point_set:
                distance = self.calculate_distance(center, self.shooting_point)
                
                # Update velocity tracking (for lead compensation)
                self.update_velocity(center, time.time())
                
                # Calculate lead-compensated distance
                lead_distance = self.calculate_lead_distance(center)
                effective_distance = distance - lead_distance  # Fire when "earlier" by lead amount
                
                # Check if in fire zone (red zone) - this is what prevents re-firing
                if distance <= self.fire_distance:
                    current_target_in_fire_zone = True
                
                # Color based on distance
                if distance <= self.fire_distance:
                    color = (0, 0, 255)  # Red - in fire zone!
                    thickness = 3
                    
                    if effective_distance < closest_distance:  # Use lead-compensated distance
                        closest_distance = effective_distance
                        closest_circle = circle
                elif distance <= warning_zone_distance:
                    color = (0, 255, 255)  # Yellow - getting close
                    thickness = 2
                else:
                    color = (0, 255, 0)  # Green - far away
                    thickness = 2
                
                # Draw circle
                cv2.circle(frame, center, radius, color, thickness)
                cv2.circle(frame, center, 3, (0, 0, 255), -1)
                
                # Draw distance line
                cv2.line(frame, center, self.shooting_point, (128, 128, 128), 1)
                
                # Distance label
                mid_x = (center[0] + self.shooting_point[0]) // 2
                mid_y = (center[1] + self.shooting_point[1]) // 2
                label = f"{int(distance)}px"
                if self.lead_compensation_enabled and self.target_velocity:
                    lead_dist = self.calculate_lead_distance(center)
                    label += f" (lead:{int(lead_dist)}px)"
                cv2.putText(frame, label, (mid_x, mid_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            else:
                # No shooting point set - just draw green
                cv2.circle(frame, center, radius, (0, 255, 0), 2)
                cv2.circle(frame, center, 3, (0, 0, 255), -1)
        
        # Fire if: closest circle in fire zone AND conditions met
        if closest_circle is not None and self.should_fire():
            self.fire()
            self.zone_was_clear = False  # Prevent immediate re-fire
            
            # Visual feedback
            cv2.circle(frame, self.shooting_point, 50, (0, 0, 255), 5)
        
        # Update zone state AFTER firing check
        # Only reset when FIRE zone (red) clears, not just the yellow zone
        if not current_target_in_fire_zone and self.target_in_zone:
            # Fire zone just cleared - can fire at next target
            self.zone_was_clear = True
        
        self.target_in_zone = current_target_in_fire_zone
    
    def draw_info_panel(self, frame):
        """Draw information panel"""
        # Background
        cv2.rectangle(frame, (5, 5), (350, 180), (0, 0, 0), -1)
        cv2.rectangle(frame, (5, 5), (350, 180), (0, 255, 0), 2)
        
        y = 30
        h = 25
        
        # Title
        cv2.putText(frame, "PROXIMITY SHOOTER", (15, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        y += h + 5
        
        # Armed status
        if self.should_fire():
            status = "✓ ARMED - READY TO FIRE"
            color = (0, 255, 0)
        else:
            cooldown_remaining = self.fire_cooldown - (time.time() - self.last_fire_time)
            status = f"⏱️ COOLDOWN: {cooldown_remaining:.2f}s"
            color = (0, 165, 255)
            
            # Draw cooldown progress bar
            bar_width = 320
            bar_height = 10
            progress = max(0.0, min(1.0, cooldown_remaining / self.fire_cooldown))  # Clamp 0-1
            filled_width = int(bar_width * (1 - progress))
            filled_width = max(0, min(bar_width, filled_width))  # Clamp to valid range
            
            # Background bar
            cv2.rectangle(frame, (15, y + 5), (15 + bar_width, y + 5 + bar_height), (50, 50, 50), -1)
            # Progress bar (only draw if filled_width > 0)
            if filled_width > 0:
                cv2.rectangle(frame, (15, y + 5), (15 + filled_width, y + 5 + bar_height), (0, 255, 0), -1)
            # Border
            cv2.rectangle(frame, (15, y + 5), (15 + bar_width, y + 5 + bar_height), (255, 255, 255), 1)
        
        cv2.putText(frame, f"Status: {status}", (15, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        y += h + 15  # Extra space for progress bar
        
        # Shot count
        cv2.putText(frame, f"Shots fired: {self.shot_count}", (15, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y += h
        
        # Zone status (tracks fire zone - red zone)
        zone_status = "Target in FIRE ZONE" if self.target_in_zone else "Fire zone clear ✓"
        zone_color = (0, 0, 255) if self.target_in_zone else (0, 255, 0)
        cv2.putText(frame, f"Zone: {zone_status}", (15, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, zone_color, 1)
        y += h
        
        # Shooting point
        if self.shooting_point_set:
            cv2.putText(frame, f"Target: {self.shooting_point}", (15, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y += h
            
            cv2.putText(frame, f"Fire distance: {self.fire_distance}px", (15, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y += h
            
            # Lead compensation status
            lead_status = "ON" if self.lead_compensation_enabled else "OFF"
            lead_color = (0, 255, 0) if self.lead_compensation_enabled else (128, 128, 128)
            cv2.putText(frame, f"Lead comp: {lead_status}", (15, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, lead_color, 1)
            
            # Show velocity if available
            if self.target_velocity and self.lead_compensation_enabled:
                vx, vy = self.target_velocity
                speed = np.sqrt(vx**2 + vy**2)
                cv2.putText(frame, f"  Speed: {int(speed)}px/s", (15, y + 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        else:
            cv2.putText(frame, "Click to set target", (15, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 165, 0), 1)
        
        return frame
    
    def run(self):
        """Main loop"""
        print("=" * 60)
        print("PROXIMITY SHOOTER")
        print("=" * 60)
        print("\nHow it works:")
        print("  1. Click to set shooting point (crosshair)")
        print("  2. Move green circle toward the crosshair")
        print("  3. System fires automatically when circle gets close!")
        print("\nControls:")
        print("  CLICK - Set shooting point")
        print("  q     - Quit")
        print("  r     - Reset shot counter")
        print("  m     - Toggle mask view")
        print("  l     - Toggle LEAD COMPENSATION (predict target movement)")
        print("  +     - Increase fire distance")
        print("  -     - Decrease fire distance")
        print()
        print("Note: Won't fire again until target exits the RED fire zone (30px)")
        print("      Yellow 'getting close' zone is 2x fire distance (60px)")
        print("      LEAD COMPENSATION: Fires earlier to hit moving targets!")
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
                    print("Error reading frame")
                    break
                
                # Detect circles
                circles, mask = self.detect_green_circles(frame)
                
                # Draw visualization
                self.draw_shooting_point(frame)
                self.draw_circles(frame, circles)
                frame = self.draw_info_panel(frame)
                
                # FPS
                fps_counter += 1
                if time.time() - fps_time > 1.0:
                    fps_display = fps_counter
                    fps_counter = 0
                    fps_time = time.time()
                
                cv2.putText(frame, f"FPS: {fps_display}", 
                           (frame.shape[1] - 100, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                
                # Circles detected
                cv2.putText(frame, f"Targets: {len(circles)}", 
                           (frame.shape[1] - 130, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # Show windows
                cv2.imshow('Proximity Shooter', frame)
                
                if self.show_mask:
                    cv2.imshow('Mask', mask)
                
                # Handle keyboard
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    break
                elif key == ord('r'):
                    self.shot_count = 0
                    self.target_in_zone = False
                    self.zone_was_clear = True
                    print("\n🔄 Shot counter reset and zone cleared")
                elif key == ord('m'):
                    self.show_mask = not self.show_mask
                    if not self.show_mask:
                        cv2.destroyWindow('Mask')
                elif key == ord('l'):
                    self.lead_compensation_enabled = not self.lead_compensation_enabled
                    status = "ENABLED" if self.lead_compensation_enabled else "DISABLED"
                    print(f"\n🎯 Lead compensation {status}")
                elif key == ord('+') or key == ord('='):
                    self.fire_distance += 5
                    print(f"Fire distance: {self.fire_distance}px")
                elif key == ord('-'):
                    self.fire_distance = max(10, self.fire_distance - 5)
                    print(f"Fire distance: {self.fire_distance}px")
                
                # Maintain timing
                elapsed = time.time() - loop_start
                if elapsed < 0.033:
                    time.sleep(0.033 - elapsed)
        
        except KeyboardInterrupt:
            print("\nStopping...")
        
        finally:
            self.camera.release()
            cv2.destroyAllWindows()
            self.motor.cleanup()
            print(f"\nFinal stats: {self.shot_count} shots fired")
            print("System stopped.")


def main():
    """
    Main entry point
    Default configuration:
      - Motor GPIO Pin: 17 (BCM mode)
      - Fire duration: 0.15 seconds
    
    To change, edit this function or create new instance:
      shooter = ProximityShooter(motor_pin=18, fire_duration=0.2)
    """
    shooter = ProximityShooter(motor_pin=17, fire_duration=0.15)
    shooter.run()


if __name__ == "__main__":
    main()

