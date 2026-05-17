# Vid2Scan - Line Scan / Slit Scan Photo Generator

A cross-platform Python GUI application for creating line scan and slit scan photographs from videos.

> **WARNING**: This codebase is entirely "vibe coded" — written by feel, trial-and-error, and guesswork rather than proper software engineering practices. The code works, but it's fragile, untested, and will likely break in unexpected ways. Not a good thing. Use at your own risk.

## Features

- **Multi-pixel slit support**: Extract single-pixel lines or multi-pixel slits (1-100px)
- **Bidirectional scanning**: Horizontal and vertical scan directions
- **Temporal stretch**: Repeat each extracted line 1-100 times
- **Spatial stretch**: Scale line width 1-10x
- **Time range control**: Extract frames from specific time intervals
- **Frame stepping**: Extract every Nth frame for different temporal resolutions
- **Output scaling**: Scale final output (25%, 50%, 75%, 100%, or custom)
- **Preview quality options**: Low (fast), Medium (balanced), or High (detailed)
- **Real-time preview**: See results before generating full resolution
- **Cross-platform**: Works on Windows and Linux
- **Multiple output formats**: JPEG (default), PNG, TIFF

## Requirements

- Python 3.13.2
- PySide6 >= 6.6.0
- opencv-python >= 4.8.0
- numpy >= 1.24.0
- Pillow >= 10.0.0

## Installation

### 1. Install Python 3.13.2

Using pyenv:
```bash
pyenv install 3.13.2
pyenv local 3.13.2
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate.fish  # For fish shell
# or
source venv/bin/activate       # For bash/zsh
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

1. **Launch the application**:
   ```bash
   python main.py
   ```

2. **Open a video**: File → Open Video (or Ctrl+O)

3. **Adjust the extraction line**:
   - Click and drag the red line on the video preview
   - The line indicates which pixels will be extracted

4. **Configure extraction settings**:
   - **Direction**: Choose horizontal (lines stacked vertically) or vertical (columns stacked horizontally)
   - **Line Position**: Position of the extraction line
   - **Line Width**: Width of the slit in pixels (1-100)
   - **Combine Mode**: Average multi-pixel slits or keep as stripes
   - **Stretch Factors**:
     - Temporal: Repeat each extracted line N times
     - Spatial: Scale line width by N
   - **Time Range**: Start and end timestamps
   - **Frame Step**: Extract every Nth frame
   - **Output Scale**: Scale the final output
   - **Preview Quality**: Low/Medium/High

5. **Preview**: Click "Update Preview" to see a low-resolution preview

6. **Generate**: Click "Generate Full Resolution" to create the full slitscan image

7. **Save**: File → Save Image (or Ctrl+S) to save the result

## Understanding Line Scan / Slit Scan Photography

### What is a Slitscan?

A slitscan (or line scan) photograph is created by extracting a thin slice (line) from each video frame and stacking them together. This transforms temporal changes into spatial dimensions, revealing patterns that are invisible to the naked eye.

### Horizontal Scan

- Extracts a horizontal line from each frame
- Stacks lines vertically
- Time flows from top to bottom in the output
- Use for horizontal motion analysis

### Vertical Scan

- Extracts a vertical column from each frame
- Stacks columns horizontally
- Time flows from left to right in the output
- Use for vertical motion analysis

### Stretch Factors

**Temporal Stretch**: Repeats each extracted line N times. Creates a slower, more stretched-out progression.

**Spatial Stretch**: Scales the extracted line width. Increases resolution without affecting temporal density.

## Project Structure

```
vid2scan/
├── src/
│   ├── __init__.py
│   ├── video_processor.py      # Core slitscan logic
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py      # Main application window
│   │   ├── video_preview.py    # Video player with line selector
│   │   ├── scan_controls.py    # Extraction settings panel
│   │   └── slitscan_preview.py # Slitscan display with zoom
│   └── utils/
│       ├── __init__.py
│       ├── time_utils.py       # Time parsing/validation
│       └── geometry.py         # Line/column calculations
├── tests/
│   ├── __init__.py
│   ├── test_scan_processor.py
│   ├── test_geometry.py
│   └── test_integration.py
├── requirements.txt
├── README.md
├── setup.py
└── main.py
```

## Keyboard Shortcuts

- `Ctrl+O`: Open Video
- `Ctrl+S`: Save Image
- `Ctrl+Q`: Exit

## Tips for Best Results

1. **Start with a preview**: Use low quality preview to quickly find the right extraction line
2. **Use time range**: Limit extraction to interesting portions of the video
3. **Adjust frame step**: Increase for faster processing of long videos
4. **Use temporal stretch** for artistic effects (stretching time)
5. **Use spatial stretch** for higher resolution output
6. **Output scaling**: For very long videos, scale down to manage file size

## Troubleshooting

**Application won't start**:
- Ensure Python 3.13.2 is installed and active
- Verify all dependencies are installed: `pip list`

**Video won't load**:
- Check video format (MP4, AVI, MOV, MKV, WMV supported)
- Ensure file is not corrupted
- Try converting video with FFmpeg if needed

**Slitscan generation is slow**:
- Increase frame step (extract every Nth frame)
- Use lower preview quality
- Reduce time range

**Output image is too large**:
- Reduce output scale
- Decrease temporal stretch
- Increase frame step

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

The project follows PEP 8 guidelines. Run linting:

```bash
flake8 src/
black src/
```

## License

This project is provided as-is for educational and creative purposes.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Acknowledgments

Built with:
- [PySide6](https://www.qt.io/qt-for-python/) - Cross-platform GUI framework
- [OpenCV](https://opencv.org/) - Computer vision and video processing
- [NumPy](https://numpy.org/) - Numerical computing
- [Pillow](https://python-pillow.org/) - Image processing
