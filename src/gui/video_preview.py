from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QSlider, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont
import numpy as np
import cv2


class VideoPreviewWidget(QWidget):
    line_position_changed = Signal(int)
    crop_changed = Signal(int, int)
    
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.setMinimumSize(400, 300)
        
        self._frame = None
        self._display_pixmap = None
        self.line_position = 0
        self.line_width = 1
        self.direction = 'horizontal'
        self.crop_top = 0
        self.crop_bottom = 0
        self._line_position_initialized = False
        
        self.dragging = False
        self.drag_start_pos = None
        self.dragging_crop = None
    
    @property
    def frame(self):
        return self._frame
    
    def set_frame(self, frame: np.ndarray, reset_position: bool = False):
        self._frame = frame.copy()
        if not self._line_position_initialized or reset_position:
            if self.direction == 'horizontal':
                self.line_position = frame.shape[0] // 2
            else:
                self.line_position = frame.shape[1] // 2
            self._line_position_initialized = True
        self._update_display_pixmap()
        self.update()
    
    def _update_display_pixmap(self):
        if self._frame is None:
            self._display_pixmap = None
            return
        rgb_frame = cv2.cvtColor(self._frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self._display_pixmap = QPixmap.fromImage(qimg)
    
    def set_line_position(self, position: int):
        self.line_position = position
        self.update()
    
    def set_line_width(self, width_start: int, width_end: int = 1):
        self.line_width = width_start
        self.update()
    
    def set_direction(self, direction: str):
        self.direction = direction
        self._line_position_initialized = False
        if self._frame is not None:
            if direction == 'horizontal':
                self.line_position = self._frame.shape[0] // 2
            else:
                self.line_position = self._frame.shape[1] // 2
            self._line_position_initialized = True
        self.update()
    
    def set_crop(self, crop_top: int, crop_bottom: int):
        self.crop_top = crop_top
        self.crop_bottom = crop_bottom
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self._display_pixmap is None or self._frame is None:
            painter.fillRect(self.rect(), QColor(30, 30, 30))
            painter.setPen(QColor(150, 150, 150))
            painter.setFont(QFont('Arial', 12))
            painter.drawText(self.rect(), Qt.AlignCenter, "No video loaded")
            return
        
        h, w = self._frame.shape[:2]
        aspect_ratio = w / h
        
        widget_size = self.size()
        widget_width = widget_size.width()
        widget_height = widget_size.height()
        
        if widget_width / widget_height > aspect_ratio:
            scaled_height = widget_height
            scaled_width = int(scaled_height * aspect_ratio)
        else:
            scaled_width = widget_width
            scaled_height = int(scaled_width / aspect_ratio)
        
        x = (widget_width - scaled_width) // 2
        y = (widget_height - scaled_height) // 2
        
        self.display_rect = (x, y, scaled_width, scaled_height)
        self.scale_x = scaled_width / w
        self.scale_y = scaled_height / h
        
        pixmap = self._display_pixmap.scaled(scaled_width, scaled_height, Qt.KeepAspectRatio)
        
        painter.drawPixmap(x, y, pixmap)
        
        pen = QPen(QColor(255, 0, 0))
        pen.setWidth(2)
        painter.setPen(pen)
        
        if self.direction == 'horizontal':
            line_y = int(y + self.line_position * self.scale_y)
            line_start_x = x
            line_end_x = x + scaled_width
            
            painter.drawLine(line_start_x, line_y, line_end_x, line_y)
            
            if self.line_width > 1:
                pen.setWidth(1)
                pen.setColor(QColor(255, 100, 100, 150))
                painter.setPen(pen)
                for i in range(1, self.line_width):
                    offset_y = int(i * self.scale_y)
                    painter.drawLine(line_start_x, line_y + offset_y, line_end_x, line_y + offset_y)
        else:
            line_x = int(x + self.line_position * self.scale_x)
            line_start_y = y
            line_end_y = y + scaled_height
            
            painter.drawLine(line_x, line_start_y, line_x, line_end_y)
            
            if self.line_width > 1:
                pen.setWidth(1)
                pen.setColor(QColor(255, 100, 100, 150))
                painter.setPen(pen)
                for i in range(1, self.line_width):
                    offset_x = int(i * self.scale_x)
                    painter.drawLine(line_x + offset_x, line_start_y, line_x + offset_x, line_end_y)
        
        if self.crop_top > 0 or self.crop_bottom > 0:
            pen.setWidth(2)
            pen.setStyle(Qt.DashLine)
            pen.setColor(QColor(0, 255, 255))
            painter.setPen(pen)
            
            if self.crop_top > 0:
                crop_top_y = int(y + self.crop_top * self.scale_y)
                painter.drawLine(x, crop_top_y, x + scaled_width, crop_top_y)
            
            if self.crop_bottom > 0:
                crop_bottom_y = int(y + (h - self.crop_bottom) * self.scale_y)
                painter.drawLine(x, crop_bottom_y, x + scaled_width, crop_bottom_y)
            
            pen.setStyle(Qt.SolidLine)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._frame is not None:
            self.dragging = True
            self.drag_start_pos = event.pos()
            self.update_line_from_mouse(event.pos())
    
    def mouseMoveEvent(self, event):
        if self.dragging and self._frame is not None:
            self.update_line_from_mouse(event.pos())
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.dragging:
                self.dragging = False
                if self._frame is not None:
                    self.line_position_changed.emit(self.line_position)
    
    def update_line_from_mouse(self, pos):
        if not hasattr(self, 'display_rect') or self._frame is None:
            return
        
        x, y, w, h = self.display_rect
        
        if self.direction == 'horizontal':
            if x <= pos.x() <= x + w:
                new_pos = int((pos.y() - y) / self.scale_y)
                max_pos = self._frame.shape[0] - 1
                self.line_position = max(0, min(new_pos, max_pos))
        else:
            if y <= pos.y() <= y + h:
                new_pos = int((pos.x() - x) / self.scale_x)
                max_pos = self._frame.shape[1] - 1
                self.line_position = max(0, min(new_pos, max_pos))
        
        self.update()


class VideoPreview(QWidget):
    line_position_changed = Signal(int)
    time_changed = Signal(float)
    
    def __init__(self):
        super().__init__()
        self.video_width = 0
        self.video_height = 0
        self.video_fps = 30.0
        self._video_duration = 0.0
        self.current_time = 0.0
        self.playing = False
        self._slider_dragging = False
        self._pending_seek_time = None
        self.setup_ui()
        self.setup_debounce()
        self.setup_playback_timer()
    
    @property
    def video_duration(self) -> float:
        return self._video_duration
    
    def setup_playback_timer(self):
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.playback_step)
    
    def setup_debounce(self):
        self.seek_debounce_timer = QTimer()
        self.seek_debounce_timer.setSingleShot(True)
        self.seek_debounce_timer.setInterval(100)
        self.seek_debounce_timer.timeout.connect(self._emit_pending_seek)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.preview_widget = VideoPreviewWidget()
        layout.addWidget(self.preview_widget, 1)
        self.preview_widget.line_position_changed.connect(self.line_position_changed.emit)
        
        controls_layout = QHBoxLayout()
        
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_playback)
        controls_layout.addWidget(self.play_button)
        
        self.prev_button = QPushButton("<<")
        self.prev_button.clicked.connect(self.step_backward)
        controls_layout.addWidget(self.prev_button)
        
        self.next_button = QPushButton(">>")
        self.next_button.clicked.connect(self.step_forward)
        controls_layout.addWidget(self.next_button)
        
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(1000)
        self.time_slider.valueChanged.connect(self.on_slider_changed)
        self.time_slider.sliderPressed.connect(self.on_slider_pressed)
        self.time_slider.sliderReleased.connect(self.on_slider_released)
        controls_layout.addWidget(self.time_slider, 1)
        
        self.time_label = QLabel("00:00.000")
        controls_layout.addWidget(self.time_label)
        
        controls_container = QFrame()
        controls_container.setLayout(controls_layout)
        layout.addWidget(controls_container)
    
    def set_frame(self, frame: np.ndarray, reset_position: bool = False):
        self.preview_widget.set_frame(frame, reset_position)
    
    def set_video_properties(self, width: int, height: int, fps: float):
        self.video_width = width
        self.video_height = height
        self.video_fps = fps
    
    def set_video_duration(self, duration: float):
        self._video_duration = duration
    
    def set_line_position(self, position: int):
        self.preview_widget.set_line_position(position)
    
    def set_line_width(self, width_start: int, width_end: int = 1):
        self.preview_widget.set_line_width(width_start, width_end)
    
    def set_direction(self, direction: str):
        self.preview_widget.set_direction(direction)
    
    def set_crop(self, crop_top: int, crop_bottom: int):
        self.preview_widget.set_crop(crop_top, crop_bottom)
    
    def toggle_playback(self):
        if self.playing:
            self.pause_playback()
        else:
            self.start_playback()
    
    def start_playback(self):
        self.playing = True
        self.play_button.setText("Pause")
        interval = int(1000 / self.video_fps)
        self.playback_timer.start(interval)
    
    def pause_playback(self):
        self.playing = False
        self.play_button.setText("Play")
        self.playback_timer.stop()
    
    def playback_step(self):
        self.current_time += 1.0 / self.video_fps
        if self.current_time > self.video_duration:
            self.current_time = 0
        self.update_time_display()
        self.time_changed.emit(self.current_time)
    
    def step_forward(self):
        self.current_time += 1.0 / self.video_fps
        if self.current_time > self.video_duration:
            self.current_time = self.video_duration
        self.update_time_display()
        self.time_changed.emit(self.current_time)
    
    def step_backward(self):
        self.current_time -= 1.0 / self.video_fps
        if self.current_time < 0:
            self.current_time = 0
        self.update_time_display()
        self.time_changed.emit(self.current_time)
    
    def seek_to_time(self, time_sec: float):
        self.current_time = max(0, min(time_sec, self.video_duration))
        self.update_time_display()
    
    def on_slider_changed(self, value):
        if self.video_duration > 0:
            self.current_time = (value / 1000.0) * self.video_duration
            self.update_time_display()
            
            if self._slider_dragging:
                self._pending_seek_time = self.current_time
                self.seek_debounce_timer.start()
            else:
                self.time_changed.emit(self.current_time)
    
    def on_slider_pressed(self):
        self._slider_dragging = True
        self.seek_debounce_timer.stop()
    
    def on_slider_released(self):
        self._slider_dragging = False
        self.seek_debounce_timer.stop()
        if self._pending_seek_time is not None:
            self.time_changed.emit(self._pending_seek_time)
            self._pending_seek_time = None
    
    def _emit_pending_seek(self):
        if self._pending_seek_time is not None:
            self.time_changed.emit(self._pending_seek_time)
            self._pending_seek_time = None
    
    def update_time_display(self):
        minutes = int(self.current_time // 60)
        seconds = int(self.current_time % 60)
        milliseconds = int((self.current_time % 1) * 1000)
        self.time_label.setText(f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}")
        
        if self.video_duration > 0:
            slider_value = int((self.current_time / self.video_duration) * 1000)
            self.time_slider.blockSignals(True)
            self.time_slider.setValue(slider_value)
            self.time_slider.blockSignals(False)
    
    def stop_playback(self):
        if hasattr(self, 'playback_timer') and self.playback_timer.isActive():
            self.playback_timer.stop()
        if hasattr(self, 'seek_debounce_timer') and self.seek_debounce_timer.isActive():
            self.seek_debounce_timer.stop()
        self.playing = False
    
    def stop_debounce(self):
        if hasattr(self, 'seek_debounce_timer') and self.seek_debounce_timer.isActive():
            self.seek_debounce_timer.stop()
            self._pending_seek_time = None
    
    def __del__(self):
        self.stop_playback()
    
    def mouseReleaseEvent(self, event):
        pos = event.pos()
        child = self.childAt(pos)
        if child == self.preview_widget:
            self.line_position_changed.emit(self.preview_widget.line_position)
        super().mouseReleaseEvent(event)
