#!/usr/bin/env python3
# proximity_shooter.py - minimal, headless, auto-fire on green target
# Requirements: python3-opencv, python3-lgpio
# Put this file at /home/pi/hackathon/proximity_shooter.py and run as root.

import cv2, time, sys
import lgpio
import signal

# ---- CONFIG ----
CAM_PREFERRED = (0, 1)
CAM_SIZE = (640, 480)
CAM_FPS = 15

SERVO_PIN = 17          # BCM pin used to trigger motor/servo (change if needed)
SERVO_FREQ = 50         # PWM freq for servo-like actuator
SERVO_MIN_US = 500
SERVO_MAX_US = 2500

COOLDOWN = 0.7          # seconds between shots
MIN_AREA = 1200         # minimum contour area to consider a valid target
FIRE_PULSE_ANGLE = 180  # servo angle used to "fire"
NEUTRAL_ANGLE = 90      # neutral/rest angle
FIRE_HOLD = 0.12        # seconds to hold fire angle
RETURN_HOLD = 0.12      # seconds to hold return

# ---- Camera open helper ----
def open_usb_cam(preferred=CAM_PREFERRED, size=CAM_SIZE, fps=CAM_FPS):
    fourcc_try = [
        cv2.VideoWriter_fourcc(*'MJPG'),
        cv2.VideoWriter_fourcc(*'YUYV'),
        0
    ]
    for idx in preferred:
        try:
            cap = cv2.VideoCapture(int(idx), cv2.CAP_V4L2)
        except Exception:
            continue
        if not cap.isOpened():
            continue
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  size[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, size[1])
        cap.set(cv2.CAP_PROP_FPS, fps)
        for fcc in fourcc_try:
            if fcc:
                cap.set(cv2.CAP_PROP_FOURCC, fcc)
            for _ in range(8):
                cap.read(); time.sleep(0.01)
            ret, frame = cap.read()
            if ret and frame is not None:
                print(f"[CAM] opened /dev/video{idx} {size[0]}x{size[1]} @{fps}")
                return cap
        cap.release()
    raise RuntimeError("Could not find a working camera. Check /dev/video* and v4l2 formats.")

# ---- Servo (lgpio) helper ----
def _angle_to_dc(angle, freq=SERVO_FREQ, min_us=SERVO_MIN_US, max_us=SERVO_MAX_US):
    angle = max(0, min(180, angle))
    period_us = 1_000_000 / freq
    pulse = min_us + (max_us - min_us) * (angle / 180.0)
    return (pulse / period_us) * 100.0

class SimpleActuator:
    def __init__(self, pin=SERVO_PIN, freq=SERVO_FREQ):
        self.pin = pin
        self.freq = freq
        try:
            self.chip = lgpio.gpiochip_open(0)
            lgpio.gpio_claim_output(self.chip, self.pin)
        except Exception as e:
            print("ERROR initializing lgpio:", e)
            raise
        # start neutral
        self.set_angle(NEUTRAL_ANGLE, hold=0.1)

    def set_angle(self, angle, hold=0.0):
        dc = _angle_to_dc(angle, self.freq)
        try:
            lgpio.tx_pwm(self.chip, self.pin, self.freq, dc)
        except Exception as e:
            print("ERROR tx_pwm:", e)
        if hold:
            time.sleep(hold)

    def off(self):
        try:
            lgpio.tx_pwm(self.chip, self.pin, 0, 0)
        except Exception:
            pass

    def cleanup(self):
        try:
            lgpio.tx_pwm(self.chip, self.pin, 0, 0)
            lgpio.gpiochip_close(self.chip)
        except Exception:
            pass

# ---- Fire action ----
def fire_action(actuator: SimpleActuator):
    actuator.set_angle(FIRE_PULSE_ANGLE, hold=FIRE_HOLD)
    actuator.set_angle(NEUTRAL_ANGLE, hold=RETURN_HOLD)

# ---- Detection loop ----
running = True
def sigint_handler(sig, frame):
    global running
    running = False

def main():
    global running
    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGTERM, sigint_handler)

    try:
        cap = open_usb_cam()
    except Exception as e:
        print("ERROR: Could not find a working camera!")
        print(" Available devices:", " ".join(sorted([p for p in ["/dev/video0","/dev/video1","/dev/video10","/dev/video11"]])))
        raise

    actuator = None
    try:
        actuator = SimpleActuator(pin=SERVO_PIN, freq=SERVO_FREQ)
    except Exception as e:
        print("Motor init failed:", e)
        cap.release()
        sys.exit(1)

    last_fire = 0.0

    while running:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.02)
            continue

        # HSV mask for green (tune if needed)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (35, 80, 80), (85, 255, 255))
        # optional noise reduction
        mask = cv2.medianBlur(mask, 5)

        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            c = max(cnts, key=lambda x: cv2.contourArea(x))
            area = cv2.contourArea(c)
            if area >= MIN_AREA and (time.time() - last_fire) > COOLDOWN:
                fire_action(actuator)
                last_fire = time.time()

        # tiny throttle to reduce CPU usage
        time.sleep(0.01)

    # cleanup
    try:
        cap.release()
    except:
        pass
    try:
        actuator.cleanup()
    except:
        pass
    print("✓ Motor controller cleaned up")
    print("✓ Final stats: done")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Fatal error:", e)
        try:
            # ensure actuator off if possible
            lgpio.tx_pwm(lgpio.gpiochip_open(0), SERVO_PIN, 0, 0)
        except Exception:
            pass
        sys.exit(1)
