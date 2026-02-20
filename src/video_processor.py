import cv2
import numpy as np
import logging
import os
from typing import Optional, Callable

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

# Create absolute path for error.log
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
    
    def _extract_horizontal_lines(
        self,
        frame: np.ndarray,
        line_y: int,
        line_width: int,
        combine_mode: str,
        spatial_stretch: int
    ) -> np.ndarray:
        lines = frame[line_y:line_y + line_width, :]
        
        if line_width > 1 and combine_mode == 'average':
            line = np.mean(lines, axis=0, dtype=np.uint8)
            line = line.reshape(1, -1)
        else:
            line = lines[0] if line_width > 1 else lines
        
        if spatial_stretch > 1:
            if len(line.shape) == 1:
                line = line.reshape(1, -1)
            new_width = int(line.shape[1] * spatial_stretch)
            line = cv2.resize(line, (new_width, 1), interpolation=cv2.INTER_LINEAR)
        
        return line
    
    def _extract_vertical_lines(
        self,
        frame: np.ndarray,
        line_x: int,
        line_width: int,
        combine_mode: str,
        spatial_stretch: int
    ) -> np.ndarray:
        cols = frame[:, line_x:line_x + line_width]
        
        if line_width > 1 and combine_mode == 'average':
            col = np.mean(cols, axis=1, dtype=np.uint8)
        else:
            col = cols[:, 0] if line_width > 1 else cols
        
        if spatial_stretch > 1:
            col = cv2.resize(col, (1, int(col.shape[0] * spatial_stretch)), interpolation=cv2.INTER_LINEAR)
        
        return col
    
    def _apply_temporal_stretch(self, lines: list, temporal_stretch: int) -> np.ndarray:
        if temporal_stretch > 1:
            stretched_lines = []
            for line in lines:
                for _ in range(temporal_stretch):
                    stretched_lines.append(line)
            return np.array(stretched_lines, dtype=np.uint8)
        return np.array(lines, dtype=np.uint8)
    
    def extract_horizontal_scan(
        self,
        line_y: int,
        line_width: int,
        combine_mode: str,
        start_time: float,
        end_time: float,
        frame_step: int,
        temporal_stretch: int,
        spatial_stretch: int,
        output_scale: float,
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
        
        lines = []
        total_frames_to_process = (end_frame - start_frame) // frame_step
        
        try:
            for frame_idx in range(start_frame, end_frame, frame_step):
                if self.is_canceled():
                    if lines:
                        lines = self._apply_temporal_stretch(lines, temporal_stretch)
                        result = np.vstack(lines)
                        if output_scale != 1.0:
                            new_height = int(result.shape[0] * output_scale)
                            new_width = int(result.shape[1] * output_scale)
                            result = cv2.resize(result, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
                    return result
                    return None
                
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = self.cap.read()
                
                if not ret:
                    logger.warning(f"Failed to read frame {frame_idx}")
                    continue
                
                line = self._extract_horizontal_lines(frame, line_y, line_width, combine_mode, spatial_stretch)
                lines.append(line)
                
                if progress_callback and len(lines) % 10 == 0:
                    progress = len(lines) / total_frames_to_process * 100
                    if progress_callback(progress):
                        return None
            
            if not lines:
                logger.warning("No frames extracted")
                return None
            
            lines = self._apply_temporal_stretch(lines, temporal_stretch)
            result = np.vstack(lines)
            
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
        temporal_stretch: int,
        spatial_stretch: int,
        output_scale: float,
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
        
        cols = []
        total_frames_to_process = (end_frame - start_frame) // frame_step
        
        try:
            for frame_idx in range(start_frame, end_frame, frame_step):
                if self.is_canceled():
                    if cols:
                        cols = self._apply_temporal_stretch(cols, temporal_stretch)
                        result = np.hstack(cols)
                        if output_scale != 1.0:
                            new_height = max(1, int(result.shape[0] * output_scale))
                            new_width = max(1, int(result.shape[1] * output_scale))
                            result = cv2.resize(result, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
                    return result
                    return None
                
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = self.cap.read()
                
                if not ret:
                    logger.warning(f"Failed to read frame {frame_idx}")
                    continue
                
                col = self._extract_vertical_lines(frame, line_x, line_width, combine_mode, spatial_stretch)
                cols.append(col)
                
                if progress_callback and len(cols) % 10 == 0:
                    progress = len(cols) / total_frames_to_process * 100
                    if progress_callback(progress):
                        return None
            
            if not cols:
                logger.warning("No frames extracted")
                return None
            
            cols = self._apply_temporal_stretch(cols, temporal_stretch)
            result = np.hstack(cols)
            
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
        temporal_stretch: int,
        spatial_stretch: int,
        output_scale: float,
        quality: str,
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
                progress_callback
            )
        else:
            return self.extract_vertical_scan(
                line_pos, line_width, combine_mode,
                start_time, end_time, adjusted_frame_step,
                temporal_stretch, spatial_stretch, adjusted_scale,
                progress_callback
            )
