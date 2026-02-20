from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QSlider, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont
import numpy as np
import cv2


class VideoPreviewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.setMinimumSize(400, 300)
        
        self.frame = None
        self.line_position = 0
        self.line_width = 1
        self.direction = 'horizontal'
        
        self.dragging = False
        self.drag_start_pos = None
    
    def set_frame(self, frame: np.ndarray):
        self.frame = frame
        if self.direction == 'horizontal':
            self.line_position = frame.shape[0] // 2
        else:
            self.line_position = frame.shape[1] // 2
        self.update()
    
    def set_line_position(self, position: int):
        self.line_position = position
        self.update()
    
    def set_line_width(self, width: int):
        self.line_width = width
        self.update()
    
    def set_direction(self, direction: str):
        self.direction = direction
        if self.frame is not None:
            if direction == 'horizontal':
                self.line_position = self.frame.shape[0] // 2
            else:
                self.line_position = self.frame.shape[1] // 2
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.frame is None:
            painter.fillRect(self.rect(), QColor(30, 30, 30))
            painter.setPen(QColor(150, 150, 150))
            painter.setFont(QFont('Arial', 12))
            painter.drawText(self.rect(), Qt.AlignCenter, "No video loaded")
            return
        
        h, w = self.frame.shape[:2]
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
        
        rgb_frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg).scaled(scaled_width, scaled_height, Qt.KeepAspectRatio)
        
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
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.frame is not None:
            self.dragging = True
            self.drag_start_pos = event.pos()
            self.update_line_from_mouse(event.pos())
    
    def mouseMoveEvent(self, event):
        if self.dragging and self.frame is not None:
            self.update_line_from_mouse(event.pos())
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.dragging:
                self.dragging = False
                if self.frame is not None:
                    self.parent().parent().parent().line_position_changed.emit(self.line_position)
    
    def update_line_from_mouse(self, pos):
        if not hasattr(self, 'display_rect'):
            return
        
        x, y, w, h = self.display_rect
        
        if self.direction == 'horizontal':
            if x <= pos.x() <= x + w:
                new_pos = int((pos.y() - y) / self.scale_y)
                max_pos = self.frame.shape[0] - 1
                self.line_position = max(0, min(new_pos, max_pos))
        else:
            if y <= pos.y() <= y + h:
                new_pos = int((pos.x() - x) / self.scale_x)
                max_pos = self.frame.shape[1] - 1
                self.line_position = max(0, min(new_pos, max_pos))
        
        self.update()


class VideoPreview(QWidget):
    line_position_changed = Signal(int)
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.video_width = 0
        self.video_height = 0
        self.video_fps = 30.0
        self.current_time = 0.0
        self.playing = False
        
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.playback_step)
        
        self.frames_cache = {}
        self.cache_size = 100
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.preview_widget = VideoPreviewWidget()
        layout.addWidget(self.preview_widget, 1)
        
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
        controls_layout.addWidget(self.time_slider, 1)
        
        self.time_label = QLabel("00:00.000")
        controls_layout.addWidget(self.time_label)
        
        controls_container = QFrame()
        controls_container.setLayout(controls_layout)
        layout.addWidget(controls_container)
    
    def set_frame(self, frame: np.ndarray):
        self.preview_widget.set_frame(frame)
    
    def set_video_properties(self, width: int, height: int, fps: float):
        self.video_width = width
        self.video_height = height
        self.video_fps = fps
    
    def set_line_position(self, position: int):
        self.preview_widget.set_line_position(position)
    
    def set_line_width(self, width: int):
        self.preview_widget.set_line_width(width)
    
    def set_direction(self, direction: str):
        self.preview_widget.set_direction(direction)
    
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
        self.update_time_display()
    
    def step_forward(self):
        self.current_time += 1.0 / self.video_fps
        self.update_time_display()
    
    def step_backward(self):
        self.current_time -= 1.0 / self.video_fps
        if self.current_time < 0:
            self.current_time = 0
        self.update_time_display()
    
    def seek_to_time(self, time_sec: float):
        self.current_time = time_sec
        self.update_time_display()
    
    def on_slider_changed(self, value):
        pass
    
    def update_time_display(self):
        minutes = int(self.current_time // 60)
        seconds = int(self.current_time % 60)
        milliseconds = int((self.current_time % 1) * 1000)
        self.time_label.setText(f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}")
    
    def stop_playback(self):
        if hasattr(self, 'playback_timer') and self.playback_timer.isActive():
            self.playback_timer.stop()
        self.playing = False
    
    def __del__(self):
        self.stop_playback()
    
    def mouseReleaseEvent(self, event):
        pos = event.pos()
        child = self.childAt(pos)
        if child == self.preview_widget:
            self.line_position_changed.emit(self.preview_widget.line_position)
        super().mouseReleaseEvent(event)
