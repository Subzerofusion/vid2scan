import cv2
import numpy as np


def extract_horizontal_line(frame: np.ndarray, y: int, width: int) -> np.ndarray:
    return frame[y:y + width, :]


def extract_vertical_line(frame: np.ndarray, x: int, width: int) -> np.ndarray:
    return frame[:, x:x + width]


def combine_lines_average(lines: np.ndarray) -> np.ndarray:
    return np.mean(lines, axis=0).astype(np.uint8)


def apply_spatial_stretch(line: np.ndarray, factor: int) -> np.ndarray:
    if factor <= 1:
        return line
    
    if len(line.shape) == 1:
        new_width = line.shape[0] * factor
        return cv2.resize(line, (new_width, 1), interpolation=cv2.INTER_LINEAR)
    else:
        new_width = line.shape[1] * factor
        new_height = line.shape[0]
        return cv2.resize(line, (new_width, new_height), interpolation=cv2.INTER_LINEAR)


def apply_temporal_stretch(lines: list, factor: int) -> np.ndarray:
    if factor <= 1:
        return np.array(lines, dtype=np.uint8)
    
    stretched = []
    for line in lines:
        for _ in range(factor):
            stretched.append(line)
    return np.array(stretched, dtype=np.uint8)


def scale_output(image: np.ndarray, scale: float) -> np.ndarray:
    if scale == 1.0:
        return image
    
    new_height = int(image.shape[0] * scale)
    new_width = int(image.shape[1] * scale)
    return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
