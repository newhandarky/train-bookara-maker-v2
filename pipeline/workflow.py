"""
專案流程協調
"""

from pathlib import Path
from typing import Optional, Callable, Tuple

from core.subtitle import LrcToAssConverter, SubtitleConfig
from core.video import VideoRenderer
from core.lrc import LrcTimeline


class KaraokeWorkflow:
    """專案流程管理"""

    def __init__(self, subtitle_config: Optional[dict] = None):
        self.subtitle_config = SubtitleConfig.from_dict(subtitle_config) if subtitle_config else SubtitleConfig()
        self.renderer = VideoRenderer()

    def ensure_ass_file(self, timeline: LrcTimeline, output_dir: str) -> Tuple[str, str]:
        """確保 ASS 檔案存在並回傳路徑與內容"""
        output_path = Path(output_dir) / "subtitles.ass"
        converter = LrcToAssConverter(self.subtitle_config.to_dict())
        ass_content = converter.convert(timeline)
        converter.save_file(ass_content, str(output_path))
        return str(output_path), ass_content

    def export_video(
        self,
        video_path: str,
        audio_path: str,
        subtitle_path: str,
        output_path: str,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> bool:
        """輸出影片"""
        return self.renderer.render(
            video_path=video_path,
            audio_path=audio_path,
            subtitle_path=subtitle_path,
            output_path=output_path,
            progress_callback=progress_callback,
        )
