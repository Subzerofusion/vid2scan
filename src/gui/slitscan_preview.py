from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QScrollArea, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage
import numpy as np
import cv2


class SlitscanPreview(QWidget):
    def __init__(self):
        super().__init__()
        self.current_image = None
        self.frame_count = 0
        self.zoom_level = 1.0
        self.setup_ui()
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(200, 200)
        self.image_label.setStyleSheet("background-color: #1e1e1e;")
        
        self.scroll_area.setWidget(self.image_label)
        main_layout.addWidget(self.scroll_area, 1)
        
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        info_layout = QHBoxLayout(info_frame)
        
        self.info_label = QLabel("No slitscan generated")
        info_layout.addWidget(self.info_label, 1)
        
        main_layout.addWidget(info_frame)
        
        controls_layout = QHBoxLayout()
        
        self.zoom_out_button = QPushButton("-")
        self.zoom_out_button.setFixedWidth(30)
        self.zoom_out_button.clicked.connect(self.zoom_out)
        controls_layout.addWidget(self.zoom_out_button)
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 400)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.on_zoom_slider_changed)
        controls_layout.addWidget(self.zoom_slider, 1)
        
        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setFixedWidth(30)
        self.zoom_in_button.clicked.connect(self.zoom_in)
        controls_layout.addWidget(self.zoom_in_button)
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(50)
        controls_layout.addWidget(self.zoom_label)
        
        self.fit_width_button = QPushButton("Fit Width")
        self.fit_width_button.clicked.connect(self.fit_to_width)
        controls_layout.addWidget(self.fit_width_button)
        
        self.fit_height_button = QPushButton("Fit Height")
        self.fit_height_button.clicked.connect(self.fit_to_height)
        controls_layout.addWidget(self.fit_height_button)
        
        main_layout.addLayout(controls_layout)
    
    def set_image(self, image: np.ndarray):
        self.current_image = image
        self.update_display()
    
    def update_display(self):
        if self.current_image is None:
            self.image_label.clear()
            self.info_label.setText("No slitscan generated")
            return
        
        h, w = self.current_image.shape[:2]
        
        self.info_label.setText(f"Size: {w} x {h} px | Frames: {self.frame_count}")
        
        if self.zoom_level != 1.0:
            new_w = int(w * self.zoom_level)
            new_h = int(h * self.zoom_level)
            scaled = cv2.resize(self.current_image, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
        else:
            scaled = self.current_image
        
        if len(scaled.shape) == 2:
            h, w = scaled.shape
            bytes_per_line = w
            scaled_copy = np.ascontiguousarray(scaled)
            qimg = QImage(scaled_copy.data, w, h, bytes_per_line, QImage.Format.Format_Grayscale8).copy()
        else:
            h, w, ch = scaled.shape
            bytes_per_line = ch * w
            if ch == 3:
                scaled_rgb = cv2.cvtColor(scaled, cv2.COLOR_BGR2RGB)
                scaled_copy = np.ascontiguousarray(scaled_rgb)
                qimg = QImage(scaled_copy.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
            else:
                scaled_copy = np.ascontiguousarray(scaled)
                qimg = QImage(scaled_copy.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
        
        pixmap = QPixmap.fromImage(qimg)
        self.image_label.setPixmap(pixmap)
        self.image_label.setMinimumSize(1, 1)
    
    def set_zoom(self, level: float):
        self.zoom_level = max(0.1, min(level, 4.0))
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(int(self.zoom_level * 100))
        self.zoom_slider.blockSignals(False)
        self.zoom_label.setText(f"{int(self.zoom_level * 100)}%")
        self.update_display()
    
    def on_zoom_slider_changed(self, value):
        self.set_zoom(value / 100.0)
    
    def zoom_in(self):
        new_zoom = min(self.zoom_level + 0.25, 4.0)
        self.set_zoom(new_zoom)
    
    def zoom_out(self):
        new_zoom = max(self.zoom_level - 0.25, 0.1)
        self.set_zoom(new_zoom)
    
    def fit_to_width(self):
        if self.current_image is None:
            return
        
        scroll_width = self.scroll_area.viewport().width()
        image_width = self.current_image.shape[1]
        
        if image_width > 0:
            self.set_zoom(scroll_width / image_width)
    
    def fit_to_height(self):
        if self.current_image is None:
            return
        
        scroll_height = self.scroll_area.viewport().height()
        image_height = self.current_image.shape[0]
        
        if image_height > 0:
            self.set_zoom(scroll_height / image_height)
    
    def clear(self):
        import gc
        self.current_image = None
        self.frame_count = 0
        self.image_label.clear()
        self.info_label.setText("No slitscan generated")
        self.set_zoom(1.0)
        gc.collect()
    
    def set_frame_count(self, count: int):
        self.frame_count = count
        if self.current_image is not None:
            self.update_display()
