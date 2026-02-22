from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QComboBox, QSpinBox, QDoubleSpinBox, QSlider, QCheckBox,
    QPushButton, QGroupBox, QTimeEdit
)
from PySide6.QtCore import Qt, Signal, QTimer, QTime, QSettings


class ScanControls(QWidget):
    params_changed = Signal(dict)
    generate_clicked = Signal()
    save_clicked = Signal()
    line_position_changed = Signal(int)
    line_width_changed = Signal(int, int)
    crop_changed = Signal(int, int)
    set_start_from_time = Signal()
    set_end_from_time = Signal()
    go_to_start_time = Signal()
    go_to_end_time = Signal()
    
    def __init__(self):
        super().__init__()
        self.video_loaded = False
        self.video_width = 0
        self.video_height = 0
        self.video_duration = 0.0
        self.settings = QSettings('Vid2Scan', 'Vid2Scan')
        self.setup_ui()
        self.setup_connections()
        self.setup_debounce()
        self.load_settings()
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        scroll_content = QWidget()
        form_layout = QFormLayout(scroll_content)
        
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(['horizontal', 'vertical'])
        form_layout.addRow('Direction:', self.direction_combo)
        
        self.line_position_slider = QSlider(Qt.Orientation.Horizontal)
        self.line_position_slider.setRange(0, 100)
        self.line_position_spinbox = QSpinBox()
        self.line_position_spinbox.setRange(0, 9999)
        
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(self.line_position_slider, 1)
        pos_layout.addWidget(self.line_position_spinbox)
        form_layout.addRow('Line Position:', pos_layout)
        
        line_width_group = QGroupBox('Line Width (px)')
        line_width_layout = QVBoxLayout()
        
        start_end_layout = QHBoxLayout()
        start_end_layout.addWidget(QLabel('Start:'))
        self.line_width_start_spinbox = QSpinBox()
        self.line_width_start_spinbox.setRange(1, 100)
        self.line_width_start_spinbox.setValue(1)
        start_end_layout.addWidget(self.line_width_start_spinbox)
        start_end_layout.addWidget(QLabel('End:'))
        self.line_width_end_spinbox = QSpinBox()
        self.line_width_end_spinbox.setRange(1, 100)
        self.line_width_end_spinbox.setValue(1)
        start_end_layout.addWidget(self.line_width_end_spinbox)
        line_width_layout.addLayout(start_end_layout)
        
        lerp_layout = QHBoxLayout()
        lerp_layout.addWidget(QLabel('Interpolation:'))
        self.lerp_type_combo = QComboBox()
        self.lerp_type_combo.addItems(['linear', 'ease-in', 'ease-out', 'ease-in-out'])
        lerp_layout.addWidget(self.lerp_type_combo)
        line_width_layout.addLayout(lerp_layout)
        
        blend_layout = QHBoxLayout()
        self.gaussian_blend_checkbox = QCheckBox()
        self.gaussian_blend_checkbox.setChecked(False)
        blend_layout.addWidget(self.gaussian_blend_checkbox)
        blend_layout.addWidget(QLabel('Blend (px):'))
        self.gaussian_blend_spinbox = QSpinBox()
        self.gaussian_blend_spinbox.setRange(1, 50)
        self.gaussian_blend_spinbox.setValue(5)
        self.gaussian_blend_spinbox.setEnabled(False)
        blend_layout.addWidget(self.gaussian_blend_spinbox)
        blend_layout.addStretch()
        line_width_layout.addLayout(blend_layout)
        
        line_width_group.setLayout(line_width_layout)
        form_layout.addRow(line_width_group)
        
        crop_group = QGroupBox('Vertical Crop (px)')
        crop_layout = QHBoxLayout()
        
        crop_layout.addWidget(QLabel('Top:'))
        self.crop_top_spinbox = QSpinBox()
        self.crop_top_spinbox.setRange(0, 9999)
        self.crop_top_spinbox.setValue(0)
        crop_layout.addWidget(self.crop_top_spinbox)
        
        crop_layout.addWidget(QLabel('Bottom:'))
        self.crop_bottom_spinbox = QSpinBox()
        self.crop_bottom_spinbox.setRange(0, 9999)
        self.crop_bottom_spinbox.setValue(0)
        crop_layout.addWidget(self.crop_bottom_spinbox)
        
        crop_group.setLayout(crop_layout)
        form_layout.addRow(crop_group)
        
        self.combine_mode_combo = QComboBox()
        self.combine_mode_combo.addItems(['average', 'stack'])
        form_layout.addRow('Combine Mode:', self.combine_mode_combo)
        
        self.reverse_stack_checkbox = QCheckBox()
        self.reverse_stack_checkbox.setChecked(False)
        self.reverse_stack_checkbox.setEnabled(False)
        form_layout.addRow('Reverse Stack:', self.reverse_stack_checkbox)
        
        stretch_group = QGroupBox('Stretch Factor')
        stretch_layout = QFormLayout()
        
        self.spatial_stretch_spinbox = QDoubleSpinBox()
        self.spatial_stretch_spinbox.setRange(0.1, 10.0)
        self.spatial_stretch_spinbox.setValue(1.0)
        self.spatial_stretch_spinbox.setSingleStep(0.1)
        stretch_layout.addRow('Spatial:', self.spatial_stretch_spinbox)
        
        stretch_group.setLayout(stretch_layout)
        form_layout.addRow(stretch_group)
        
        time_group = QGroupBox('Time Range')
        time_layout = QVBoxLayout()
        
        time_row = QHBoxLayout()
        time_row.addWidget(QLabel('Start:'))
        self.start_time_edit = QTimeEdit()
        self.start_time_edit.setDisplayFormat('HH:mm:ss.zzz')
        self.start_time_edit.setTime(QTime(0, 0, 0, 0))
        time_row.addWidget(self.start_time_edit, 1)
        self.set_start_button = QPushButton('Set')
        self.set_start_button.setFixedWidth(40)
        time_row.addWidget(self.set_start_button)
        self.go_start_button = QPushButton('Go')
        self.go_start_button.setFixedWidth(40)
        time_row.addWidget(self.go_start_button)
        time_layout.addLayout(time_row)
        
        time_row2 = QHBoxLayout()
        time_row2.addWidget(QLabel('End:'))
        self.end_time_edit = QTimeEdit()
        self.end_time_edit.setDisplayFormat('HH:mm:ss.zzz')
        self.end_time_edit.setTime(QTime(0, 0, 0, 0))
        time_row2.addWidget(self.end_time_edit, 1)
        self.set_end_button = QPushButton('Set')
        self.set_end_button.setFixedWidth(40)
        time_row2.addWidget(self.set_end_button)
        self.go_end_button = QPushButton('Go')
        self.go_end_button.setFixedWidth(40)
        time_row2.addWidget(self.go_end_button)
        time_layout.addLayout(time_row2)
        
        self.duration_label = QLabel('Duration: 0.00 s')
        time_layout.addWidget(self.duration_label)
        
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
        self.line_width_start_spinbox.valueChanged.connect(self.on_line_width_changed)
        self.line_width_end_spinbox.valueChanged.connect(self.on_line_width_changed)
        self.crop_top_spinbox.valueChanged.connect(self.on_crop_changed)
        self.crop_bottom_spinbox.valueChanged.connect(self.on_crop_changed)
        self.combine_mode_combo.currentTextChanged.connect(self.on_combine_mode_changed)
        self.reverse_stack_checkbox.stateChanged.connect(self.on_reverse_stack_changed)
        self.spatial_stretch_spinbox.valueChanged.connect(self.on_param_changed)
        self.start_time_edit.timeChanged.connect(self.on_time_changed)
        self.end_time_edit.timeChanged.connect(self.on_time_changed)
        self.frame_step_spinbox.valueChanged.connect(self.on_param_changed)
        self.output_scale_combo.currentTextChanged.connect(self.on_scale_combo_changed)
        self.custom_scale_spinbox.valueChanged.connect(self.on_param_changed)
        self.preview_quality_combo.currentTextChanged.connect(self.on_param_changed)
        self.lerp_type_combo.currentTextChanged.connect(self.on_param_changed)
        self.gaussian_blend_checkbox.stateChanged.connect(self.on_gaussian_blend_changed)
        self.gaussian_blend_spinbox.valueChanged.connect(self.on_param_changed)
        
        self.save_button.clicked.connect(self.save_clicked.emit)
        self.set_start_button.clicked.connect(self.set_start_from_time.emit)
        self.set_end_button.clicked.connect(self.set_end_from_time.emit)
        self.go_start_button.clicked.connect(self.go_to_start_time.emit)
        self.go_end_button.clicked.connect(self.go_to_end_time.emit)
    
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
            self.save_settings()
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
        self.save_settings()
    
    def update_position_range(self, direction):
        if direction == 'horizontal':
            max_pos = max(0, self.video_height - 1) if self.video_loaded else 100
            self.line_position_slider.setRange(0, max_pos)
            self.line_position_spinbox.setRange(0, max_pos)
        else:
            max_pos = max(0, self.video_width - 1) if self.video_loaded else 100
            self.line_position_slider.setRange(0, max_pos)
            self.line_position_spinbox.setRange(0, max_pos)
    
    def on_line_width_changed(self):
        self.line_width_changed.emit(
            self.line_width_start_spinbox.value(),
            self.line_width_end_spinbox.value()
        )
        self.save_settings()
    
    def on_param_changed(self):
        self.trigger_params_changed()
    
    def on_crop_changed(self):
        self.crop_changed.emit(
            self.crop_top_spinbox.value(),
            self.crop_bottom_spinbox.value()
        )
    
    def on_combine_mode_changed(self, mode: str):
        self.reverse_stack_checkbox.setEnabled(mode == 'stack')
        self.save_settings()
    
    def on_reverse_stack_changed(self):
        self.save_settings()
    
    def on_gaussian_blend_changed(self):
        self.gaussian_blend_spinbox.setEnabled(self.gaussian_blend_checkbox.isChecked())
        self.on_param_changed()
    
    def on_time_changed(self):
        start_msecs = self.start_time_edit.time().msecsSinceStartOfDay()
        end_msecs = self.end_time_edit.time().msecsSinceStartOfDay()
        duration = (end_msecs - start_msecs) / 1000.0
        self.duration_label.setText(f'Duration: {max(0.0, duration):.2f} s')
    
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
        
        self.crop_top_spinbox.setRange(0, height - 1)
        self.crop_bottom_spinbox.setRange(0, height - 1)
        
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
    
    def update_crop(self, crop_top: int, crop_bottom: int):
        self.crop_top_spinbox.blockSignals(True)
        self.crop_bottom_spinbox.blockSignals(True)
        self.crop_top_spinbox.setValue(crop_top)
        self.crop_bottom_spinbox.setValue(crop_bottom)
        self.crop_top_spinbox.blockSignals(False)
        self.crop_bottom_spinbox.blockSignals(False)
    
    def get_start_time(self) -> float:
        msecs = self.start_time_edit.time().msecsSinceStartOfDay()
        return msecs / 1000.0
    
    def get_end_time(self) -> float:
        msecs = self.end_time_edit.time().msecsSinceStartOfDay()
        return msecs / 1000.0
    
    def get_params(self) -> dict:
        direction = self.direction_combo.currentText()
        
        line_pos = self.line_position_spinbox.value()
        
        if direction == 'horizontal':
            max_pos = self.video_height - 1 if self.video_height > 0 else 0
        else:
            max_pos = self.video_width - 1 if self.video_width > 0 else 0
        
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
            'line_width_start': self.line_width_start_spinbox.value(),
            'line_width_end': self.line_width_end_spinbox.value(),
            'lerp_type': self.lerp_type_combo.currentText(),
            'crop_top': self.crop_top_spinbox.value(),
            'crop_bottom': self.crop_bottom_spinbox.value(),
            'combine_mode': self.combine_mode_combo.currentText(),
            'reverse_stack': self.reverse_stack_checkbox.isChecked(),
            'gaussian_blend': self.gaussian_blend_checkbox.isChecked(),
            'gaussian_blend_pixels': self.gaussian_blend_spinbox.value(),
            'start_time': start_time,
            'end_time': end_time,
            'frame_step': self.frame_step_spinbox.value(),
            'spatial_stretch': self.spatial_stretch_spinbox.value(),
            'output_scale': self.custom_scale_spinbox.value(),
            'quality': self.preview_quality_combo.currentText()
        }
    
    def validate_params(self) -> bool:
        params = self.get_params()
        
        if params['start_time'] >= params['end_time']:
            return False
        
        line_pos = params['line_pos']
        line_width = max(params['line_width_start'], params['line_width_end'])
        
        if params['direction'] == 'horizontal':
            max_pos = self.video_height if self.video_height > 0 else 1
        else:
            max_pos = self.video_width if self.video_width > 0 else 1
        
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
    
    def save_settings(self):
        self.settings.setValue('direction', self.direction_combo.currentText())
        self.settings.setValue('line_width_start', self.line_width_start_spinbox.value())
        self.settings.setValue('line_width_end', self.line_width_end_spinbox.value())
        self.settings.setValue('lerp_type', self.lerp_type_combo.currentText())
        self.settings.setValue('combine_mode', self.combine_mode_combo.currentText())
        self.settings.setValue('reverse_stack', self.reverse_stack_checkbox.isChecked())
        self.settings.setValue('spatial_stretch', self.spatial_stretch_spinbox.value())
        self.settings.setValue('frame_step', self.frame_step_spinbox.value())
        self.settings.setValue('output_scale_index', self.output_scale_combo.currentIndex())
        self.settings.setValue('custom_scale', self.custom_scale_spinbox.value())
        self.settings.setValue('preview_quality', self.preview_quality_combo.currentText())
        self.settings.setValue('gaussian_blend', self.gaussian_blend_checkbox.isChecked())
        self.settings.setValue('gaussian_blend_pixels', self.gaussian_blend_spinbox.value())
    
    def load_settings(self):
        direction = self.settings.value('direction', 'horizontal')
        if isinstance(direction, str):
            direction_index = self.direction_combo.findText(direction)
            if direction_index >= 0:
                self.direction_combo.setCurrentIndex(direction_index)
        
        line_width_start = self.settings.value('line_width_start', 1)
        if line_width_start is not None:
            self.line_width_start_spinbox.setValue(int(line_width_start))
        
        line_width_end = self.settings.value('line_width_end', 1)
        if line_width_end is not None:
            self.line_width_end_spinbox.setValue(int(line_width_end))
        
        lerp_type = self.settings.value('lerp_type', 'linear')
        if isinstance(lerp_type, str):
            lerp_index = self.lerp_type_combo.findText(lerp_type)
            if lerp_index >= 0:
                self.lerp_type_combo.setCurrentIndex(lerp_index)
        
        combine_mode = self.settings.value('combine_mode', 'average')
        if isinstance(combine_mode, str):
            combine_index = self.combine_mode_combo.findText(combine_mode)
            if combine_index >= 0:
                self.combine_mode_combo.setCurrentIndex(combine_index)
        
        reverse_stack = self.settings.value('reverse_stack', False)
        if reverse_stack is not None:
            self.reverse_stack_checkbox.setChecked(bool(reverse_stack))
        
        spatial_stretch = self.settings.value('spatial_stretch', 1.0)
        if spatial_stretch is not None:
            self.spatial_stretch_spinbox.setValue(float(spatial_stretch))
        
        frame_step = self.settings.value('frame_step', 1)
        if frame_step is not None:
            self.frame_step_spinbox.setValue(int(frame_step))
        
        output_scale_index = self.settings.value('output_scale_index', 0)
        if output_scale_index is not None:
            self.output_scale_combo.setCurrentIndex(int(output_scale_index))
        
        custom_scale = self.settings.value('custom_scale', 1.0)
        if custom_scale is not None:
            self.custom_scale_spinbox.setValue(float(custom_scale))
        
        preview_quality = self.settings.value('preview_quality', 'medium')
        if isinstance(preview_quality, str):
            quality_index = self.preview_quality_combo.findText(preview_quality)
            if quality_index >= 0:
                self.preview_quality_combo.setCurrentIndex(quality_index)
        
        gaussian_blend = self.settings.value('gaussian_blend', False)
        if gaussian_blend is not None:
            self.gaussian_blend_checkbox.setChecked(bool(gaussian_blend))
        
        gaussian_blend_pixels = self.settings.value('gaussian_blend_pixels', 5)
        if gaussian_blend_pixels is not None:
            self.gaussian_blend_spinbox.setValue(int(gaussian_blend_pixels))
