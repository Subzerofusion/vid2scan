import json
import os
from typing import Optional, Dict, Any
from pathlib import Path


class SessionManager:
    def __init__(self):
        self.session_dir = Path.home() / '.vid2scan'
        self.session_file = self.session_dir / 'session.json'
        self.session_dir.mkdir(parents=True, exist_ok=True)
    
    def save_session(self, video_path: Optional[str], settings: Dict[str, Any]) -> bool:
        try:
            session_data = {
                'video_path': video_path,
                'settings': settings
            }
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            return True
        except Exception:
            return False
    
    def load_session(self) -> Optional[Dict[str, Any]]:
        try:
            if not self.session_file.exists():
                return None
            with open(self.session_file, 'r') as f:
                data = json.load(f)
            
            if data.get('video_path') and not os.path.exists(data['video_path']):
                data['video_path'] = None
            
            return data
        except Exception:
            return None
    
    def clear_session(self) -> bool:
        try:
            if self.session_file.exists():
                self.session_file.unlink()
            return True
        except Exception:
            return False
