import re


def parse_time_str(time_str: str) -> float:
    pattern = r'^(\d{2}):(\d{2}):(\d{2})(?:\.(\d{3}))?$'
    match = re.match(pattern, time_str)
    
    if not match:
        raise ValueError(f"Invalid time format: {time_str}. Expected HH:MM:SS.mmm")
    
    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    milliseconds = int(match.group(4)) if match.group(4) else 0
    
    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000


def seconds_to_time_str(seconds: float) -> str:
    hours = int(seconds // 3600)
    remaining = seconds % 3600
    minutes = int(remaining // 60)
    remaining_seconds = remaining % 60
    secs = int(remaining_seconds)
    milliseconds = int((remaining_seconds - secs) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"


def clamp_time(time_sec: float, max_duration: float) -> float:
    return max(0.0, min(time_sec, max_duration))
