#!/usr/bin/env python3
"""Simple motor pulser: fire every 3 seconds."""

import time

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
    print("✓ RPi.GPIO loaded - Motor control ENABLED")
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠ RPi.GPIO not available - Motor control DISABLED (simulation mode)")


class MotorPulser:
    def __init__(self, motor_pin=17, fire_duration=0.15, interval=3.0):
        self.motor_pin = motor_pin
        self.fire_duration = fire_duration
        self.interval = interval
        self.enabled = GPIO_AVAILABLE

        if self.enabled:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.motor_pin, GPIO.OUT)
            GPIO.output(self.motor_pin, GPIO.LOW)
            print(f"✓ Motor initialized on GPIO {self.motor_pin}")
        else:
            print("⚠ Running in simulation mode")

    def fire(self):
        if self.enabled:
            GPIO.output(self.motor_pin, GPIO.HIGH)
            time.sleep(self.fire_duration)
            GPIO.output(self.motor_pin, GPIO.LOW)
        print(f"🔥 Motor pulsed for {self.fire_duration}s")

    def cleanup(self):
        if self.enabled:
            GPIO.output(self.motor_pin, GPIO.LOW)
            GPIO.cleanup()
            print("✓ GPIO cleaned up")

    def run(self):
        print(f"Starting automatic firing every {self.interval}s. Press Ctrl+C to stop.")
        next_fire = time.time()
        try:
            while True:
                now = time.time()
                if now >= next_fire:
                    self.fire()
                    next_fire = now + self.interval
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            self.cleanup()


def main():
    pulser = MotorPulser(motor_pin=17, fire_duration=0.15, interval=3.0)
    pulser.run()


if __name__ == "__main__":
    main()
