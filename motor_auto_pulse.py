#!/usr/bin/env python3
"""Simple motor pulser using PWM: fire every 3 seconds."""

import time

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
    print("✓ RPi.GPIO loaded - Motor control ENABLED")
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠ RPi.GPIO not available - Motor control DISABLED (simulation mode)")


class MotorPulser:
    def __init__(self, motor_pin=17, fire_duration=0.15, interval=3.0,
                 pwm_frequency=1000, pwm_duty_cycle=100):
        self.motor_pin = motor_pin
        self.fire_duration = fire_duration
        self.interval = interval
        self.pwm_frequency = pwm_frequency
        self.pwm_duty_cycle = max(0, min(100, pwm_duty_cycle))
        self.enabled = GPIO_AVAILABLE
        self.pwm = None

        if self.enabled:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.motor_pin, GPIO.OUT)
            self.pwm = GPIO.PWM(self.motor_pin, self.pwm_frequency)
            print(f"✓ Motor initialized on GPIO {self.motor_pin} (PWM {self.pwm_frequency}Hz)")
        else:
            print("⚠ Running in simulation mode")

    def fire(self):
        if self.enabled:
            self.pwm.start(self.pwm_duty_cycle)
            time.sleep(self.fire_duration)
            self.pwm.stop()
        print(f"🔥 Motor pulsed for {self.fire_duration}s at {self.pwm_duty_cycle}% duty")

    def cleanup(self):
        if self.enabled:
            if self.pwm is not None:
                self.pwm.stop()
            GPIO.cleanup()
            print("✓ GPIO cleaned up")

    def run(self):
        print(f"Starting automatic PWM firing every {self.interval}s. Press Ctrl+C to stop.")
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
    pulser = MotorPulser(motor_pin=17, fire_duration=0.15, interval=3.0,
                         pwm_frequency=1000, pwm_duty_cycle=100)
    pulser.run()


if __name__ == "__main__":
    main()
