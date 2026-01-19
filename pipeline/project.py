"""
Karaoke project state management
Phase 1.1.3: Project State 管理
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class KaraokeProject:
    """卡拉OK 專案狀態"""
    
    # 基本信息
    project_name: str = ""
    project_path: Optional[str] = None
    video_path: Optional[str] = None
    
    # 音訊狀態
    stems: Optional[Dict[str, str]] = None  # {'vocal': '/path/to/vocal.wav', ...}
    stems_dir: Optional[str] = None  # 存放各軌的目錄
    
    # LRC 狀態
    lrc_timeline: Optional[object] = None  # LrcTimeline 對象
    lrc_file_path: Optional[str] = None
    
    # ASS 狀態
    ass_content: Optional[str] = None
    ass_file_path: Optional[str] = None
    
    # 輸出
    output_path: Optional[str] = None
    
    # 時間戳
    created_at: str = ""
    updated_at: str = ""
    
    def get_state(self) -> str:
        """取得目前專案狀態"""
        if not self.video_path:
            return 'EMPTY'
        elif self.video_path and not self.stems:
            return 'VIDEO_UPLOADED'
        elif self.stems and not self.lrc_timeline:
            return 'STEMS_READY'
        elif self.lrc_timeline and not self.ass_content:
            return 'LRC_READY'
        elif self.ass_content and not self.output_path:
            return 'SUBTITLE_CONVERTED'
        elif self.output_path:
            return 'EXPORT_COMPLETE'
        return 'UNKNOWN'
    
    def to_dict(self) -> dict:
        """轉為字典（不包含不可序列化的對象）"""
        return {
            'project_name': self.project_name,
            'project_path': self.project_path,
            'video_path': self.video_path,
            'stems': self.stems,
            'stems_dir': self.stems_dir,
            'lrc_file_path': self.lrc_file_path,
            'ass_file_path': self.ass_file_path,
            'output_path': self.output_path,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
    
    def save_to_json(self, file_path: str):
        """保存專案狀態為 JSON"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"Project saved: {file_path}")
        except Exception as e:
            logger.error(f"Failed to save project: {e}")
            raise
    
    @classmethod
    def load_from_json(cls, file_path: str) -> 'KaraokeProject':
        """從 JSON 加載專案狀態"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            project = cls(**data)
            logger.info(f"Project loaded: {file_path}")
            return project
        except Exception as e:
            logger.error(f"Failed to load project: {e}")
            raise


if __name__ == "__main__":
    # 測試代碼
    logging.basicConfig(level=logging.INFO)
    
    project = KaraokeProject(project_name="Test Project")
    print(f"Initial state: {project.get_state()}")
    
    # 模擬上傳視頻
    project.video_path = "/path/to/video.mp4"
    print(f"After upload: {project.get_state()}")
