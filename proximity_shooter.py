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
    def __init__(self, motor_pin=17, fire_duration=0.15, camera_device=0):
        """
        Args:
            motor_pin: GPIO pin for motor control (default: GPIO 17)
            fire_duration: How long to activate motor in seconds (default: 0.15s)
            camera_device: Video device number (default: 0)
        """
        # Motor controller
        self.motor = MotorController(motor_pin=motor_pin, fire_duration=fire_duration)
        
        # Camera setup - try common devices (prioritize 0 and 1 based on available devices)
        devices_to_try = [0, 1, camera_device] if camera_device not in [0, 1] else [camera_device, 0, 1]
        self.camera = None
        
        for device in devices_to_try:
            print(f"📷 Trying camera device {device}...")
            try:
                cam = cv2.VideoCapture(device, cv2.CAP_V4L2)  # Force V4L2 backend
                # Suppress GStreamer warnings
                cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M','J','P','G'))
                ret, test_frame = cam.read()
                if ret and test_frame is not None:
                    print(f"✓ Camera device {device} works! Frame size: {test_frame.shape[1]}x{test_frame.shape[0]}")
                    self.camera = cam
                    self.camera_device = device
                    break
                else:
                    cam.release()
                    print(f"  ✗ Device {device} failed to read")
            except Exception as e:
                print(f"  ✗ Device {device} error: {e}")
        
        if self.camera is None:
            print("❌ ERROR: Could not find a working camera!")
            print("   Available devices: /dev/video0, /dev/video1, /dev/video10, /dev/video11")
            print("   Try: ls -l /dev/video* to see all devices")
            self.motor.cleanup()
            raise RuntimeError("Camera initialization failed")
        
        print(f"✓ Using camera device {self.camera_device}")
        
        # Lower resolution for better FPS on Raspberry Pi
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer lag
        
        # Detection parameters
        self.lower_green = np.array([35, 50, 50])
        self.upper_green = np.array([85, 255, 255])
        self.min_circle_radius = 5
        self.max_circle_radius = 100
        self.min_area = 50
        
        # Shooting parameters - hardcoded for headless operation
        # Set to center of frame (320x240 resolution), 30 pixels below center
        self.shooting_point = (160, 150)  # (x, y) where to shoot - center is (160, 120), +30 = 150
        self.shooting_point_set = True
        self.fire_distance = 20  # Fire when target within this many pixels (adjusted for lower res)
        print(f"🎯 Shooting point set to: {self.shooting_point} (center + 30px down)")
        
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
        self.lead_compensation_enabled = True
        
        # Statistics
        self.shot_count = 0
        
    def detect_green_circles(self, frame):
        """
        Detect all green circles in frame
        Returns: list of circles, mask
        """
        # Resize for faster processing if needed
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_green, self.upper_green)
        
        # Simplified morphology for speed
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        circles = []
        for contour in contours:
            area = cv2.contourArea(contour)
            
            if area < self.min_area:
                continue
            
            (x, y), radius = cv2.minEnclosingCircle(contour)
            
            if radius < self.min_circle_radius or radius > self.max_circle_radius:
                continue
            
            # Simplified circularity check for speed (skip if too expensive)
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
    
    def process_targets(self, circles):
        """Process detected circles and check for firing (headless version)"""
        closest_distance = float('inf')
        closest_circle = None
        warning_zone_distance = self.fire_distance * 2
        
        # Track if any target is in the FIRE zone this frame (red zone)
        current_target_in_fire_zone = False
        
        for circle in circles:
            center = circle['center']
            
            if self.shooting_point_set:
                distance = self.calculate_distance(center, self.shooting_point)
                
                # Update velocity tracking (for lead compensation)
                self.update_velocity(center, time.time())
                
                # Calculate lead-compensated distance
                lead_distance = self.calculate_lead_distance(center)
                effective_distance = distance - lead_distance
                
                # Check if in fire zone (red zone)
                if distance <= self.fire_distance:
                    current_target_in_fire_zone = True
                    
                    if effective_distance < closest_distance:
                        closest_distance = effective_distance
                        closest_circle = circle
                        # Print status when target is close
                        status = f"🎯 TARGET IN RANGE: {int(distance)}px"
                        if self.lead_compensation_enabled and self.target_velocity:
                            status += f" (lead: {int(lead_distance)}px)"
                        print(status)
                elif distance <= warning_zone_distance:
                    # Target getting close
                    print(f"⚠️  Target approaching: {int(distance)}px")
        
        # Fire if: closest circle in fire zone AND conditions met
        if closest_circle is not None and self.should_fire():
            self.fire()
            self.zone_was_clear = False
        
        # Update zone state AFTER firing check
        if not current_target_in_fire_zone and self.target_in_zone:
            self.zone_was_clear = True
            print("✓ Fire zone cleared - ready for next target")
        
        self.target_in_zone = current_target_in_fire_zone
    
    def run(self):
        """Main loop - Headless mode"""
        print("=" * 60)
        print("PROXIMITY SHOOTER - HEADLESS MODE")
        print("=" * 60)
        print("\n🎯 System Configuration:")
        print(f"  • Shooting point: {self.shooting_point}")
        print(f"  • Fire distance: {self.fire_distance}px")
        print(f"  • Warning zone: {self.fire_distance * 2}px")
        print(f"  • Lead compensation: {'ENABLED' if self.lead_compensation_enabled else 'DISABLED'}")
        print(f"  • Camera device: {self.camera_device}")
        print(f"  • Motor GPIO pin: {self.motor.motor_pin}")
        print("\n⚙️  How it works:")
        print("  1. Detects green circles moving in the camera view")
        print("  2. Tracks their position and velocity")
        print("  3. Fires automatically when target enters the fire zone!")
        print("  4. Won't fire again until target exits the fire zone")
        print("\n🛑 Press Ctrl+C to stop")
        print("=" * 60)
        print("\n🚀 Starting detection loop...")
        
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
                
                # Process detection (headless - no GUI)
                self.process_targets(circles)
                
                # FPS tracking (update every 3 seconds to reduce overhead)
                fps_counter += 1
                if time.time() - fps_time > 3.0:
                    fps_display = fps_counter / 3.0
                    fps_counter = 0
                    fps_time = time.time()
                    # Print periodic status update
                    print(f"🔄 Status: FPS={fps_display:.1f}, Targets={len(circles)}, Shots={self.shot_count}")
                
                # Headless mode - no keyboard input needed
                # Press Ctrl+C to stop
                # No artificial timing constraint - run as fast as possible
        
        except KeyboardInterrupt:
            print("\nStopping...")
        
        finally:
            self.camera.release()
            self.motor.cleanup()
            print(f"\n✓ Final stats: {self.shot_count} shots fired")
            print("✓ System stopped.")


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

