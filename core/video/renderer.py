"""
FFmpeg 影片渲染器
"""

import re
import subprocess
from typing import Optional, Callable
from pathlib import Path


class VideoRenderer:
    """使用 FFmpeg 渲染影片"""

    def render(
        self,
        video_path: str,
        audio_path: str,
        subtitle_path: str,
        output_path: str,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> bool:
        """渲染影片"""
        try:
            total_duration = self._get_duration(video_path)
            subtitle_filter = self._build_subtitle_filter(subtitle_path)

            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-i', audio_path,
                '-vf', subtitle_filter,
                '-map', '0:v:0',
                '-map', '1:a:0',
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-shortest',
                '-y',
                output_path,
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if process.stderr:
                for line in process.stderr:
                    progress = self._parse_progress(line, total_duration)
                    if progress_callback and progress is not None:
                        progress_callback(progress)

            process.wait()
            if progress_callback:
                progress_callback(100)

            return process.returncode == 0
        except Exception:
            return False

    def _get_duration(self, video_path: str) -> Optional[float]:
        """取得影片總長度（秒）"""
        try:
            result = subprocess.run(
                [
                    'ffprobe',
                    '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    video_path,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if result.stdout:
                return float(result.stdout.strip())
        except Exception:
            return None
        return None

    def _parse_progress(self, line: str, total_duration: Optional[float]) -> Optional[int]:
        """從 FFmpeg 輸出解析進度百分比"""
        if total_duration is None:
            return None
        match = re.search(r'time=(\d+):(\d+):(\d+)\.(\d+)', line)
        if not match:
            return None
        hours, minutes, seconds, centisecs = match.groups()
        current = (
            int(hours) * 3600
            + int(minutes) * 60
            + int(seconds)
            + int(centisecs) / 100
        )
        percent = int(min(1.0, current / total_duration) * 100)
        return percent

    def _build_subtitle_filter(self, subtitle_path: str) -> str:
        """建立字幕濾鏡參數"""
        escaped = self._escape_filter_path(subtitle_path)
        return f"subtitles=filename='{escaped}'"

    def _escape_filter_path(self, subtitle_path: str) -> str:
        """轉義字幕路徑（避免 FFmpeg 濾鏡解析失敗）"""
        path_str = str(Path(subtitle_path))
        return (
            path_str.replace('\\', '\\\\')
            .replace("'", "\\'")
            .replace(':', '\\:')
        )
