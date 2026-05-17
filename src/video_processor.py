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


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def log_interp(a: float, b: float, t: float) -> float:
    if a <= 0 or b <= 0:
        return lerp(a, b, t)
    ratio = b / a
    return a * (ratio ** t)


def exp_interp(a: float, b: float, t: float) -> float:
    return a + (b - a) * (t * t)


LERP_FUNCTIONS = {
    'linear': lerp,
    'log': log_interp,
    'exp': exp_interp
}


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
        line_width_start: int,
        line_width_end: int,
        lerp_type: str,
        combine_mode: str,
        start_time: float,
        end_time: float,
        frame_step: int,
        spatial_stretch: float,
        output_scale: float,
        reverse_stack: bool = False,
        crop_top: int = 0,
        crop_bottom: int = 0,
        gaussian_blend: bool = False,
        gaussian_blend_pixels: int = 5,
        progress_callback: Optional[Callable] = None,
        partial_callback: Optional[Callable] = None
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

        crop_left = max(0, min(crop_top, self.width - 1))
        crop_right = max(0, min(crop_bottom, self.width - crop_left - 1))
        effective_width = self.width - crop_left - crop_right

        line_y_clamped = max(0, min(line_y, self.height - 1))
        
        lerp_func = LERP_FUNCTIONS.get(lerp_type, lerp)
        max_line_width = max(line_width_start, line_width_end)
        
        if combine_mode == 'stack':
            slice_height = max_line_width
        else:
            slice_height = 1
        
        if gaussian_blend:
            blend_margin = gaussian_blend_pixels
        else:
            blend_margin = 0

        output_width = effective_width
        output_height = num_output_rows * slice_height

        if spatial_stretch != 1.0:
            output_width = max(1, int(output_width * spatial_stretch))
        
        raw_slices = []
        extracted_heights = []
        
        processed_slices = 0
        total_frames_to_process = num_output_rows
        
        try:
            frame_idx_in_slice = 0
            for frame_idx in range(start_frame, end_frame, frame_step):
                if self.is_canceled():
                    break
                
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = self.cap.read()
                
                if not ret:
                    logger.warning(f"Failed to read frame {frame_idx}")
                    continue
                
                if crop_left > 0 or crop_right > 0:
                    frame = frame[:, crop_left:self.width - crop_right]

                t = frame_idx_in_slice / max(1, total_frames_to_process - 1)
                current_line_width = int(round(lerp_func(line_width_start, line_width_end, t)))
                current_line_width = max(1, min(current_line_width, effective_width))
                
                if gaussian_blend and combine_mode != 'average':
                    y_start = line_y_clamped
                    y_end = min(
                        self.height,
                        line_y_clamped + current_line_width + gaussian_blend_pixels
                    )
                else:
                    y_start = line_y_clamped
                    y_end = min(self.height, line_y_clamped + current_line_width)
                
                if combine_mode == 'average' and current_line_width > 1:
                    slice_rows = y_end - y_start
                    if slice_rows > 1:
                        slice_data = np.mean(frame[y_start:y_end, :], axis=0)
                        slice_data = slice_data.astype(np.uint8)
                        slice_data = slice_data.reshape(1, -1, 3)
                    else:
                        slice_data = frame[y_start:y_end, :].copy()
                else:
                    slice_data = frame[y_start:y_end, :].copy()
                
                extracted_heights.append(current_line_width)
                
                if spatial_stretch != 1.0:
                    new_slice_height = slice_data.shape[0]
                    slice_data = cv2.resize(
                        slice_data,
                        (output_width, new_slice_height),
                        interpolation=cv2.INTER_LINEAR
                    )
                
                raw_slices.append(slice_data.copy())
                processed_slices += 1
                frame_idx_in_slice += 1
                
                if progress_callback and processed_slices % 10 == 0:
                    progress = processed_slices / num_output_rows * 100
                    if progress_callback(progress):
                        return None
                    if partial_callback and len(raw_slices) > 0:
                        partial_result = np.vstack(raw_slices)
                        partial_callback(partial_result)
            
            if processed_slices == 0:
                logger.warning("No frames extracted")
                return None
            
            if reverse_stack and combine_mode != 'average':
                raw_slices = [
                    np.flip(s, axis=0) if s.shape[0] > 1 else s for s in raw_slices
                ]
            
            if gaussian_blend and len(raw_slices) > 1 and combine_mode != 'average':
                blend_pixels = gaussian_blend_pixels
                
                output_slice = raw_slices[0].astype(np.float64)
                
                for i in range(1, len(raw_slices)):
                    next_slice = raw_slices[i].astype(np.float64)
                    
                    prev_height = output_slice.shape[0]
                    next_height = next_slice.shape[0]
                    overlap = min(blend_pixels, prev_height, next_height)
                    
                    if overlap > 0:
                        for row in range(overlap):
                            alpha = row / max(1, overlap - 1) if overlap > 1 else 0.5
                            prev_row_idx = prev_height - overlap + row
                            blended = (
                                output_slice[prev_row_idx, :] * (1 - alpha) +
                                next_slice[row, :] * alpha
                            )
                            output_slice[prev_row_idx, :] = blended
                        
                        if next_height > overlap:
                            output_slice = np.vstack(
                                [output_slice, next_slice[overlap:, :]]
                            )
                    else:
                        output_slice = np.vstack([output_slice, next_slice])
                
                result = output_slice.astype(np.uint8)
                
                if gaussian_blend_pixels > 0 and result.shape[0] > gaussian_blend_pixels:
                    result = result[:-gaussian_blend_pixels, :]
                
                if output_scale != 1.0:
                    new_height = max(1, int(result.shape[0] * output_scale))
                    new_width = max(1, int(result.shape[1] * output_scale))
                    result = cv2.resize(
                        result, (new_width, new_height), interpolation=cv2.INTER_LINEAR
                    )
                
                return result
            
            slices = raw_slices
            
            if slices:
                result = np.vstack(slices)
                
                if output_scale != 1.0:
                    new_height = max(1, int(result.shape[0] * output_scale))
                    new_width = max(1, int(result.shape[1] * output_scale))
                    result = cv2.resize(result, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
                
                return result
            
            return None
        except Exception as e:
            logger.error(f"Error in extract_horizontal_scan: {str(e)}")
            return None
    
    def extract_vertical_scan(
        self,
        line_x: int,
        line_width_start: int,
        line_width_end: int,
        lerp_type: str,
        combine_mode: str,
        start_time: float,
        end_time: float,
        frame_step: int,
        spatial_stretch: float,
        output_scale: float,
        reverse_stack: bool = False,
        crop_top: int = 0,
        crop_bottom: int = 0,
        gaussian_blend: bool = False,
        gaussian_blend_pixels: int = 5,
        progress_callback: Optional[Callable] = None,
        partial_callback: Optional[Callable] = None
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
        
        crop_top = max(0, min(crop_top, self.height - 1))
        crop_bottom = max(0, min(crop_bottom, self.height - crop_top - 1))
        effective_height = self.height - crop_top - crop_bottom
        
        line_x_clamped = max(0, min(line_x, self.width - 1))
        
        lerp_func = LERP_FUNCTIONS.get(lerp_type, lerp)
        max_line_width = max(line_width_start, line_width_end)
        
        if gaussian_blend:
            blend_margin = gaussian_blend_pixels
        else:
            blend_margin = 0
        
        output_height = effective_height
        
        if spatial_stretch != 1.0:
            output_height = max(1, int(output_height * spatial_stretch))
        
        raw_slices = []
        extracted_widths = []
        processed_slices = 0
        total_frames_to_process = num_output_cols
        
        try:
            frame_idx_in_slice = 0
            for frame_idx in range(start_frame, end_frame, frame_step):
                if self.is_canceled():
                    break
                
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = self.cap.read()
                
                if not ret:
                    logger.warning(f"Failed to read frame {frame_idx}")
                    continue
                
                if crop_top > 0 or crop_bottom > 0:
                    frame = frame[crop_top:self.height - crop_bottom, :]
                
                t = frame_idx_in_slice / max(1, total_frames_to_process - 1)
                current_line_width = int(round(lerp_func(line_width_start, line_width_end, t)))
                current_line_width = max(1, min(current_line_width, self.width - line_x_clamped))
                
                if gaussian_blend and combine_mode != 'average':
                    x_start = line_x_clamped
                    x_end = min(
                        self.width,
                        line_x_clamped + current_line_width + gaussian_blend_pixels
                    )
                else:
                    x_start = line_x_clamped
                    x_end = min(self.width, line_x_clamped + current_line_width)
                
                if combine_mode == 'average' and current_line_width > 1:
                    slice_cols = x_end - x_start
                    if slice_cols > 1:
                        slice_data = np.mean(frame[:, x_start:x_end], axis=1)
                        slice_data = slice_data.astype(np.uint8)
                        slice_data = slice_data.reshape(-1, 1, 3)
                    else:
                        slice_data = frame[:, x_start:x_end].copy()
                else:
                    slice_data = frame[:, x_start:x_end].copy()
                
                extracted_widths.append(current_line_width)
                
                if spatial_stretch != 1.0:
                    new_slice_width = slice_data.shape[1]
                    slice_data = cv2.resize(
                        slice_data,
                        (new_slice_width, output_height),
                        interpolation=cv2.INTER_LINEAR
                    )
                
                raw_slices.append(slice_data.copy())
                processed_slices += 1
                frame_idx_in_slice += 1
                
                if progress_callback and processed_slices % 10 == 0:
                    progress = processed_slices / num_output_cols * 100
                    if progress_callback(progress):
                        return None
                    if partial_callback and len(raw_slices) > 0:
                        partial_result = np.hstack(raw_slices)
                        partial_callback(partial_result)
            
            if processed_slices == 0:
                logger.warning("No frames extracted")
                return None
            
            if reverse_stack and combine_mode != 'average':
                raw_slices = [
                    np.flip(s, axis=1) if s.shape[1] > 1 else s for s in raw_slices
                ]
            
            if gaussian_blend and len(raw_slices) > 1 and combine_mode != 'average':
                blend_pixels = gaussian_blend_pixels
                
                output_slice = raw_slices[0].astype(np.float64)
                
                for i in range(1, len(raw_slices)):
                    next_slice = raw_slices[i].astype(np.float64)
                    
                    prev_width = output_slice.shape[1]
                    next_width = next_slice.shape[1]
                    overlap = min(blend_pixels, prev_width, next_width)
                    
                    if overlap > 0:
                        for col in range(overlap):
                            alpha = col / max(1, overlap - 1) if overlap > 1 else 0.5
                            prev_col_idx = prev_width - overlap + col
                            blended = (
                                output_slice[:, prev_col_idx] * (1 - alpha) +
                                next_slice[:, col] * alpha
                            )
                            output_slice[:, prev_col_idx] = blended
                        
                        if next_width > overlap:
                            output_slice = np.hstack(
                                [output_slice, next_slice[:, overlap:]]
                            )
                    else:
                        output_slice = np.hstack([output_slice, next_slice])
                
                result = output_slice.astype(np.uint8)
                
                if gaussian_blend_pixels > 0 and result.shape[1] > gaussian_blend_pixels:
                    result = result[:, :-gaussian_blend_pixels]
                
                if output_scale != 1.0:
                    new_height = max(1, int(result.shape[0] * output_scale))
                    new_width = max(1, int(result.shape[1] * output_scale))
                    result = cv2.resize(
                        result, (new_width, new_height), interpolation=cv2.INTER_LINEAR
                    )
                
                return result
            
            slices = raw_slices
            
            if slices:
                result = np.hstack(slices)
                
                if output_scale != 1.0:
                    new_height = max(1, int(result.shape[0] * output_scale))
                    new_width = max(1, int(result.shape[1] * output_scale))
                    result = cv2.resize(result, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
                
                return result
            
            return None
        except Exception as e:
            logger.error(f"Error in extract_vertical_scan: {str(e)}")
            return None
    
    def preview_scan(
        self,
        direction: str,
        line_pos: int,
        line_width_start: int,
        line_width_end: int,
        lerp_type: str,
        combine_mode: str,
        start_time: float,
        end_time: float,
        frame_step: int,
        spatial_stretch: float,
        output_scale: float,
        quality: str,
        reverse_stack: bool = False,
        crop_top: int = 0,
        crop_bottom: int = 0,
        gaussian_blend: bool = False,
        gaussian_blend_pixels: int = 5,
        progress_callback: Optional[Callable] = None,
        partial_callback: Optional[Callable] = None
    ) -> Optional[np.ndarray]:
        if direction == 'horizontal':
            return self.extract_horizontal_scan(
                line_pos, line_width_start, line_width_end, lerp_type, combine_mode,
                start_time, end_time, frame_step,
                spatial_stretch, output_scale,
                reverse_stack, crop_top, crop_bottom, 
                gaussian_blend, gaussian_blend_pixels, progress_callback, partial_callback
            )
        else:
            return self.extract_vertical_scan(
                line_pos, line_width_start, line_width_end, lerp_type, combine_mode,
                start_time, end_time, frame_step,
                spatial_stretch, output_scale,
                reverse_stack, crop_top, crop_bottom,
                gaussian_blend, gaussian_blend_pixels, progress_callback, partial_callback
            )
