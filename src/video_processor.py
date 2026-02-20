import cv2
import numpy as np
import logging
import os
from typing import Optional, Callable

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'error.log')
if os.path.exists(log_path):
    os.remove(log_path)
file_handler = logging.FileHandler(log_path)
file_handler.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.ERROR)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


class VideoProcessor:
    def __init__(self):
        self.video_path = None
        self.cap = None
        self.fps = None
        self.total_frames = None
        self.width = None
        self.height = None
        self.duration = None
        self._cancel_requested = False
    
    def load_video(self, path: str) -> bool:
        self.video_path = path
        try:
            self.cap = cv2.VideoCapture(path)
            
            if not self.cap.isOpened():
                logger.error(f"Failed to open video file: {path}")
                self.close()
                return False
            
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.duration = self.total_frames / self.fps if self.fps > 0 else 0
            
            return True
        except Exception as e:
            logger.error(f"Error loading video {path}: {str(e)}")
            self.close()
            return False
    
    def close(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.video_path = None
        self.fps = None
        self.total_frames = None
        self.width = None
        self.height = None
        self.duration = None
        self._cancel_requested = False
    
    def cancel(self):
        self._cancel_requested = True
    
    def is_canceled(self) -> bool:
        return self._cancel_requested
    
    def reset_cancel(self):
        self._cancel_requested = False
    
    def get_frame_at_time(self, time_sec: float) -> Optional[np.ndarray]:
        if self.cap is None or self.fps == 0:
            return None
        
        frame_number = int(time_sec * self.fps)
        frame_number = max(0, min(frame_number, self.total_frames - 1))
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.cap.read()
        
        if ret:
            return frame
        return None
    
    def extract_horizontal_scan(
        self,
        line_y: int,
        line_width: int,
        combine_mode: str,
        start_time: float,
        end_time: float,
        frame_step: int,
        temporal_stretch: float,
        spatial_stretch: float,
        output_scale: float,
        reverse_stack: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> Optional[np.ndarray]:
        if self.cap is None:
            logger.error("Video not loaded")
            return None
        
        self.reset_cancel()
        
        start_frame = int(start_time * self.fps)
        end_frame = int(end_time * self.fps)
        start_frame = max(0, start_frame)
        end_frame = min(self.total_frames, end_frame)
        
        if start_frame >= end_frame:
            logger.error(f"Invalid time range: start={start_time}, end={end_time}")
            return None
        
        num_output_rows = (end_frame - start_frame) // frame_step
        if num_output_rows == 0:
            logger.warning("No frames to process")
            return None
        
        line_y_clamped = max(0, min(line_y, self.height - 1))
        actual_line_width = min(line_width, self.height - line_y_clamped)
        actual_line_width = max(1, actual_line_width)
        
        if combine_mode == 'stack':
            slice_height = actual_line_width
        else:
            slice_height = 1
        
        output_width = self.width
        output_height = num_output_rows * slice_height
        
        if spatial_stretch != 1.0:
            output_width = max(1, int(output_width * spatial_stretch))
        
        buffer = np.zeros((output_height, output_width, 3), dtype=np.uint8)
        
        processed_slices = 0
        
        try:
            for frame_idx in range(start_frame, end_frame, frame_step):
                if self.is_canceled():
                    if processed_slices > 0:
                        return buffer[:processed_slices * slice_height]
                    return None
                
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = self.cap.read()
                
                if not ret:
                    logger.warning(f"Failed to read frame {frame_idx}")
                    continue
                
                line_end = min(line_y_clamped + actual_line_width, self.height)
                
                if combine_mode == 'average' and actual_line_width > 1:
                    slice_rows = line_end - line_y_clamped
                    if slice_rows > 1:
                        slice_data = np.mean(frame[line_y_clamped:line_end, :], axis=0)
                        slice_data = slice_data.astype(np.uint8)
                        slice_data = slice_data.reshape(1, -1, 3)
                    else:
                        slice_data = frame[line_y_clamped:line_end, :].copy()
                else:
                    slice_data = frame[line_y_clamped:line_end, :].copy()
                    if reverse_stack and slice_data.shape[0] > 1:
                        slice_data = np.flip(slice_data, axis=0)
                
                if spatial_stretch != 1.0:
                    new_slice_height = slice_data.shape[0]
                    slice_data = cv2.resize(
                        slice_data,
                        (output_width, new_slice_height),
                        interpolation=cv2.INTER_LINEAR
                    )
                
                row_start = processed_slices * slice_height
                row_end = row_start + slice_data.shape[0]
                
                if row_end <= output_height:
                    buffer[row_start:row_end, :] = slice_data
                    processed_slices += 1
                
                if progress_callback and processed_slices % 10 == 0:
                    progress = processed_slices / num_output_rows * 100
                    if progress_callback(progress):
                        return None
            
            if processed_slices == 0:
                logger.warning("No frames extracted")
                return None
            
            result = buffer[:processed_slices * slice_height]
            
            if temporal_stretch != 1.0:
                new_height = max(1, int(result.shape[0] * temporal_stretch))
                result = cv2.resize(result, (result.shape[1], new_height), interpolation=cv2.INTER_LINEAR)
            
            if output_scale != 1.0:
                new_height = max(1, int(result.shape[0] * output_scale))
                new_width = max(1, int(result.shape[1] * output_scale))
                result = cv2.resize(result, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
            
            return result
        except Exception as e:
            logger.error(f"Error in extract_horizontal_scan: {str(e)}")
            return None
    
    def extract_vertical_scan(
        self,
        line_x: int,
        line_width: int,
        combine_mode: str,
        start_time: float,
        end_time: float,
        frame_step: int,
        temporal_stretch: float,
        spatial_stretch: float,
        output_scale: float,
        reverse_stack: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> Optional[np.ndarray]:
        if self.cap is None:
            logger.error("Video not loaded")
            return None
        
        self.reset_cancel()
        
        start_frame = int(start_time * self.fps)
        end_frame = int(end_time * self.fps)
        start_frame = max(0, start_frame)
        end_frame = min(self.total_frames, end_frame)
        
        if start_frame >= end_frame:
            logger.error(f"Invalid time range: start={start_time}, end={end_time}")
            return None
        
        num_output_cols = (end_frame - start_frame) // frame_step
        if num_output_cols == 0:
            logger.warning("No frames to process")
            return None
        
        line_x_clamped = max(0, min(line_x, self.width - 1))
        actual_line_width = min(line_width, self.width - line_x_clamped)
        actual_line_width = max(1, actual_line_width)
        
        if combine_mode == 'stack':
            slice_width = actual_line_width
        else:
            slice_width = 1
        
        output_width = num_output_cols * slice_width
        output_height = self.height
        
        if spatial_stretch != 1.0:
            output_height = max(1, int(output_height * spatial_stretch))
        
        buffer = np.zeros((output_height, output_width, 3), dtype=np.uint8)
        
        processed_slices = 0
        
        try:
            for frame_idx in range(start_frame, end_frame, frame_step):
                if self.is_canceled():
                    if processed_slices > 0:
                        return buffer[:, :processed_slices * slice_width]
                    return None
                
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = self.cap.read()
                
                if not ret:
                    logger.warning(f"Failed to read frame {frame_idx}")
                    continue
                
                line_end = min(line_x_clamped + actual_line_width, self.width)
                
                if combine_mode == 'average' and actual_line_width > 1:
                    slice_cols = line_end - line_x_clamped
                    if slice_cols > 1:
                        slice_data = np.mean(frame[:, line_x_clamped:line_end], axis=1)
                        slice_data = slice_data.astype(np.uint8)
                        slice_data = slice_data.reshape(-1, 1, 3)
                    else:
                        slice_data = frame[:, line_x_clamped:line_end].copy()
                else:
                    slice_data = frame[:, line_x_clamped:line_end].copy()
                    if reverse_stack and slice_data.shape[1] > 1:
                        slice_data = np.flip(slice_data, axis=1)
                
                if spatial_stretch != 1.0:
                    new_slice_width = slice_data.shape[1]
                    slice_data = cv2.resize(
                        slice_data,
                        (new_slice_width, output_height),
                        interpolation=cv2.INTER_LINEAR
                    )
                
                col_start = processed_slices * slice_width
                col_end = col_start + slice_data.shape[1]
                
                if col_end <= output_width:
                    buffer[:, col_start:col_end] = slice_data
                    processed_slices += 1
                
                if progress_callback and processed_slices % 10 == 0:
                    progress = processed_slices / num_output_cols * 100
                    if progress_callback(progress):
                        return None
            
            if processed_slices == 0:
                logger.warning("No frames extracted")
                return None
            
            result = buffer[:, :processed_slices * slice_width]
            
            if temporal_stretch != 1.0:
                new_width = max(1, int(result.shape[1] * temporal_stretch))
                result = cv2.resize(result, (new_width, result.shape[0]), interpolation=cv2.INTER_LINEAR)
            
            if output_scale != 1.0:
                new_height = max(1, int(result.shape[0] * output_scale))
                new_width = max(1, int(result.shape[1] * output_scale))
                result = cv2.resize(result, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
            
            return result
        except Exception as e:
            logger.error(f"Error in extract_vertical_scan: {str(e)}")
            return None
    
    def preview_scan(
        self,
        direction: str,
        line_pos: int,
        line_width: int,
        combine_mode: str,
        start_time: float,
        end_time: float,
        frame_step: int,
        temporal_stretch: float,
        spatial_stretch: float,
        output_scale: float,
        quality: str,
        reverse_stack: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> Optional[np.ndarray]:
        quality_presets = {
            'low': {'frame_step': 10, 'scale': 0.25},
            'medium': {'frame_step': 5, 'scale': 0.50},
            'high': {'frame_step': 2, 'scale': 0.75}
        }
        
        preset = quality_presets.get(quality, quality_presets['medium'])
        
        adjusted_frame_step = max(frame_step, preset['frame_step'])
        adjusted_scale = output_scale * preset['scale']
        
        if direction == 'horizontal':
            return self.extract_horizontal_scan(
                line_pos, line_width, combine_mode,
                start_time, end_time, adjusted_frame_step,
                temporal_stretch, spatial_stretch, adjusted_scale,
                reverse_stack, progress_callback
            )
        else:
            return self.extract_vertical_scan(
                line_pos, line_width, combine_mode,
                start_time, end_time, adjusted_frame_step,
                temporal_stretch, spatial_stretch, adjusted_scale,
                reverse_stack, progress_callback
            )
