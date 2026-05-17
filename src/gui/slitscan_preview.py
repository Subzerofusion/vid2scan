from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame
from PySide6.QtCore import Qt, QPoint, QEvent
from PySide6.QtGui import QPixmap, QImage, QWheelEvent, QMouseEvent, QCursor
import numpy as np
import cv2


class SlitscanPreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_image = None
        self.frame_count = 0
        self.zoom_level = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        self.dragging = False
        self.last_mouse_pos = QPoint()
        self.pixmap = None
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def set_image(self, image: np.ndarray):
        self.current_image = image.copy() if image is not None else None
        self.update_pixmap()
        if self.pixmap:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
    
    def update_pixmap(self):
        if self.current_image is None:
            self.pixmap = None
            self.update()
            return
        
        h, w = self.current_image.shape[:2]
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
        
        self.pixmap = QPixmap.fromImage(qimg)
        self.setFixedSize(new_w, new_h)
        self.update()
    
    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.pixmap is None:
            painter.fillRect(self.rect(), QColor(30, 30, 30))
            return
        
        x = (self.width() - self.pixmap.width()) // 2
        y = (self.height() - self.pixmap.height()) // 2
        painter.drawPixmap(x, y, self.pixmap)
    
    def wheelEvent(self, event):
        if self.current_image is None or self.pixmap is None:
            return
        
        delta = event.angleDelta().y()
        factor = 1.1 if delta > 0 else 0.9
        
        old_zoom = self.zoom_level
        new_zoom = old_zoom * factor
        new_zoom = max(self.min_zoom, min(new_zoom, self.max_zoom))
        
        if new_zoom == old_zoom:
            return
        
        scroll_parent = self.parent()
        while scroll_parent and not isinstance(scroll_parent, QScrollArea):
            scroll_parent = scroll_parent.parent()
        
        if not scroll_parent:
            self.set_zoom(new_zoom)
            return
        
        viewport = scroll_parent.viewport()
        cursor_pos_viewport = viewport.mapFromGlobal(event.globalPosition().toPoint())
        
        h_bar = scroll_parent.horizontalScrollBar()
        v_bar = scroll_parent.verticalScrollBar()
        
        old_scroll_x = h_bar.value()
        old_scroll_y = v_bar.value()
        
        logical_x = (old_scroll_x + cursor_pos_viewport.x()) / max(old_zoom, 1e-6)
        logical_y = (old_scroll_y + cursor_pos_viewport.y()) / max(old_zoom, 1e-6)
        
        self.set_zoom(new_zoom)
        
        new_scroll_x = int(logical_x * new_zoom - cursor_pos_viewport.x())
        new_scroll_y = int(logical_y * new_zoom - cursor_pos_viewport.y())
        
        h_bar.setValue(max(h_bar.minimum(), min(new_scroll_x, h_bar.maximum())))
        v_bar.setValue(max(v_bar.minimum(), min(new_scroll_y, v_bar.maximum())))
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.pixmap is not None:
            self.dragging = True
            self.last_mouse_pos = event.globalPosition().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
    
    def mouseMoveEvent(self, event):
        if self.dragging:
            current_pos = event.globalPosition().toPoint()
            delta = current_pos - self.last_mouse_pos
            
            scroll_parent = self.parent()
            while scroll_parent and not isinstance(scroll_parent, QScrollArea):
                scroll_parent = scroll_parent.parent()
            
            if scroll_parent:
                h_bar = scroll_parent.horizontalScrollBar()
                v_bar = scroll_parent.verticalScrollBar()
                h_bar.setValue(h_bar.value() - delta.x())
                v_bar.setValue(v_bar.value() - delta.y())
            
            self.last_mouse_pos = current_pos
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            if self.pixmap is not None:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def set_zoom(self, level: float):
        self.zoom_level = max(self.min_zoom, min(level, self.max_zoom))
        self.update_pixmap()
    
    def clear(self):
        self.current_image = None
        self.pixmap = None
        self.frame_count = 0
        self.zoom_level = 1.0
        self.setMinimumSize(200, 200)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()


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
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.image_widget = SlitscanPreviewWidget()
        self.scroll_area.setWidget(self.image_widget)
        main_layout.addWidget(self.scroll_area, 1)
        
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        info_layout = QHBoxLayout(info_frame)
        
        self.info_label = QLabel("No slitscan generated")
        info_layout.addWidget(self.info_label, 1)
        
        info_layout.addWidget(QLabel("|"))
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(60)
        info_layout.addWidget(self.zoom_label)
        
        info_layout.addWidget(QLabel("|"))
        
        self.fit_width_button = QPushButton("Fit Width")
        self.fit_width_button.clicked.connect(self.fit_to_width)
        info_layout.addWidget(self.fit_width_button)
        
        self.fit_height_button = QPushButton("Fit Height")
        self.fit_height_button.clicked.connect(self.fit_to_height)
        info_layout.addWidget(self.fit_height_button)
        
        self.reset_view_button = QPushButton("Reset")
        self.reset_view_button.clicked.connect(self.reset_view)
        info_layout.addWidget(self.reset_view_button)
        
        main_layout.addWidget(info_frame)
    
    def set_image(self, image: np.ndarray):
        self.current_image = image.copy() if image is not None else None
        self.image_widget.set_image(self.current_image)
        self.update_info()
    
    def update_info(self):
        if self.current_image is None:
            self.info_label.setText("No slitscan generated")
            return
        
        h, w = self.current_image.shape[:2]
        self.info_label.setText(f"Size: {w} x {h} px | Frames: {self.frame_count}")
        self.zoom_label.setText(f"{int(self.image_widget.zoom_level * 100)}%")
    
    def set_zoom(self, level: float):
        self.image_widget.set_zoom(level)
        self.zoom_level = level
        self.zoom_label.setText(f"{int(level * 100)}%")
    
    def zoom_in(self):
        new_zoom = min(self.image_widget.zoom_level * 1.25, self.image_widget.max_zoom)
        self.set_zoom(new_zoom)
    
    def zoom_out(self):
        new_zoom = max(self.image_widget.zoom_level / 1.25, self.image_widget.min_zoom)
        self.set_zoom(new_zoom)
    
    def fit_to_width(self):
        if self.current_image is None:
            return
        
        viewport_width = self.scroll_area.viewport().width()
        image_width = self.current_image.shape[1]
        
        if image_width > 0 and viewport_width > 0:
            self.set_zoom(viewport_width / image_width)
    
    def fit_to_height(self):
        if self.current_image is None:
            return
        
        viewport_height = self.scroll_area.viewport().height()
        image_height = self.current_image.shape[0]
        
        if image_height > 0 and viewport_height > 0:
            self.set_zoom(viewport_height / image_height)
    
    def reset_view(self):
        self.set_zoom(1.0)
        self.scroll_area.horizontalScrollBar().setValue(0)
        self.scroll_area.verticalScrollBar().setValue(0)
    
    def clear(self):
        import gc
        self.current_image = None
        self.frame_count = 0
        self.image_widget.clear()
        self.info_label.setText("No slitscan generated")
        self.set_zoom(1.0)
        gc.collect()
    
    def set_frame_count(self, count: int):
        self.frame_count = count
        self.update_info()
