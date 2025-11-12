#!/bin/bash
echo "========================================="
echo "RASPBERRY PI DEVICE CHECK"
echo "========================================="
echo ""

echo "📹 VIDEO DEVICES:"
ls -l /dev/video* 2>/dev/null || echo "  No video devices found"
echo ""

echo "🔌 USB DEVICES:"
lsusb 2>/dev/null || echo "  lsusb not available"
echo ""

echo "💾 STORAGE DEVICES:"
lsblk 2>/dev/null || echo "  lsblk not available"
echo ""

echo "🌐 NETWORK INTERFACES:"
ip a 2>/dev/null | grep -E "^[0-9]+:" || ifconfig 2>/dev/null | grep -E "^[a-z]" || echo "  No network info"
echo ""

echo "📊 CAMERA DETAILS:"
v4l2-ctl --list-devices 2>/dev/null || echo "  v4l2-ctl not installed (sudo apt install v4l-utils)"
echo ""

echo "🔧 GPIO STATUS:"
gpio readall 2>/dev/null || echo "  wiringpi not installed (sudo apt install wiringpi)"
echo ""

echo "========================================="
