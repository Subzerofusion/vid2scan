from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter, 
    QFileDialog, QMessageBox, QMenu, QMenuBar, QStatusBar, QProgressDialog,
    QProgressBar, QPushButton, QStackedWidget, QLabel, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal, QThread, QEvent
from PySide6.QtGui import QAction, QImage, QPixmap, QShortcut, QKeySequence
import numpy as np
import logging
from pathlib import Path
from PIL import Image

from src.video_processor import VideoProcessor
from src.gui.video_preview import VideoPreview
from src.gui.slitscan_preview import SlitscanPreview
from src.gui.scan_controls import ScanControls
from src.gui.slitscan_worker import SlitscanWorker

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vid2Scan - Line Scan / Slit Scan Photo Generator")
        self.resize(1400, 900)
        
        self.video_processor = VideoProcessor()
        self.current_slitscan = None
        self.current_worker = None
        self.current_thread = None
        self.is_processing = False
        self.last_save_path = None
        
        self.create_menu_bar()
        self.create_central_widget()
        self.create_status_bar()
        self.setup_status_bar_progress()
        self.setup_shortcuts()
        
        self.scan_controls.setEnabled(False)
    
    def setup_shortcuts(self):
        self.cancel_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.cancel_shortcut.activated.connect(self.cancel_current_operation)
    
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("&File")
        
        open_action = QAction("&Open Video...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_video)
        file_menu.addAction(open_action)
        
        save_action = QAction("&Save Image...", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_image)
        save_action.setEnabled(False)
        self.save_action = save_action
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_central_widget(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.slitscan_preview = SlitscanPreview()
        self.video_preview = VideoPreview()
        
        preview_buttons = QWidget()
        preview_buttons_layout = QHBoxLayout(preview_buttons)
        preview_buttons_layout.setContentsMargins(5, 5, 5, 5)
        
        self.update_preview_button = QPushButton('Update Preview')
        self.update_preview_button.clicked.connect(self.update_preview)
        preview_buttons_layout.addWidget(self.update_preview_button)
        
        self.preview_size_label = QLabel('Size: -')
        self.preview_size_label.setStyleSheet('color: #666; font-size: 10px;')
        preview_buttons_layout.addWidget(self.preview_size_label)
        
        preview_buttons_layout.addStretch()
        
        self.generate_button = QPushButton('Generate Full Res')
        self.generate_button.clicked.connect(self.generate_full_scan)
        preview_buttons_layout.addWidget(self.generate_button)
        
        left_splitter = QSplitter(Qt.Orientation.Vertical)
        
        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.addWidget(self.slitscan_preview, 1)
        preview_layout.addWidget(preview_buttons)
        
        left_splitter.addWidget(preview_container)
        left_splitter.addWidget(self.video_preview)
        left_splitter.setSizes([450, 450])
        
        left_layout.addWidget(left_splitter)
        main_splitter.addWidget(left_widget)
        
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)
        
        controls_scroll = QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        controls_scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self.scan_controls = ScanControls()
        controls_scroll.setWidget(self.scan_controls)
        right_layout.addWidget(controls_scroll, 1)
        
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([1000, 400])
        
        main_layout.addWidget(main_splitter)
        
        self.video_preview.line_position_changed.connect(self.on_line_position_changed)
        self.scan_controls.line_position_changed.connect(self.on_controls_line_position_changed)
        self.scan_controls.line_width_changed.connect(self.video_preview.set_line_width)
        self.scan_controls.crop_changed.connect(self.on_crop_changed)
        self.scan_controls.params_changed.connect(self.update_preview)
        self.scan_controls.save_clicked.connect(self.save_image)
        self.scan_controls.direction_combo.currentTextChanged.connect(self.on_direction_changed)
        self.video_preview.time_changed.connect(self.on_video_time_changed)
        self.scan_controls.set_start_from_time.connect(self.on_set_start_from_time)
        self.scan_controls.set_end_from_time.connect(self.on_set_end_from_time)
        self.scan_controls.go_to_start_time.connect(self.on_go_to_start_time)
        self.scan_controls.go_to_end_time.connect(self.on_go_to_end_time)
    
    def create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Open a video to begin. Press ESC to cancel operations.")
    
    def setup_status_bar_progress(self):
        self.progress_stack = QStackedWidget()
        self.progress_stack.setFixedWidth(200)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_stack.addWidget(self.progress_bar)
        
        self.cancel_button = QPushButton("Cancel (ESC)")
        self.cancel_button.setFixedHeight(30)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
            QPushButton:pressed {
                background-color: #8e0000;
            }
        """)
        self.cancel_button.clicked.connect(self.cancel_current_operation)
        self.progress_stack.addWidget(self.cancel_button)
        
        self.progress_stack.installEventFilter(self)
        
        self.progress_stack.setCurrentIndex(0)
        self.progress_stack.setVisible(False)
        
        self.status_bar.addPermanentWidget(self.progress_stack)
    
    def eventFilter(self, obj, event):
        if obj == self.progress_stack and self.progress_stack.isVisible():
            if event.type() == QEvent.Type.Enter:
                if self.is_processing:
                    self.progress_stack.setCurrentIndex(1)
                    return False
            
            elif event.type() == QEvent.Type.Leave:
                if self.is_processing:
                    self.progress_stack.setCurrentIndex(0)
                    return False
        
        return super().eventFilter(obj, event)
    
    def set_processing_state(self, processing: bool, operation: str = ""):
        self.is_processing = processing
        
        if processing:
            self.progress_stack.setVisible(True)
            self.progress_stack.setCurrentIndex(0)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.status_bar.showMessage(f"{operation}... (Press ESC to cancel)")
            self.scan_controls.setEnabled(False)
            self.video_preview.setEnabled(False)
            self.save_action.setEnabled(False)
        else:
            self.progress_stack.setVisible(False)
            self.progress_stack.setCurrentIndex(0)
            self.status_bar.showMessage("Ready. Press ESC to cancel operations.")
            self.scan_controls.setEnabled(True)
            self.video_preview.setEnabled(True)
            if self.current_slitscan is not None:
                self.save_action.setEnabled(True)
    
    def cancel_current_operation(self):
        if self.is_processing and self.current_worker:
            self.current_worker.cancel()
            self.status_bar.showMessage("Canceling...")
    
    def start_worker(self, worker: SlitscanWorker, operation: str):
        if self.current_worker:
            self.cancel_current_operation()
            if self.current_thread and self.current_thread.isRunning():
                self.current_thread.quit()
                if not self.current_thread.wait(2000):
                    self.current_thread.terminate()
                    self.current_thread.wait(500)
        
        self.current_worker = worker
        self.current_thread = QThread()
        worker.moveToThread(self.current_thread)
        
        self.current_thread.started.connect(worker.run)
        worker.progress_updated.connect(self.on_worker_progress)
        worker.finished.connect(lambda r, t=operation: self.on_worker_finished(r, t))
        worker.error.connect(self.on_worker_error)
        worker.canceled.connect(lambda r, t=operation: self.on_worker_canceled(r, t))
        
        worker.finished.connect(self.current_thread.quit)
        worker.finished.connect(self.cleanup_worker)
        self.current_thread.finished.connect(worker.deleteLater)
        self.current_thread.finished.connect(self.current_thread.deleteLater)
        
        self.set_processing_state(True, operation)
        self.current_thread.start()
    
    def cleanup_worker(self):
        import gc
        gc.collect()
        self.current_worker = None
    
    def on_worker_progress(self, percent: int):
        self.progress_bar.setValue(percent)
        self.status_bar.showMessage(f"Processing... {percent}% (Press ESC to cancel)")
    
    def on_worker_finished(self, result, operation_type: str):
        if operation_type == 'preview':
            if result is not None:
                self.slitscan_preview.set_image(result)
                if len(result.shape) == 2:
                    h, w = result.shape
                else:
                    h, w = result.shape[0], result.shape[1]
                self.preview_size_label.setText(f'Size: {w}x{h}')
                self.status_bar.showMessage("Preview updated")
            else:
                self.preview_size_label.setText('Size: -')
                self.status_bar.showMessage("No frames in specified range")
                
        elif operation_type == 'full_scan':
            if result is not None:
                self.current_slitscan = result
                self.slitscan_preview.set_image(result)
                if len(result.shape) == 2:
                    h, w = result.shape
                else:
                    h, w = result.shape[0], result.shape[1]
                self.preview_size_label.setText(f'Size: {w}x{h}')
                self.save_action.setEnabled(True)
                self.scan_controls.enable_save_button()
                self.status_bar.showMessage("Full resolution slitscan generated")
            else:
                self.preview_size_label.setText('Size: -')
                self.status_bar.showMessage("No frames in specified range")
                
        elif operation_type == 'save_image':
            if result is not None and self.last_save_path:
                self.status_bar.showMessage(f"Saved: {Path(self.last_save_path).name}")
        
        self.set_processing_state(False)
    
    def on_worker_error(self, error_msg: str):
        logger.error(f"Worker error: {error_msg}")
        QMessageBox.critical(
            self,
            "Error",
            error_msg
        )
        self.status_bar.showMessage(f"Error: {error_msg}")
        self.set_processing_state(False)
    
    def on_worker_canceled(self, partial_result, operation_type: str):
        if partial_result is not None:
            if operation_type == 'full_scan':
                self.current_slitscan = partial_result
                self.slitscan_preview.set_image(partial_result)
                reply = QMessageBox.question(
                    self, "Operation Canceled",
                    "Processing was canceled. Keep partial result?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.save_action.setEnabled(True)
                    self.status_bar.showMessage("Partial result kept")
                else:
                    self.slitscan_preview.clear()
                    self.status_bar.showMessage("Operation canceled")
            else:
                self.status_bar.showMessage("Operation canceled")
        else:
            self.status_bar.showMessage("Operation canceled (no partial result)")
        
        self.set_processing_state(False)
    
    def open_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Open Video File",
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv);;All Files (*)"
        )
        
        if not file_path:
            return
        
        logger.info(f"Opening video: {file_path}")
        
        if self.video_processor.load_video(file_path):
            vp = self.video_processor
            self.status_bar.showMessage(
                f"Loaded: {Path(file_path).name} | "
                f"Size: {vp.width}x{vp.height} | "
                f"Duration: {vp.duration:.2f}s | "
                f"FPS: {vp.fps:.2f}"
            )
            
            first_frame = self.video_processor.get_frame_at_time(0)
            if first_frame is not None:
                self.video_preview.set_frame(first_frame, reset_position=True)
                self.video_preview.set_video_properties(
                    vp.width, vp.height, vp.fps
                )
                self.video_preview.set_video_duration(vp.duration)
            
            self.scan_controls.set_video_properties(
                vp.fps, vp.width, vp.height, vp.duration
            )
            self.scan_controls.setEnabled(True)
            self.save_action.setEnabled(False)
            self.current_slitscan = None
            self.slitscan_preview.clear()
        else:
            error_msg = "Could not open video file. Please check the file format."
            logger.error(f"Failed to open video {file_path}: {error_msg}")
            QMessageBox.critical(
                self, 
                "Error", 
                error_msg
            )
    
    def save_image(self):
        if self.current_slitscan is None or self.is_processing:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Slitscan Image",
            "slitscan.jpg",
            "JPEG Image (*.jpg);;PNG Image (*.png);;TIFF Image (*.tiff);;All Files (*)"
        )
        
        if not file_path:
            return
        
        logger.info(f"Saving image to: {file_path}")
        
        self.last_save_path = file_path
        
        worker = SlitscanWorker(
            self.video_processor,
            {
                'image': self.current_slitscan,
                'path': file_path
            },
            'save_image',
            save_path=file_path
        )
        
        self.start_worker(worker, "Saving image")
    
    def update_preview(self):
        if self.video_processor.video_path is None:
            return
        
        if self.is_processing:
            return
        
        params = self.scan_controls.get_params()
        
        if not self.scan_controls.validate_params():
            return
        
        worker = SlitscanWorker(
            self.video_processor,
            params,
            'preview'
        )
        
        self.start_worker(worker, "Generating preview")
    
    def generate_full_scan(self):
        if self.video_processor.video_path is None or self.is_processing:
            return
        
        params = self.scan_controls.get_params()
        
        if not self.scan_controls.validate_params():
            return
        
        worker = SlitscanWorker(
            self.video_processor,
            params,
            'full_scan'
        )
        
        self.start_worker(worker, "Generating slitscan")
    
    def on_line_position_changed(self, position):
        self.scan_controls.update_line_position(position)
    
    def on_controls_line_position_changed(self, position):
        self.video_preview.set_line_position(position)
    
    def on_direction_changed(self, direction):
        self.video_preview.set_direction(direction)
    
    def on_crop_changed(self, crop_top: int, crop_bottom: int):
        self.video_preview.set_crop(crop_top, crop_bottom)
    
    def on_video_time_changed(self, time_sec: float):
        self._current_time = time_sec
        if self.video_processor.video_path is not None:
            frame = self.video_processor.get_frame_at_time(time_sec)
            if frame is not None:
                self.video_preview.set_frame(frame, reset_position=False)
    
    def on_set_start_from_time(self):
        if hasattr(self, '_current_time'):
            self.scan_controls.set_start_time(self._current_time)
    
    def on_set_end_from_time(self):
        if hasattr(self, '_current_time'):
            self.scan_controls.set_end_time(self._current_time)
    
    def on_go_to_start_time(self):
        start_time = self.scan_controls.get_start_time()
        self._current_time = start_time
        frame = self.video_processor.get_frame_at_time(start_time)
        if frame is not None:
            self.video_preview.set_frame(frame, reset_position=False)
    
    def on_go_to_end_time(self):
        end_time = self.scan_controls.get_end_time()
        self._current_time = end_time
        frame = self.video_processor.get_frame_at_time(end_time)
        if frame is not None:
            self.video_preview.set_frame(frame, reset_position=False)
    
    def show_about(self):
        QMessageBox.about(
            self,
            "About Vid2Scan",
            "Vid2Scan - Line Scan / Slit Scan Photo Generator\n\n"
            "A cross-platform application for creating line scan and "
            "slit scan photographs from videos.\n\n"
            "Built with Python, PySide6, and OpenCV."
        )
    
    def closeEvent(self, event):
        if hasattr(self, 'scan_controls') and self.scan_controls:
            if hasattr(self.scan_controls, 'stop_debounce'):
                self.scan_controls.stop_debounce()
        if hasattr(self, 'video_preview') and self.video_preview:
            if hasattr(self.video_preview, 'stop_playback'):
                self.video_preview.stop_playback()
        
        if self.is_processing and self.current_worker:
            reply = QMessageBox.question(
                self, 
                "Processing in Progress",
                "An operation is in progress. Cancel and close?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
            
            self.current_worker.cancel()
            
            if self.current_thread and self.current_thread.isRunning():
                self.current_thread.quit()
                self.current_thread.wait(1000)
            
            self.is_processing = False
            self.video_processor.close()
            event.accept()
        
        self.video_processor.close()
        event.accept()
