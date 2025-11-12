# Raspberry Pi Setup Guide for Nerf Turret

## Hardware Requirements

### Components:
1. **Raspberry Pi** (3B+ or 4 recommended)
2. **Logitech USB Camera** (or Pi Camera)
3. **Torque Motor** (to fire the nerf gun)
4. **Motor Driver** (L293D, L298N, or transistor/MOSFET)
5. **Power Supply** (5V for Pi, appropriate voltage for motor)
6. **Stationary Nerf Gun**
7. **Green circle targets** (for detection)

### GPIO Connection:

```
Raspberry Pi (BCM Numbering)
┌─────────────────────────────┐
│                             │
│  GPIO 17 ──────────┐        │
│                    │        │
│  GND ──────────────┼────┐   │
│                    │    │   │
└────────────────────┼────┼───┘
                     │    │
                     ↓    ↓
              ┌──────────────┐
              │ Motor Driver │
              └──────┬───────┘
                     │
              ┌──────┴───────┐
              │ Torque Motor │
              └──────────────┘
```

**Default Pin:**
- **GPIO 17** (Physical Pin 11) - Motor trigger signal
- **GND** - Common ground with motor circuit

**To change the pin**, edit line 421 in `proximity_shooter.py`:
```python
shooter = ProximityShooter(motor_pin=18, fire_duration=0.2)  # Use GPIO 18 instead
```

## Software Setup

### 1. Install Raspberry Pi OS
Use Raspberry Pi Imager to install Raspberry Pi OS (with desktop)

### 2. Update System
```bash
sudo apt update
sudo apt upgrade -y
```

### 3. Install Dependencies
```bash
# Install Python packages
pip3 install opencv-python numpy RPi.GPIO

# Or use the requirements file
pip3 install -r requirements.txt
```

### 4. Enable Camera
If using Pi Camera:
```bash
sudo raspi-config
# Navigate to: Interface Options → Camera → Enable
```

### 5. Test Camera
```bash
python3 test_camera.py
```

## Running the System

### Step 1: Calibrate Green Detection (Optional)
```bash
python3 calibrate_green.py
```
Adjust sliders until your green targets are detected properly.

### Step 2: Run the Shooter
```bash
python3 proximity_shooter.py
```

### Step 3: Setup
1. Window opens with camera feed
2. **Click** on screen to set shooting point (crosshair appears)
3. Move green circle target toward crosshair
4. System fires automatically when target gets within 30 pixels!

## Configuration

### Adjust Fire Distance
Press **+** or **-** while running to adjust sensitivity:
- **+** : Increase fire distance (fires from farther away)
- **-** : Decrease fire distance (must be closer to fire)

### Change Motor Settings

Edit `proximity_shooter.py` line 421:
```python
shooter = ProximityShooter(
    motor_pin=17,        # GPIO pin number (BCM mode)
    fire_duration=0.15   # How long to activate motor (seconds)
)
```

**Parameters:**
- `motor_pin`: Which GPIO pin controls the motor (default: 17)
- `fire_duration`: How long to pulse the motor (0.1-0.3s typical)

### Change Cooldown Time

Edit line 98:
```python
self.fire_cooldown = 1.0  # Minimum time between shots (seconds)
```

## Motor Driver Circuit

### Option 1: Using Transistor (Simple)
```
GPIO 17 ──── 1kΩ ──── Base (NPN Transistor)
                      Collector ── Motor (+)
                      Emitter ──── GND
Motor (-) ──────────── Power Supply (+)
```

### Option 2: Using L298N Motor Driver
```
GPIO 17 ────→ IN1 on L298N
             IN2 ──→ GND
             Motor connected to OUT1 and OUT2
             12V power supply to motor driver
```

### Option 3: Using Relay Module
```
GPIO 17 ────→ Signal pin on Relay
             Motor connected through relay contacts
             Separate power supply for motor
```

## Troubleshooting

### Camera not detected?
```bash
# Check connected cameras
ls /dev/video*

# Try different camera index in code (line 79)
self.camera = cv2.VideoCapture(1)  # Try 0, 1, 2...
```

### GPIO permissions error?
```bash
# Add user to GPIO group
sudo usermod -a -G gpio $USER
# Logout and login again
```

### Motor not firing?
1. Check GPIO pin connection
2. Verify motor driver wiring
3. Test motor manually: `python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.setup(17, GPIO.OUT); GPIO.output(17, GPIO.HIGH)"`
4. Check power supply to motor
5. Increase `fire_duration` if motor is too slow

### Detection not working?
1. Run `calibrate_green.py` to adjust HSV values
2. Ensure good lighting
3. Make green circles bright and vivid
4. Adjust `fire_distance` with +/- keys

### System too slow?
1. Lower camera resolution (line 80-81)
2. Close other programs
3. Overclock Raspberry Pi (careful!)
4. Use Raspberry Pi 4 for better performance

## Auto-Start on Boot (Optional)

Create a systemd service:
```bash
sudo nano /etc/systemd/system/nerf-turret.service
```

Add:
```ini
[Unit]
Description=Nerf Turret Auto Shooter
After=multi-user.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/hackathon
ExecStart=/usr/bin/python3 /home/pi/hackathon/proximity_shooter.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable nerf-turret.service
sudo systemctl start nerf-turret.service
```

## Safety Tips

⚠️ **IMPORTANT SAFETY CONSIDERATIONS:**

1. **Test without ammunition first** - Verify detection and firing logic
2. **Use appropriate eye protection** when testing
3. **Secure the nerf gun** so it can't move or fall
4. **Add emergency stop button** (optional GPIO button to kill system)
5. **Test motor current** - Ensure it doesn't overload GPIO/driver
6. **Use external power** for motor (not from Pi's 5V pins)
7. **Add flyback diode** if using DC motor directly
8. **Supervise operation** - Don't leave running unattended

## Performance Tips

- **Resolution**: 640x480 is good balance of speed/quality
- **FPS**: 30 FPS works well, higher may not help
- **Fire Distance**: 30-50 pixels typical for good accuracy
- **Cooldown**: 1 second prevents multiple fires per target
- **Fire Duration**: 0.15s usually enough, adjust for your motor

## Testing Checklist

- [ ] Camera working and detecting green circles
- [ ] Crosshair appears when clicking
- [ ] Distance calculation showing correct values
- [ ] Motor triggers when target gets close
- [ ] Cooldown working (no rapid-fire)
- [ ] System runs stable for 5+ minutes
- [ ] Nerf gun fires successfully
- [ ] Targets are hit accurately

## Support

If you have issues:
1. Check all connections
2. Verify GPIO pin numbers (BCM vs BOARD mode)
3. Test components individually
4. Check power supply voltage
5. Review terminal output for error messages

Good luck with your automated nerf turret! 🎯🔫

