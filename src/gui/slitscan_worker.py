from PySide6.QtCore import QObject, Signal
from typing import Optional, Dict, Any
import numpy as np
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


class SlitscanWorker(QObject):
    progress_updated = Signal(int)
    finished = Signal(object, str)
    error = Signal(str)
    canceled = Signal(object, str)
    
    def __init__(self, video_processor, params: Dict[str, Any], operation_type: str, save_path: Optional[str] = None):
        super().__init__()
        self.video_processor = video_processor
        self.params = params
        self.operation_type = operation_type
        self.save_path = save_path
        self.result: Optional[np.ndarray] = None
        self._is_canceled = False
    
    def cancel(self):
        self._is_canceled = True
        self.video_processor.cancel()
    
    def run(self):
        try:
            self._check_cancel()
            
            if self.operation_type == 'preview':
                self._run_preview()
            elif self.operation_type == 'full_scan':
                self._run_full_scan()
            elif self.operation_type == 'save_image':
                self._run_save_image()
            else:
                error_msg = f"Unknown operation type: {self.operation_type}"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
        except CancelException:
            logger.info(f"Operation {self.operation_type} canceled by user")
            self.canceled.emit(self.result, self.operation_type)
            self.finished.emit(self.result, self.operation_type)
        except Exception as e:
            error_msg = f"Error in {self.operation_type}: {str(e)}"
            logger.error(error_msg)
            self.error.emit(str(e))
            self.finished.emit(None, self.operation_type)
    
    def _check_cancel(self):
        if self._is_canceled:
            raise CancelException()
    
    def _progress_callback(self, percent: float) -> bool:
        self.progress_updated.emit(int(percent))
        self._check_cancel()
        return False
    
    def _run_preview(self):
        direction = self.params['direction']
        
        if direction == 'horizontal':
            self.result = self.video_processor.preview_scan(
                direction,
                progress_callback=self._progress_callback,
                **{k: v for k, v in self.params.items() if k != 'direction'}
            )
        else:
            self.result = self.video_processor.preview_scan(
                direction,
                progress_callback=self._progress_callback,
                **{k: v for k, v in self.params.items() if k != 'direction'}
            )
        
        self.finished.emit(self.result, self.operation_type)
    
    def _run_full_scan(self):
        direction = self.params['direction']
        
        # Map parameter names to match what extraction methods expect
        extract_params = {
            'line_y': self.params['line_pos'] if direction == 'horizontal' else 0,
            'line_x': self.params['line_pos'] if direction == 'vertical' else 0,
            'line_width': self.params['line_width'],
            'combine_mode': self.params['combine_mode'],
            'start_time': self.params['start_time'],
            'end_time': self.params['end_time'],
            'frame_step': self.params['frame_step'],
            'temporal_stretch': self.params['temporal_stretch'],
            'spatial_stretch': self.params['spatial_stretch'],
            'output_scale': self.params['output_scale']
        }
        
        if direction == 'horizontal':
            self.result = self.video_processor.extract_horizontal_scan(
                progress_callback=self._progress_callback,
                **extract_params
            )
        else:
            self.result = self.video_processor.extract_vertical_scan(
                progress_callback=self._progress_callback,
                **extract_params
            )
        
        self.finished.emit(self.result, self.operation_type)
    
    def _run_save_image(self):
        from pathlib import Path
        from PIL import Image
        
        image = self.params['image']
        save_path = self.save_path
        
        # Emit progress at 0%
        self.progress_updated.emit(0)
        self._check_cancel()
        
        try:
            # Save image
            image_pil = Image.fromarray(image)
            
            # Emit progress at 50%
            self.progress_updated.emit(50)
            self._check_cancel()
            
            image_pil.save(save_path, quality=95)
            
            # Emit progress at 100%
            self.progress_updated.emit(100)
            self._check_cancel()
            
            self.result = image
            self.finished.emit(self.result, self.operation_type)
            logger.info(f"Image saved successfully to {save_path}")
        except Exception as e:
            error_msg = f"Failed to save image to {save_path}: {str(e)}"
            logger.error(error_msg)
            raise


class CancelException(Exception):
    pass
