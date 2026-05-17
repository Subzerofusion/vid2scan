#!/bin/bash
# Build vid2scan Windows executable
# NOTE: Run this on Windows, not WSL/Linux

# Activate venv and build
source venv/bin/activate
pyinstaller vid2scan.spec --clean

# Output: dist/vid2scan.exe
