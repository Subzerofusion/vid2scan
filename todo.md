# Line Scan / Slit Scan Photo Generator - Implementation Plan

## Project Overview
Cross-platform Python GUI application using PySide6 and OpenCV to create line scan/slitscan photographs from videos.

## Tech Stack
- **Python**: 3.13.2 (via pyenv)
- **GUI Framework**: PySide6 (cross-platform: Windows/Linux)
- **Video Processing**: OpenCV (cv2)
- **Array Processing**: NumPy
- **Image I/O**: Pillow (PIL)

## Key Features
- Multi-pixel slit support (1-100px)
- Horizontal + vertical scan directions
- Temporal stretch (repeat lines 1-100x)
- Spatial stretch (scale line width 1-10x)
- Time range control (start/end timestamps)
- Frame stepping (every Nth frame)
- Output scaling (100%, 75%, 50%, 25%, custom)
- Preview quality options (low/medium/high)
- Default output: JPEG

---

## Phase 1: Environment Setup

### Tasks
- [ ] Install Python 3.13.2 via pyenv
  - Command: `pyenv install 3.13.2`
  - Set local: `pyenv local 3.13.2`
- [ ] Create virtual environment
  - Command: `python -m venv venv`
  - Activate in fish: `source venv/bin/activate.fish`
- [ ] Create requirements.txt with dependencies:
  ```txt
  PySide6>=6.6.0
  opencv-python>=4.8.0
  numpy>=1.24.0
  Pillow>=10.0.0
  ```
- [ ] Install dependencies
  - Command: `pip install -r requirements.txt`
- [ ] Verify installations
  - Test PySide6: `python -c "import PySide6"`
  - Test OpenCV: `python -c "import cv2"`

---

## Phase 2: Project Structure

### Create Directory Structure
```
vid2scan/
├── src/
│   ├── __init__.py
│   ├── video_processor.py
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   ├── video_preview.py
│   │   ├── scan_controls.py
│   │   ├── slitscan_preview.py
│   │   └── styles.qss
│   └── utils/
│       ├── __init__.py
│       ├── time_utils.py
│       └── geometry.py
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

### Tasks
- [ ] Create all directories
- [ ] Create all `__init__.py` files
- [ ] Create empty stub files for each module

---

## Phase 3: Core Logic - Video Processor

### File: `src/video_processor.py`

### Class: VideoProcessor

#### Methods to Implement

**__init__**
- Initialize video properties (path, cap, fps, frames, width, height, duration)

**load_video(path: str) -> bool**
- Open video with cv2.VideoCapture
- Extract properties: fps, width, height, frame_count, duration
- Return True if successful, False otherwise

**close()**
- Release cv2.VideoCapture

**get_frame_at_time(time_sec: float) -> np.ndarray**
- Convert time to frame number: frame = time_sec * fps
- Seek to frame with cap.set(cv2.CAP_PROP_POS_FRAMES)
- Return frame array

**extract_horizontal_scan(...) -> np.ndarray**
Parameters:
- line_y: int - Y position of extraction line
- line_width: int - 1-N pixels wide
- combine_mode: str - 'average' or 'stack'
- start_time: float - Start timestamp (seconds)
- end_time: float - End timestamp (seconds)
- frame_step: int - Extract every Nth frame
- temporal_stretch: int - Duplicate each line N times
- spatial_stretch: int - Scale line width by N
- output_scale: float - Scale final output (1.0 = 100%)
- progress_callback: Optional[Callable] - Progress updates

Algorithm:
1. Calculate frame range from time range
2. Iterate frames with frame_step
3. Extract horizontal strip: frame[y:y+line_width, :]
4. Combine if line_width > 1:
   - Average: np.mean(strips, axis=0)
   - Stack: Keep all strips (striped effect)
5. Apply spatial stretch: cv2.resize(line, (w * spatial_stretch, 1))
6. Apply temporal stretch: Repeat line N times
7. Stack lines vertically with np.vstack
8. Scale output: cv2.resize(result, scale factor)
9. Call progress_callback periodically

**extract_vertical_scan(...) -> np.ndarray**
Parameters: Same as horizontal scan, but line_x instead of line_y

Algorithm:
1. Same frame iteration
2. Extract vertical strip: frame[:, x:x+line_width]
3. Combine, stretch, stack horizontally with np.hstack
4. Scale output

**preview_scan(...) -> np.ndarray**
Parameters: Same as extract + quality: str ('low', 'medium', 'high')

Quality Presets:
- Low: frame_step=10, scale=0.25
- Medium: frame_step=5, scale=0.50
- High: frame_step=2, scale=0.75

Algorithm:
- Apply quality presets to reduce processing
- Same extraction logic as full scan

### Tasks
- [ ] Implement VideoProcessor.__init__
- [ ] Implement VideoProcessor.load_video
- [ ] Implement VideoProcessor.close
- [ ] Implement VideoProcessor.get_frame_at_time
- [ ] Implement VideoProcessor.extract_horizontal_scan
- [ ] Implement VideoProcessor.extract_vertical_scan
- [ ] Implement VideoProcessor.preview_scan
- [ ] Add unit tests in tests/test_scan_processor.py

---

## Phase 4: Utils

### File: `src/utils/time_utils.py`

#### Functions to Implement

**parse_time_str(time_str: str) -> float**
- Parse 'HH:MM:SS.mmm' to seconds
- Example: '00:01:30.500' → 90.5

**seconds_to_time_str(seconds: float) -> str**
- Convert seconds to 'HH:MM:SS.mmm'

**clamp_time(time_sec: float, max_duration: float) -> float**
- Ensure time is within [0, max_duration]

### Tasks
- [ ] Implement parse_time_str
- [ ] Implement seconds_to_time_str
- [ ] Implement clamp_time
- [ ] Add unit tests

---

### File: `src/utils/geometry.py`

#### Functions to Implement

**extract_horizontal_line(frame: np.ndarray, y: int, width: int) -> np.ndarray**
- Return frame[y:y+width, :]

**extract_vertical_line(frame: np.ndarray, x: int, width: int) -> np.ndarray**
- Return frame[:, x:x+width]

**combine_lines_average(lines: np.ndarray) -> np.ndarray**
- Average multiple lines: np.mean(lines, axis=0)

**apply_spatial_stretch(line: np.ndarray, factor: int) -> np.ndarray**
- Scale line width: cv2.resize(line, (line.shape[1] * factor, 1))

**apply_temporal_stretch(lines: np.ndarray, factor: int) -> np.ndarray**
- Repeat each line factor times using np.repeat

**scale_output(image: np.ndarray, scale: float) -> np.ndarray**
- Scale final output: cv2.resize(image, scale factor)

### Tasks
- [ ] Implement all geometry functions
- [ ] Add unit tests in tests/test_geometry.py

---

## Phase 5: GUI - Main Window

### File: `src/gui/main_window.py`

### Class: MainWindow

#### Layout
- QMainWindow with menu bar, central widget, status bar
- Central widget: QSplitter (horizontal)
  - Left: VideoPreview (60% width)
  - Right: QWidget with QVBoxLayout
    - SlitscanPreview (expandable)
    - ScanControls (fixed height)

#### Components to Implement

**__init__**
- Initialize VideoProcessor
- Create UI components
- Set up layout
- Connect signals/slots

**create_menu_bar**
- File menu: Open Video, Save Image, Exit
- Edit menu: (placeholder for future)
- Help menu: About

**open_video**
- QFileDialog.getOpenFileName
- Call video_processor.load_video
- Update UI with video properties
- Enable controls
- Show first frame

**save_image**
- Check if slitscan generated
- QFileDialog.getSaveFileName (default: JPEG)
- Save with PIL.Image.save

**update_status_bar**
- Show video info, progress, messages

#### Signals/Slots
- video_preview.line_position_changed → scan_controls.update_line_position
- scan_controls.params_changed → update_preview
- scan_controls.generate_clicked → generate_full_scan
- scan_controls.save_clicked → save_image

### Tasks
- [ ] Implement MainWindow.__init__
- [ ] Implement create_menu_bar
- [ ] Implement open_video
- [ ] Implement save_image
- [ ] Implement update_status_bar
- [ ] Connect all signals/slots
- [ ] Create basic styles.qss (optional)

---

## Phase 6: GUI - Video Preview

### File: `src/gui/video_preview.py`

### Class: VideoPreview

#### Features
- Display video frame (QLabel with QPixmap)
- Overlay line indicator (horizontal or vertical)
- Mouse interaction: drag line to move
- Playback controls: play/pause, seek, step

#### Components

**__init__**
- QLabel for frame display
- Overlay widget for line indicator
- Playback buttons and slider
- Timer for playback

**set_frame(frame: np.ndarray)**
- Convert frame to QPixmap
- Update QLabel

**set_line_position(pos: int)**
- Update line position
- Trigger repaint

**set_direction(direction: str)**
- Update line orientation (horizontal/vertical)
- Repaint

**paintEvent**
- Draw video frame
- Draw line indicator:
  - Horizontal: red line at y position
  - Vertical: red line at x position
  - Line width visualization for multi-pixel

**mousePressEvent, mouseMoveEvent, mouseReleaseEvent**
- Handle line dragging
- Calculate new position from mouse coordinates
- Clamp to video dimensions
- Emit line_position_changed signal on release

**play, pause, step_forward, step_backward**
- Control playback
- Update frame display

**seek_to_time(seconds: float)**
- Seek to timestamp
- Update display

#### Signals
- line_position_changed(int)
- direction_changed(str)
- play_state_changed(bool)

### Tasks
- [ ] Implement VideoPreview.__init__
- [ ] Implement frame display
- [ ] Implement line overlay painting
- [ ] Implement mouse interaction
- [ ] Implement playback controls
- [ ] Connect to VideoProcessor

---

## Phase 7: GUI - Scan Controls

### File: `src/gui/scan_controls.py`

### Class: ScanControls

#### UI Components (QFormLayout)

**Direction**
- QComboBox: [Horizontal, Vertical]

**Line Position**
- QSlider: 0 to video_height (or video_width)
- QSpinBox: 0 to video_height

**Line Width**
- QSpinBox: 1 to 100

**Combine Mode**
- QComboBox: [Average, Stack Stripes]

**Stretch Factors**
- Temporal: QSpinBox 1-100
- Spatial: QSpinBox 1-10

**Time Range**
- Start time: QTimeEdit (HH:MM:SS.mmm)
- End time: QTimeEdit (HH:MM:SS.mmm)
- Duration: QLabel (read-only)

**Frame Step**
- QSpinBox: 1 to 1000

**Output Scale**
- QComboBox: [100%, 75%, 50%, 25%, Custom]
- QSpinBox: 1-200 (for custom)

**Preview Options**
- Show frame preview: QCheckBox
- Show slitscan preview: QCheckBox
- Preview quality: QComboBox [Low, Medium, High]

**Buttons**
- Update Preview: QPushButton
- Generate Full Resolution: QPushButton
- Save Image: QPushButton (disabled initially)

#### Methods

**__init__**
- Create all UI components
- Set up layout
- Connect signals
- Disable controls until video loaded

**set_video_properties(fps, width, height, duration)**
- Enable controls
- Set slider ranges
- Set default time range

**get_params()**
- Return dict of all current parameters

**validate_params()**
- Ensure start_time < end_time
- Ensure line_position + line_width <= dimensions
- Show error messages if invalid

**update_line_position(pos: int)**
- Update slider and spinbox

**debounce**
- Add timer to debounce preview updates (avoid excessive calls)

#### Signals
- params_changed(dict)
- generate_clicked()
- save_clicked()

### Tasks
- [ ] Implement all UI components
- [ ] Implement set_video_properties
- [ ] Implement get_params
- [ ] Implement validate_params
- [ ] Implement debounce logic
- [ ] Connect all signals

---

## Phase 8: GUI - Slitscan Preview

### File: `src/gui/slitscan_preview.py`

### Class: SlitscanPreview

#### Features
- Display slitscan image in scrollable area
- Zoom controls (in/out, slider, fit buttons)
- Dimension info display

#### Components

**__init__**
- QScrollArea with QLabel
- Zoom buttons, slider, fit buttons
- Info label (dimensions, frame count)

**set_image(image: np.ndarray)**
- Convert array to QPixmap
- Update QLabel
- Update dimensions info

**set_zoom(level: float)**
- Scale image to zoom level
- Update scroll area

**zoom_in, zoom_out**
- Adjust zoom level by steps (25% increments)

**fit_to_width, fit_to_height**
- Calculate zoom to fit dimension
- Apply zoom

**clear**
- Clear image display

#### Zoom Levels
- Range: 10% to 400%
- Steps: 25%, 50%, 75%, 100%, 150%, 200%, 300%, 400%

### Tasks
- [ ] Implement SlitscanPreview.__init__
- [ ] Implement image display
- [ ] Implement zoom controls
- [ ] Implement fit functions
- [ ] Add dimension info display

---

## Phase 9: Integration

### File: `main.py` (Application Entry Point)

#### Implementation

```python
import sys
from PySide6.QtWidgets import QApplication
from src.gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
```

### Tasks
- [ ] Create main.py
- [ ] Test application launch

### File: `src/gui/main_window.py` - Integration Methods

#### Additional Methods

**update_preview**
- Get current parameters from scan_controls
- Call video_processor.preview_scan
- Update slitscan_preview with result
- Handle errors

**generate_full_scan**
- Show progress dialog (QProgressDialog)
- Get current parameters
- Call video_processor.extract_*_scan with progress callback
- Update slitscan_preview with full resolution result
- Enable save button
- Close progress dialog

**handle_error(message)**
- Show QMessageBox with error

### Tasks
- [ ] Implement update_preview
- [ ] Implement generate_full_scan
- [ ] Implement handle_error
- [ ] Test full workflow

---

## Phase 10: Testing

### Unit Tests

**tests/test_scan_processor.py**
- Test video loading
- Test horizontal scan extraction
- Test vertical scan extraction
- Test stretch factors
- Test time range handling

**tests/test_geometry.py**
- Test line extraction
- Test combine functions
- Test stretch functions
- Test scale functions

**tests/test_integration.py**
- Test full workflow (video → slitscan)
- Test GUI interaction
- Test save functionality

### Tasks
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Run tests with pytest
- [ ] Fix bugs found in testing

---

## Phase 11: Documentation

### Files to Create

**README.md**
- Project overview
- Installation instructions
- Usage guide
- Features list
- Requirements
- License

**setup.py**
- Package configuration
- Dependencies
- Entry point

### Tasks
- [ ] Write README.md
- [ ] Write setup.py
- [ ] Add inline code comments

---

## Phase 12: Refinement & Polish

### Tasks
- [ ] Test with various video formats (MP4, AVI, MOV)
- [ ] Test extreme values (very long videos, large stretch factors)
- [ ] Optimize preview performance
- [ ] Add keyboard shortcuts
- [ ] Test on both Windows and Linux
- [ ] Fix any remaining bugs
- [ ] Code review and cleanup

---

## User Experience Flow

1. **Launch App**: Empty window with "Open Video" in status bar
2. **Open Video**: File dialog → select video → video loads
3. **Adjust Line Position**: Drag red line on video preview
4. **Configure Settings**: Adjust line width, direction, time range, stretch factors
5. **Preview**: Click "Update Preview" → see low-res slitscan
6. **Generate**: Click "Generate Full Resolution" → progress bar → full-res image
7. **Save**: Click "Save Image" → select path → save as JPEG

---

## Completion Checklist

- [ ] Environment setup complete
- [ ] Project structure created
- [ ] Video processor implemented and tested
- [ ] Utils implemented and tested
- [ ] Main window implemented
- [ ] Video preview implemented with line selector
- [ ] Scan controls implemented
- [ ] Slitscan preview implemented
- [ ] All components integrated
- [ ] Full workflow tested
- [ ] Unit tests passing
- [ ] Documentation complete
- [ ] Cross-platform tested (Windows/Linux)

---

## Phase 13: Threading Implementation

### Overview
Add multi-threaded processing with progress tracking and cancellation support. All operations (preview, full scan, save) will run in background threads with interactive progress bar in status bar.

### Tasks

#### Create Worker Class
- [x] Create `src/gui/slitscan_worker.py`
- [x] Implement `SlitscanWorker(QObject)` class
  - [x] Signals: `progress_updated(int)`, `finished(object, str)`, `error(str)`, `canceled(object, str)`
  - [x] Methods: `cancel()`, `run()`, `_run_preview()`, `_run_full_scan()`, `_run_save_image()`
  - [x] Progress callback wrapper with cancellation check
  - [x] Thread-safe communication via Qt signals

#### Update VideoProcessor
- [x] Add `_cancel_requested` flag to `__init__`
- [x] Implement `cancel()` method
- [x] Implement `is_canceled()` method
- [x] Implement `reset_cancel()` method
- [x] Modify extraction loops to check cancellation every 10 frames
- [x] Return partial result when canceled (if any frames processed)
- [x] Update progress_callback calls to return early if canceled

#### Update MainWindow - Status Bar with Hover
- [x] Add `QStackedWidget` for progress/cancel toggle
- [x] Add `QProgressBar` (page 0)
- [x] Add QPushButton "✕ Cancel" (page 1)
- [x] Style cancel button with red theme
- [x] Install event filter on stacked widget
- [x] Implement `eventFilter()` for hover detection
- [x] Show cancel button on `QEvent.Enter`
- [x] Show progress bar on `QEvent.Leave`
- [x] Add to status bar as permanent widget
- [x] Hide widget when not processing

#### Update MainWindow - Thread Management
- [x] Add `current_worker` and `current_thread` to `__init__`
- [x] Add `is_processing` flag
- [x] Implement `setup_status_bar_progress()` method
- [x] Implement `set_processing_state(processing, operation)` method
- [x] Implement `cancel_current_operation()` method
- [x] Implement `start_worker(worker, operation)` method
- [x] Implement `cleanup_worker()` method
- [x] Add thread cleanup in `closeEvent()`

#### Update MainWindow - Slot Methods
- [x] Implement `on_worker_progress(percent)` - Update progress bar
- [x] Implement `on_worker_finished(result, operation_type)` - Handle success
- [x] Implement `on_worker_error(error_msg)` - Show error dialog
- [x] Implement `on_worker_canceled(partial_result, operation_type)` - Handle cancellation with partial result prompt
- [x] Connect all signals in `start_worker()`

#### Update Processing Methods
- [x] Refactor `update_preview()` to use worker thread
- [x] Refactor `generate_full_scan()` to use worker thread (remove QProgressDialog)
- [x] Refactor `save_image()` to ALWAYS use worker thread (no size check)
- [x] All operations call `start_worker()` instead of synchronous execution
- [x] Update `closeEvent()` to handle processing in progress with prompt

---

## Phase 14: Logging Implementation

### Overview
Add logging of errors to error.log file for debugging and troubleshooting.

### Tasks

#### Setup Logging in VideoProcessor
- [x] Import logging module
- [x] Configure file handler for error.log
- [x] Configure stream handler for console output
- [x] Set up logger with ERROR level
- [x] Add logging to `load_video()` method
- [x] Add logging to `extract_horizontal_scan()` method
- [x] Add logging to `extract_vertical_scan()` method
- [x] Log video loading failures
- [x] Log frame reading failures
- [x] Log extraction errors with try/except blocks

#### Setup Logging in SlitscanWorker
- [x] Import logging module
- [x] Set up logger for worker thread
- [x] Add logging to `run()` method
- [x] Log cancellation events
- [x] Add logging to `_run_save_image()` method
- [x] Log save operation errors

#### Setup Logging in MainWindow
- [x] Import logging module
- [x] Add logging to `open_video()` method
- [x] Add logging to `on_worker_error()` method
- [x] Add logging to `save_image()` method
- [x] Log GUI errors and user actions
- [x] Log file operations

#### File Changes
- [x] Modify `src/video_processor.py` - Add logging configuration
- [x] Modify `src/gui/slitscan_worker.py` - Add logging configuration
- [x] Modify `src/gui/main_window.py` - Add logging configuration

---

## Phase 14: Completion Checklist
- [x] Logging configured in all modules
- [x] error.log file created
- [x] Errors logged with timestamps
- [x] Worker errors logged
- [x] Video processing errors logged
- [x] GUI errors logged
- [x] Save operation errors logged
- [x] Cancellation events logged

---

## Notes

- Use PySide6 for cross-platform compatibility
- Default output format: JPEG
- Preview quality options: Low/Medium/High
- Maximum line width: 100px
- Temporal stretch: 1-100x
- Spatial stretch: 1-10x
- Support both horizontal and vertical scans
- Real-time preview with debounce
- Progress dialogs for long operations
