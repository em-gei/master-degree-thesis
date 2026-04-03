#!/bin/bash

# --- Driver Monitoring System Setup Script for Raspberry Pi ---
# This script installs system dependencies, configures hardware interfaces,
# and sets up the Python environment.

echo "-------------------------------------------------------"
echo "Starting DMS Setup for Raspberry Pi..."
echo "-------------------------------------------------------"

# 1. Update System
echo "[1/6] Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install System-level Dependencies
# Necessary for OpenCV, PyAudio, MediaPipe and Python development
echo "[2/6] Installing system dependencies (C++/Audio/Imaging)..."
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    libportaudio2 \
    portaudio19-dev \
    libatlas-base-dev \
    libopencv-dev \
    i2c-tools \
    libgpiod-dev \
    libcap-dev

# 3. Enable Hardware Interfaces (Non-interactive)
echo "[3/6] Enabling I2C and Camera interfaces..."
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_camera 0

# 4. Set up Python Virtual Environment
echo "[4/6] Creating Python virtual environment (venv)..."
python3 -m venv venv
source venv/bin/activate

# 5. Install Python Packages
echo "[5/6] Installing Python libraries from requirements.txt..."
# We upgrade pip first to ensure compatibility with latest wheels
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 6. Specific PiCamera2 setup (For newer OS Bookworm/Bullseye)
# Picamera2 is often best managed via apt on Pi
echo "[6/6] Finalizing camera and permission settings..."
sudo apt-get install -y python3-picamera2

# Add user to 'video' and 'input' groups just in case
sudo usermod -a -G video,input,i2c $USER

echo "-------------------------------------------------------"
echo "SETUP COMPLETE!"
echo "-------------------------------------------------------"
echo "To start the system, run:"
echo "source venv/bin/activate"
echo "python src/dms_main.py"
echo "-------------------------------------------------------"
echo "NOTE: A reboot is recommended to finalize interface activation."