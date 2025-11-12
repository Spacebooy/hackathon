#!/bin/bash
# Nerf Turret Startup Script
# Run this on Raspberry Pi: bash start_turret.sh

echo "========================================"
echo "  NERF TURRET STARTING..."
echo "========================================"
echo ""

# Navigate to directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "Checking dependencies..."
pip3 install -q -r requirements.txt

echo ""
echo "Starting proximity shooter..."
echo "Controls:"
echo "  CLICK - Set shooting point"
echo "  l     - Toggle lead compensation"
echo "  +/-   - Adjust fire distance"
echo "  q     - Quit"
echo ""

# Run the shooter
python3 proximity_shooter.py

