from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QImage, QWheelEvent, QMouseEvent
import numpy as np
import cv2


class SlitscanPreview(QWidget):
    def __init__(self):
        super().__init__()
        self.current_image = None
        self.frame_count = 0
        self.zoom_level = 1.0
        self.pan_offset = QPoint(0, 0)
        self.dragging = False
        self.last_mouse_pos = QPoint()
        self.min_zoom = 0.1
        self.max_zoom = 10.0
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
        self.image_label.setMouseTracking(True)
        
        self.scroll_area.setWidget(self.image_label)
        main_layout.addWidget(self.scroll_area, 1)
        
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        info_layout = QHBoxLayout(info_frame)
        
        self.info_label = QLabel("No slitscan generated")
        info_layout.addWidget(self.info_label, 1)
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(60)
        info_layout.addWidget(self.zoom_label)
        
        main_layout.addWidget(info_frame)
        
        controls_layout = QHBoxLayout()
        
        self.zoom_out_button = QPushButton("-")
        self.zoom_out_button.setFixedWidth(30)
        self.zoom_out_button.clicked.connect(self.zoom_out)
        controls_layout.addWidget(self.zoom_out_button)
        
        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setFixedWidth(30)
        self.zoom_in_button.clicked.connect(self.zoom_in)
        controls_layout.addWidget(self.zoom_in_button)
        
        controls_layout.addWidget(QLabel("Scroll to zoom, drag to pan"))
        controls_layout.addStretch()
        
        self.fit_width_button = QPushButton("Fit Width")
        self.fit_width_button.clicked.connect(self.fit_to_width)
        controls_layout.addWidget(self.fit_width_button)
        
        self.fit_height_button = QPushButton("Fit Height")
        self.fit_height_button.clicked.connect(self.fit_to_height)
        controls_layout.addWidget(self.fit_height_button)
        
        self.reset_view_button = QPushButton("Reset")
        self.reset_view_button.clicked.connect(self.reset_view)
        controls_layout.addWidget(self.reset_view_button)
        
        main_layout.addLayout(controls_layout)
        
        self.setMouseTracking(True)
        self.scroll_area.setMouseTracking(True)
        self.image_label.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        if obj == self.image_label:
            if event.type() == QWheelEvent.Type.Wheel:
                self.handle_wheel_event(event)
                return True
            elif event.type() == QMouseEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.dragging = True
                    self.last_mouse_pos = event.position().toPoint()
                    self.image_label.setCursor(Qt.CursorShape.ClosedHandCursor)
                return True
            elif event.type() == QMouseEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.dragging = False
                    self.image_label.setCursor(Qt.CursorShape.OpenHandCursor)
                return True
            elif event.type() == QMouseEvent.Type.MouseMove:
                if self.dragging:
                    delta = event.position().toPoint() - self.last_mouse_pos
                    self.scroll_area.horizontalScrollBar().setValue(
                        self.scroll_area.horizontalScrollBar().value() - delta.x()
                    )
                    self.scroll_area.verticalScrollBar().setValue(
                        self.scroll_area.verticalScrollBar().value() - delta.y()
                    )
                    self.last_mouse_pos = event.position().toPoint()
                return True
        return super().eventFilter(obj, event)
    
    def handle_wheel_event(self, event):
        delta = event.angleDelta().y()
        factor = 1.1 if delta > 0 else 0.9
        
        new_zoom = self.zoom_level * factor
        new_zoom = max(self.min_zoom, min(new_zoom, self.max_zoom))
        
        self.set_zoom(new_zoom)
    
    def wheelEvent(self, event):
        self.handle_wheel_event(event)
    
    def set_image(self, image: np.ndarray):
        self.current_image = image
        self.update_display()
        if self.image_label.pixmap():
            self.image_label.setCursor(Qt.CursorShape.OpenHandCursor)
    
    def update_display(self):
        if self.current_image is None:
            self.image_label.clear()
            self.info_label.setText("No slitscan generated")
            return
        
        h, w = self.current_image.shape[:2]
        
        self.info_label.setText(f"Size: {w} x {h} px | Frames: {self.frame_count}")
        
        new_w = max(1, int(w * self.zoom_level))
        new_h = max(1, int(h * self.zoom_level))
        
        if self.zoom_level != 1.0:
            scaled = cv2.resize(self.current_image, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
        else:
            scaled = self.current_image
        
        if len(scaled.shape) == 2:
            h_s, w_s = scaled.shape
            bytes_per_line = w_s
            scaled_copy = np.ascontiguousarray(scaled)
            qimg = QImage(scaled_copy.data, w_s, h_s, bytes_per_line, QImage.Format.Format_Grayscale8).copy()
        else:
            h_s, w_s, ch = scaled.shape
            bytes_per_line = ch * w_s
            if ch == 3:
                scaled_rgb = cv2.cvtColor(scaled, cv2.COLOR_BGR2RGB)
                scaled_copy = np.ascontiguousarray(scaled_rgb)
                qimg = QImage(scaled_copy.data, w_s, h_s, bytes_per_line, QImage.Format.Format_RGB888).copy()
            else:
                scaled_copy = np.ascontiguousarray(scaled)
                qimg = QImage(scaled_copy.data, w_s, h_s, bytes_per_line, QImage.Format.Format_RGB888).copy()
        
        pixmap = QPixmap.fromImage(qimg)
        self.image_label.setPixmap(pixmap)
        self.image_label.setMinimumSize(1, 1)
        self.zoom_label.setText(f"{int(self.zoom_level * 100)}%")
    
    def set_zoom(self, level: float):
        self.zoom_level = max(self.min_zoom, min(level, self.max_zoom))
        self.update_display()
    
    def zoom_in(self):
        new_zoom = min(self.zoom_level * 1.25, self.max_zoom)
        self.set_zoom(new_zoom)
    
    def zoom_out(self):
        new_zoom = max(self.zoom_level / 1.25, self.min_zoom)
        self.set_zoom(new_zoom)
    
    def fit_to_width(self):
        if self.current_image is None:
            return
        
        scroll_width = self.scroll_area.viewport().width() - 20
        image_width = self.current_image.shape[1]
        
        if image_width > 0:
            self.set_zoom(scroll_width / image_width)
    
    def fit_to_height(self):
        if self.current_image is None:
            return
        
        scroll_height = self.scroll_area.viewport().height() - 20
        image_height = self.current_image.shape[0]
        
        if image_height > 0:
            self.set_zoom(scroll_height / image_height)
    
    def reset_view(self):
        self.set_zoom(1.0)
        self.scroll_area.horizontalScrollBar().setValue(0)
        self.scroll_area.verticalScrollBar().setValue(0)
    
    def clear(self):
        import gc
        self.current_image = None
        self.frame_count = 0
        self.image_label.clear()
        self.info_label.setText("No slitscan generated")
        self.set_zoom(1.0)
        self.image_label.setCursor(Qt.CursorShape.ArrowCursor)
        gc.collect()
    
    def set_frame_count(self, count: int):
        self.frame_count = count
        if self.current_image is not None:
            self.update_display()
