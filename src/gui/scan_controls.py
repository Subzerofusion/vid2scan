from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QComboBox, QSpinBox, QDoubleSpinBox, QSlider, QCheckBox,
    QPushButton, QGroupBox, QTimeEdit
)
from PySide6.QtCore import Qt, Signal, QTimer, QTime


class ScanControls(QWidget):
    params_changed = Signal(dict)
    generate_clicked = Signal()
    save_clicked = Signal()
    line_position_changed = Signal(int)
    line_width_changed = Signal(int)
    set_start_from_time = Signal()
    set_end_from_time = Signal()
    
    def __init__(self):
        super().__init__()
        self.video_loaded = False
        self.video_width = 0
        self.video_height = 0
        self.video_duration = 0.0
        self.setup_ui()
        self.setup_connections()
        self.setup_debounce()
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        scroll_content = QWidget()
        form_layout = QFormLayout(scroll_content)
        
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(['horizontal', 'vertical'])
        form_layout.addRow('Direction:', self.direction_combo)
        
        self.line_position_slider = QSlider(Qt.Horizontal)
        self.line_position_slider.setRange(0, 100)
        self.line_position_spinbox = QSpinBox()
        self.line_position_spinbox.setRange(0, 9999)
        
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(self.line_position_slider, 1)
        pos_layout.addWidget(self.line_position_spinbox)
        form_layout.addRow('Line Position:', pos_layout)
        
        self.line_width_spinbox = QSpinBox()
        self.line_width_spinbox.setRange(1, 100)
        self.line_width_spinbox.setValue(1)
        form_layout.addRow('Line Width (px):', self.line_width_spinbox)
        
        self.combine_mode_combo = QComboBox()
        self.combine_mode_combo.addItems(['average', 'stack'])
        form_layout.addRow('Combine Mode:', self.combine_mode_combo)
        
        self.reverse_stack_checkbox = QCheckBox()
        self.reverse_stack_checkbox.setChecked(False)
        self.reverse_stack_checkbox.setEnabled(False)
        form_layout.addRow('Reverse Stack:', self.reverse_stack_checkbox)
        
        stretch_group = QGroupBox('Stretch Factors')
        stretch_layout = QFormLayout()
        
        self.temporal_stretch_spinbox = QDoubleSpinBox()
        self.temporal_stretch_spinbox.setRange(0.1, 100.0)
        self.temporal_stretch_spinbox.setValue(1.0)
        self.temporal_stretch_spinbox.setSingleStep(0.1)
        stretch_layout.addRow('Temporal:', self.temporal_stretch_spinbox)
        
        self.spatial_stretch_spinbox = QDoubleSpinBox()
        self.spatial_stretch_spinbox.setRange(0.1, 10.0)
        self.spatial_stretch_spinbox.setValue(1.0)
        self.spatial_stretch_spinbox.setSingleStep(0.1)
        stretch_layout.addRow('Spatial:', self.spatial_stretch_spinbox)
        
        stretch_group.setLayout(stretch_layout)
        form_layout.addRow(stretch_group)
        
        time_group = QGroupBox('Time Range')
        time_layout = QFormLayout()
        
        self.start_time_edit = QTimeEdit()
        self.start_time_edit.setDisplayFormat('HH:mm:ss.zzz')
        self.start_time_edit.setTime(QTime(0, 0, 0, 0))
        start_row = QHBoxLayout()
        start_row.addWidget(self.start_time_edit, 1)
        self.set_start_button = QPushButton('Set')
        self.set_start_button.setFixedWidth(40)
        start_row.addWidget(self.set_start_button)
        time_layout.addRow('Start:', start_row)
        
        self.end_time_edit = QTimeEdit()
        self.end_time_edit.setDisplayFormat('HH:mm:ss.zzz')
        self.end_time_edit.setTime(QTime(0, 0, 0, 0))
        end_row = QHBoxLayout()
        end_row.addWidget(self.end_time_edit, 1)
        self.set_end_button = QPushButton('Set')
        self.set_end_button.setFixedWidth(40)
        end_row.addWidget(self.set_end_button)
        time_layout.addRow('End:', end_row)
        
        self.duration_label = QLabel('0.00 s')
        time_layout.addRow('Duration:', self.duration_label)
        
        time_group.setLayout(time_layout)
        form_layout.addRow(time_group)
        
        self.frame_step_spinbox = QSpinBox()
        self.frame_step_spinbox.setRange(1, 1000)
        self.frame_step_spinbox.setValue(1)
        form_layout.addRow('Frame Step:', self.frame_step_spinbox)
        
        self.output_scale_combo = QComboBox()
        self.output_scale_combo.addItems(['100%', '75%', '50%', '25%', 'Custom'])
        form_layout.addRow('Output Scale:', self.output_scale_combo)
        
        self.custom_scale_spinbox = QDoubleSpinBox()
        self.custom_scale_spinbox.setRange(0.01, 2.0)
        self.custom_scale_spinbox.setSingleStep(0.05)
        self.custom_scale_spinbox.setValue(1.0)
        self.custom_scale_spinbox.setEnabled(False)
        form_layout.addRow('Custom Scale:', self.custom_scale_spinbox)
        
        preview_group = QGroupBox('Preview')
        preview_layout = QFormLayout()
        
        self.show_frame_preview = QCheckBox()
        self.show_frame_preview.setChecked(True)
        preview_layout.addRow('Show Frame:', self.show_frame_preview)
        
        self.show_slitscan_preview = QCheckBox()
        self.show_slitscan_preview.setChecked(True)
        preview_layout.addRow('Show Slitscan:', self.show_slitscan_preview)
        
        self.preview_quality_combo = QComboBox()
        self.preview_quality_combo.addItems(['low', 'medium', 'high'])
        preview_layout.addRow('Quality:', self.preview_quality_combo)
        
        preview_group.setLayout(preview_layout)
        form_layout.addRow(preview_group)
        
        self.save_button = QPushButton('Save Image')
        self.save_button.setEnabled(False)
        form_layout.addRow(self.save_button)
        
        main_layout.addWidget(scroll_content)
        
        self.setEnabled(False)
    
    def setup_connections(self):
        self.direction_combo.currentTextChanged.connect(self.on_direction_changed)
        self.line_position_slider.valueChanged.connect(self.on_position_slider_changed)
        self.line_position_spinbox.valueChanged.connect(self.on_position_spinbox_changed)
        self.line_width_spinbox.valueChanged.connect(self.on_param_changed)
        self.combine_mode_combo.currentTextChanged.connect(self.on_combine_mode_changed)
        self.reverse_stack_checkbox.stateChanged.connect(self.on_param_changed)
        self.temporal_stretch_spinbox.valueChanged.connect(self.on_param_changed)
        self.spatial_stretch_spinbox.valueChanged.connect(self.on_param_changed)
        self.start_time_edit.timeChanged.connect(self.on_time_changed)
        self.end_time_edit.timeChanged.connect(self.on_time_changed)
        self.frame_step_spinbox.valueChanged.connect(self.on_param_changed)
        self.output_scale_combo.currentTextChanged.connect(self.on_scale_combo_changed)
        self.custom_scale_spinbox.valueChanged.connect(self.on_param_changed)
        self.preview_quality_combo.currentTextChanged.connect(self.on_param_changed)
        
        self.save_button.clicked.connect(self.save_clicked.emit)
        self.set_start_button.clicked.connect(self.set_start_from_time.emit)
        self.set_end_button.clicked.connect(self.set_end_from_time.emit)
    
    def setup_debounce(self):
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(300)
        self.debounce_timer.timeout.connect(self.emit_params_changed)
        self.pending_params = False
    
    def trigger_params_changed(self):
        self.pending_params = True
        self.debounce_timer.start()
    
    def emit_params_changed(self):
        if self.pending_params:
            self.pending_params = False
            self.params_changed.emit(self.get_params())
    
    def on_position_slider_changed(self, value):
        self.line_position_spinbox.blockSignals(True)
        self.line_position_spinbox.setValue(value)
        self.line_position_spinbox.blockSignals(False)
        self.line_position_changed.emit(value)
    
    def on_position_spinbox_changed(self, value):
        self.line_position_slider.blockSignals(True)
        self.line_position_slider.setValue(value)
        self.line_position_slider.blockSignals(False)
        self.line_position_changed.emit(value)
    
    def stop_debounce(self):
        if hasattr(self, 'debounce_timer') and self.debounce_timer.isActive():
            self.debounce_timer.stop()
    
    def __del__(self):
        self.stop_debounce()
    
    def on_direction_changed(self, direction):
        self.update_position_range(direction)
    
    def update_position_range(self, direction):
        if direction == 'horizontal':
            max_pos = max(0, self.video_height - 1) if self.video_loaded else 100
            self.line_position_slider.setRange(0, max_pos)
            self.line_position_spinbox.setRange(0, max_pos)
        else:
            max_pos = max(0, self.video_width - 1) if self.video_loaded else 100
            self.line_position_slider.setRange(0, max_pos)
            self.line_position_spinbox.setRange(0, max_pos)
    
    def on_param_changed(self):
        self.line_width_changed.emit(self.line_width_spinbox.value())
    
    def on_combine_mode_changed(self, mode: str):
        self.reverse_stack_checkbox.setEnabled(mode == 'stack')
        self.on_param_changed()
    
    def on_time_changed(self):
        start_msecs = self.start_time_edit.time().msecsSinceStartOfDay()
        end_msecs = self.end_time_edit.time().msecsSinceStartOfDay()
        duration = (end_msecs - start_msecs) / 1000.0
        self.duration_label.setText(f'{max(0.0, duration):.2f} s')
    
    def on_scale_combo_changed(self, text):
        if text == 'Custom':
            self.custom_scale_spinbox.setEnabled(True)
        else:
            self.custom_scale_spinbox.setEnabled(False)
            if text == '100%':
                self.custom_scale_spinbox.setValue(1.0)
            elif text == '75%':
                self.custom_scale_spinbox.setValue(0.75)
            elif text == '50%':
                self.custom_scale_spinbox.setValue(0.5)
            elif text == '25%':
                self.custom_scale_spinbox.setValue(0.25)
    
    def set_video_properties(self, fps: float, width: int, height: int, duration: float):
        self.video_loaded = True
        self.video_width = width
        self.video_height = height
        self.video_duration = duration
        
        self.line_position_slider.setRange(0, height - 1)
        self.line_position_spinbox.setRange(0, height - 1)
        self.line_position_spinbox.setValue(height // 2)
        self.line_position_slider.setValue(height // 2)
        
        max_msecs = int(duration * 1000)
        self.start_time_edit.setTimeRange(QTime(0, 0), QTime.fromMSecsSinceStartOfDay(max_msecs))
        self.end_time_edit.setTimeRange(QTime(0, 0), QTime.fromMSecsSinceStartOfDay(max_msecs))
        self.end_time_edit.setTime(QTime.fromMSecsSinceStartOfDay(max_msecs))
        
        self.on_time_changed()
        
        self.setEnabled(True)
    
    def update_line_position(self, position: int):
        self.line_position_slider.blockSignals(True)
        self.line_position_spinbox.blockSignals(True)
        self.line_position_slider.setValue(position)
        self.line_position_spinbox.setValue(position)
        self.line_position_slider.blockSignals(False)
        self.line_position_spinbox.blockSignals(False)
    
    def get_params(self) -> dict:
        direction = self.direction_combo.currentText()
        
        line_pos = self.line_position_spinbox.value()
        
        if direction == 'horizontal':
            max_pos = self.video_height - 1
        else:
            max_pos = self.video_width - 1
        
        line_pos = max(0, min(line_pos, max_pos))
        
        start_msecs = self.start_time_edit.time().msecsSinceStartOfDay()
        end_msecs = self.end_time_edit.time().msecsSinceStartOfDay()
        
        start_time = start_msecs / 1000.0
        end_time = end_msecs / 1000.0
        
        if start_time > end_time:
            start_time, end_time = end_time, start_time
        
        return {
            'direction': direction,
            'line_pos': line_pos,
            'line_width': self.line_width_spinbox.value(),
            'combine_mode': self.combine_mode_combo.currentText(),
            'reverse_stack': self.reverse_stack_checkbox.isChecked(),
            'start_time': start_time,
            'end_time': end_time,
            'frame_step': self.frame_step_spinbox.value(),
            'temporal_stretch': self.temporal_stretch_spinbox.value(),
            'spatial_stretch': self.spatial_stretch_spinbox.value(),
            'output_scale': self.custom_scale_spinbox.value(),
            'quality': self.preview_quality_combo.currentText()
        }
    
    def validate_params(self) -> bool:
        params = self.get_params()
        
        if params['start_time'] >= params['end_time']:
            return False
        
        line_pos = params['line_pos']
        line_width = params['line_width']
        
        if params['direction'] == 'horizontal':
            max_pos = self.video_height
        else:
            max_pos = self.video_width
        
        if line_pos + line_width > max_pos:
            return False
        
        return True
    
    def enable_save_button(self):
        self.save_button.setEnabled(True)
    
    def disable_save_button(self):
        self.save_button.setEnabled(False)
    
    def set_start_time(self, time_sec: float):
        msecs = int(time_sec * 1000)
        self.start_time_edit.setTime(QTime.fromMSecsSinceStartOfDay(msecs))
    
    def set_end_time(self, time_sec: float):
        msecs = int(time_sec * 1000)
        self.end_time_edit.setTime(QTime.fromMSecsSinceStartOfDay(msecs))
