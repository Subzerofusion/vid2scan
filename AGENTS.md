# AGENTS.md - Vid2Scan Agent Guidelines

This document provides guidelines for agentic coding tools working on this repository.

## Build / Lint / Test Commands

### Environment Setup
```bash
python -m venv venv
source venv/bin/activate  # or venv/bin/activate.fish for fish shell
pip install -r requirements.txt
```

### Running Tests
```bash
# Run all tests
pytest tests/

# Run a single test file
pytest tests/test_video_processor.py

# Run a specific test function
pytest tests/test_video_processor.py::test_load_video

# Run tests with verbose output
pytest tests/ -v
```

### Linting and Formatting
```bash
# Check code style with flake8
flake8 src/

# Format code with black
black src/

# Check formatting without making changes
black src/ --check
```

### Running the Application
```bash
python main.py
```

## Code Style Guidelines

### Python Version
- Python 3.13.2 (as specified in `.python-version`)

### Import Organization
1. Standard library imports first
2. Third-party imports (PySide6, cv2, numpy, PIL, etc.)
3. Local imports (from src.*)

### Type Hints
- Use type hints from `typing` module (Optional, Callable, Dict, Any, etc.)
- Return type annotations on all functions
- Parameter type hints on all functions
- Use `Optional[T]` for nullable return types

### Naming Conventions
- **Classes**: PascalCase (`VideoProcessor`, `MainWindow`, `ScanControls`)
- **Functions/Methods**: snake_case (`extract_horizontal_scan`, `set_frame`)
- **Variables**: snake_case (`video_path`, `line_position`, `frame_count`)
- **Constants**: UPPER_SNAKE_CASE (if needed, but rarely used)
- **Private methods**: prefix with underscore (`_extract_horizontal_lines`, `_check_cancel`)

### Logging
- Use module-level logger: `logger = logging.getLogger(__name__)`
- Set log level to ERROR: `logger.setLevel(logging.ERROR)`
- Log errors with context: `logger.error(f"Failed to open video: {path}")`
- Log warnings for non-critical issues: `logger.warning(f"Failed to read frame {frame_idx}")`

### Error Handling
- Use try-except blocks with logging
- Return `None` on errors for functions returning Optional[T]
- Raise exceptions for invalid input that should fail fast
- Log full error messages with context

### PySide6 / Qt Conventions
- Inherit from Qt widgets: `class MainWindow(QMainWindow):`
- Call `super().__init__()` in __init__
- Declare signals at class level: `params_changed = Signal(dict)`
- Use CamelCase for widget variables
- Connect signals with `.connect()`
- Use `blockSignals(True/False)` to avoid signal loops

### Thread Safety
- Use QThread + Worker pattern for long operations
- Worker inherits from QObject (not QThread)
- Use signals for inter-thread communication
- Never call GUI methods from worker threads

### Code Comments
- DO NOT add comments unless explicitly requested
- Code should be self-documenting through clear naming

### PEP 8 Compliance
- Follow PEP 8 guidelines for Python code style
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 88 characters (Black default)
- Two blank lines between top-level functions/classes
- One blank line between method definitions

### Video Processing Conventions
- Use OpenCV (cv2) for video reading and frame processing
- Use numpy arrays for image data
- Use PIL.Image for saving images to disk
- BGR format from OpenCV, convert to RGB when needed
- Use `cv2.INTER_LINEAR` for resizing by default

### Time Handling
- Use utilities in `src/utils/time_utils.py`
- Time strings format: `HH:MM:SS.mmm`
- Store times as float seconds internally

### File Structure
- `src/`: All application code
  - `video_processor.py`: Core video/slitscan logic
  - `gui/`: All UI components
  - `utils/`: Utility functions (time_utils.py, geometry.py)
- `tests/`: Test files
- `main.py`: Application entry point

### Project-Specific Patterns
- Slitscan extraction: Use `VideoProcessor.extract_horizontal_scan()` or `.extract_vertical_scan()`
- Preview generation: Use `VideoProcessor.preview_scan()` with quality presets
- Cancelation: Use `_cancel_requested` flag pattern, check with `is_canceled()`
- Debouncing: Use QTimer with `setSingleShot(True)` for UI updates
- Line/column extraction: Use utility functions in `src/utils/geometry.py`

### Testing
- Write tests in `tests/` directory
- Use pytest as test framework
- Test file names: `test_*.py`
- Test function names: `test_*()`
- Include test data in `data/` directory (gitignored locally)

### Dependencies
- PySide6 >= 6.6.0 (GUI framework)
- opencv-python >= 4.8.0 (video processing)
- numpy >= 1.24.0 (numerical operations)
- Pillow >= 10.0.0 (image saving)

### Common Patterns
- Private methods prefix with underscore
- Use context managers for resource cleanup
- Check for None before optional operations
- Validate user input early with clear error messages
