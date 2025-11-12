# Raspberry Pi Quick Start Guide

## Transfer Files to Pi

### Option 1: USB Drive
1. Copy `hackathon` folder to USB drive
2. Plug USB into Pi
3. Copy folder to `/home/pi/`

### Option 2: Network Transfer (If Pi is on WiFi)
```bash
# On Mac (replace IP_ADDRESS with your Pi's IP):
scp -r /Users/baobui/hackathon pi@192.168.1.XXX:/home/pi/
```

## Setup on Raspberry Pi

### 1. Open Terminal on Pi and navigate to folder:
```bash
cd /home/pi/hackathon
```

### 2. Make startup script executable:
```bash
chmod +x start_turret.sh
```

### 3. Run the startup script:
```bash
./start_turret.sh
```

That's it! The script will:
- Create virtual environment
- Install all dependencies
- Start the turret system

## Hardware Setup

### Connect Motor to GPIO:
```
GPIO 17 (Pin 11) → Motor Driver → Motor
GND (Pin 9)      → Ground
```

### Pin Layout (Physical Pin Numbers):
```
 3.3V [ 1] [ 2] 5V
      [ 3] [ 4] 5V
      [ 5] [ 6] GND ←──────┐
      [ 7] [ 8]            │
  GND [ 9] [10]            │ Connect to
      [11] [12] ← GPIO 17 ─┤ motor driver
      [13] [14]            │
      ...                  │
```

## First Time Use:

1. **Connect camera** (USB Logitech camera)
2. **Connect motor** to GPIO 17
3. **Run**: `./start_turret.sh`
4. **Click** to set shooting point
5. **Move green target** toward crosshair
6. **System fires** automatically!

## Calibration:

If detection is poor:
```bash
python3 calibrate_green.py
# Adjust sliders until only green circles are white
# Press 'q' and copy values to proximity_shooter.py
```

## Troubleshooting:

**Camera not working?**
```bash
ls /dev/video*
# If you see video0, video1, etc., camera is connected
```

**Permission denied?**
```bash
sudo usermod -a -G gpio,video $USER
# Then logout and login again
```

**Motor not firing?**
- Check GPIO connection
- Verify motor driver wiring
- Test: `python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.setup(17, GPIO.OUT); GPIO.output(17, 1)"`

## Auto-start on Boot (Optional):

```bash
# Edit crontab
crontab -e

# Add this line:
@reboot sleep 10 && /home/pi/hackathon/start_turret.sh
```

## Files:
- `proximity_shooter.py` - Main system
- `calibrate_green.py` - Calibration tool
- `start_turret.sh` - Easy startup script
- `requirements.txt` - Dependencies

## Support:
Check `RASPBERRY_PI_SETUP.md` for detailed hardware info!

