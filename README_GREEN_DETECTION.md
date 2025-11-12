# Green Circle Detection for Nerf Turret

## Quick Start Guide

### Step 1: Install Dependencies

```bash
pip install opencv-python numpy
```

### Step 2: Calibrate Green Color Detection

Run the calibration tool first to find the perfect HSV values for your green circles:

```bash
python3 calibrate_green.py
```

**What to do:**
1. Place your green circle target in the camera view
2. Adjust the sliders until ONLY the green circle appears white in the "Mask" view
3. Press 'q' when satisfied - it will print the calibrated values
4. Copy those values into `green_circle_detector.py` (lines 21-22)

**Tips:**
- Good lighting is important!
- H_min and H_max control what color is detected (35-85 is green)
- S_min controls how vibrant the green needs to be
- V_min controls minimum brightness
- Morph slider helps clean up noise

### Step 3: Run the Detector

```bash
python3 green_circle_detector.py
```

**Controls:**
- `q` - Quit
- `m` - Toggle mask view (shows what the camera sees as "green")
- `+` - Increase minimum circle radius
- `-` - Decrease minimum circle radius

**What you'll see:**
- Main window: Camera feed with detected circles highlighted in green
- Green circles drawn around detected targets
- Red dot at the center
- Info showing position, radius, and circularity
- FPS counter

### Step 4: Test and Adjust

Move your green circle target around and verify:
- ✅ It detects the circle consistently
- ✅ No false positives (detecting other green objects)
- ✅ Works at different distances
- ✅ Works at different angles

If detection is poor:
1. Re-run calibration in your actual environment
2. Adjust `min_circle_radius` and `max_circle_radius` in the code
3. Change `min_area` if needed
4. Adjust lighting if possible

## Next Steps

Once detection is working well, we'll add:
1. ✅ Green circle detection (DONE)
2. ⏳ Velocity calculation (track movement over 1 second)
3. ⏳ Predict when target reaches shooting point
4. ⏳ Trigger motor at the right time

## File Structure

```
hackathon/
├── green_circle_detector.py    # Main detection script
├── calibrate_green.py          # Calibration tool
└── README_GREEN_DETECTION.md   # This file
```

## Troubleshooting

**Camera not found?**
- Check USB connection
- Try `ls /dev/video*` to see available cameras
- Change `cv2.VideoCapture(0)` to `cv2.VideoCapture(1)` or `2`

**Detects too many things?**
- Make HSV range more restrictive in calibration
- Increase `min_area` in the code
- Increase circularity threshold (line 67)

**Misses the circles?**
- Make HSV range wider in calibration
- Decrease `min_area` in the code
- Check lighting conditions
- Decrease circularity threshold

**Slow performance?**
- Lower camera resolution (currently 640x480)
- Close other programs
- Make sure you're running Python 3

