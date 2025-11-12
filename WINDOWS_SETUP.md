# Windows Setup Guide

## Transfer Code to Windows

### Option 1: USB Drive (Easiest)
1. Copy `hackathon` folder to USB drive
2. Plug USB into Windows PC
3. Copy folder to `C:\hackathon`

### Option 2: Cloud Storage
1. Upload folder to Google Drive / OneDrive / Dropbox
2. Download on Windows
3. Extract to `C:\hackathon`

### Option 3: GitHub
```bash
# On Mac, upload to GitHub first, then on Windows:
cd C:\
git clone https://github.com/YOUR_USERNAME/nerf-turret.git
```

## Setup on Windows

### 1. Install Python (if not installed)
- Download from: https://www.python.org/downloads/
- **IMPORTANT**: Check "Add Python to PATH" during installation
- Install Python 3.8 or newer

### 2. Open Command Prompt or PowerShell
```bash
# Navigate to folder
cd C:\hackathon
```

### 3. Run the startup script
```bash
start_turret.bat
```

OR manually:
```bash
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate

# Install dependencies
pip install opencv-python numpy

# Run the program
python proximity_shooter.py
```

## Important Notes for Windows:

### ⚠️ Motor Control
- **RPi.GPIO doesn't work on Windows**
- Motor will run in **SIMULATION MODE**
- You'll see: `[SIMULATION] Motor would fire for 0.15s`
- Perfect for testing the detection and tracking!

### ✅ What Works on Windows:
- ✓ Camera detection
- ✓ Green circle tracking
- ✓ Velocity calculation
- ✓ Lead compensation
- ✓ Visual interface
- ✗ Actual motor firing (simulation only)

### 🎯 Use Windows For:
- Testing the code
- Calibrating green detection
- Adjusting fire distance
- Tuning lead compensation
- Making sure everything works before deploying to Raspberry Pi

## Testing on Windows:

1. **Run**: `python proximity_shooter.py`
2. **Click** to set shooting point
3. **Move green object** toward crosshair
4. **Watch** for "FIRE!" messages (simulation)
5. **Adjust** settings with +/- keys
6. **Once happy**, transfer to Raspberry Pi for real firing!

## Troubleshooting:

### Camera not found?
- Make sure webcam is plugged in
- Try changing camera index in code (line 79):
  ```python
  self.camera = cv2.VideoCapture(1)  # Try 0, 1, 2
  ```

### Python not recognized?
- Reinstall Python with "Add to PATH" checked
- Or manually add: `C:\Users\YourName\AppData\Local\Programs\Python\Python3XX`

### pip not working?
```bash
python -m pip install --upgrade pip
python -m pip install opencv-python numpy
```

## Files Needed:
- `proximity_shooter.py` - Main system
- `calibrate_green.py` - Calibration tool
- `start_turret.bat` - Windows startup script (NEW!)
- `requirements.txt` - Dependencies list

## After Testing on Windows:

When everything works, transfer the same files to:
- **Raspberry Pi** - For actual shooting
- Keep the Windows setup for development/testing

Enjoy! 🎯

