#!/usr/bin/env python3
# Minimal headless auto-fire: power on -> detect green -> move servo
# Requirements: sudo apt-get install -y python3-opencv python3-lgpio

import cv2, numpy as np, time
import lgpio

# ---- Camera (robust open) ----
def open_usb_cam(preferred=(0,1,2), size=(640,480), fps=15):
    fourcc_try = [cv2.VideoWriter_fourcc(*'MJPG'), cv2.VideoWriter_fourcc(*'YUYV'), 0]
    for idx in preferred:
        cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
        if not cap.isOpened(): 
            continue
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  size[0]); cap.set(cv2.CAP_PROP_FRAME_HEIGHT, size[1])
        cap.set(cv2.CAP_PROP_FPS, fps)
        for fcc in fourcc_try:
            if fcc: cap.set(cv2.CAP_PROP_FOURCC, fcc)
            # warmup
            for _ in range(8): cap.read(); time.sleep(0.01)
            ret, frame = cap.read()
            if ret and frame is not None:
                return cap
        cap.release()
    raise RuntimeError("Camera open failed")

# ---- Simple servo (lgpio PWM on BCM 18) ----
SERVO_PIN = 18          # change if needed
FREQ = 50               # Hz
MIN_US, MAX_US = 500, 2500

chip = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(chip, SERVO_PIN)

def _angle_to_dc(angle):
    angle = max(0, min(180, angle))
    period_us = 1_000_000 / FREQ
    pulse = MIN_US + (MAX_US - MIN_US) * (angle/180.0)
    return (pulse / period_us) * 100.0

def servo_set(angle, hold=0.1):
    lgpio.tx_pwm(chip, SERVO_PIN, FREQ, _angle_to_dc(angle))
    if hold: time.sleep(hold)

def servo_off():
    lgpio.tx_pwm(chip, SERVO_PIN, 0, 0)

# ---- Fire action (short pulse) ----
def fire_servo():
    # tweak these two angles for your mechanism
    servo_set(180, 0.12)   # press/trigger
    servo_set(90,  0.12)   # return to neutral

# ---- Main loop ----
def main():
    cap = open_usb_cam()
    last_fire = 0.0
    cooldown = 0.7             # seconds between shots
    min_area = 1200            # ignore tiny noise

    # pre-position
    servo_set(90, 0.2)

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.02)
            continue

        # HSV green mask (tune if lighting differs)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (35, 80, 80), (85, 255, 255))

        # largest blob area
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            c = max(cnts, key=cv2.contourArea)
            if cv2.contourArea(c) >= min_area and (time.time() - last_fire) > cooldown:
                fire_servo()
                last_fire = time.time()

        # small sleep to reduce CPU
        time.sleep(0.01)

if __name__ == "__main__":
    try:
        # optional boot delay if you run via systemd/crontab: time.sleep(5)
        main()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            servo_off()
            lgpio.gpiochip_close(chip)
        except Exception:
            pass
