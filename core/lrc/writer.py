"""
LRC 寫入器

作用：
- 將 LrcTimeline 轉為 LRC 字串
- 寫入 LRC 檔案（UTF-8-SIG）
"""

from .model import LrcTimeline


class LrcWriter:
    """LRC 文件寫入器"""

    def write_file(self, timeline: LrcTimeline, file_path: str):
        """寫入 LRC 檔案（UTF-8-SIG）"""
        content = self.to_string(timeline)
        # 強制使用 UTF-8-SIG（帶 BOM）
        with open(file_path, 'w', encoding='utf-8-sig') as file_handle:
            file_handle.write(content)

    def to_string(self, timeline: LrcTimeline) -> str:
        """將時間軸轉為 LRC 字串"""
        lines = []

        # 元資訊
        artist = timeline.metadata.get('artist', '')
        title = timeline.metadata.get('title', '')
        album = timeline.metadata.get('album', '')

        if artist:
            lines.append(f"[ar:{artist}]")
        if title:
            lines.append(f"[ti:{title}]")
        if album:
            lines.append(f"[al:{album}]")
        if timeline.offset:
            offset_ms = int(round(timeline.offset * 1000))
            lines.append(f"[offset:{offset_ms}]")

        # 空行分隔
        lines.append('')

        # 歌詞行（以詞為單位輸出）
        for line in timeline.lines:
            for word in line.words:
                timestamp = self._format_timestamp(word.start_time)
                ruby_text = ''
                if word.ruby_pair and word.ruby_pair.ruby != '':
                    ruby_text = f"{{{word.ruby_pair.ruby}}}"
                lines.append(f"[{timestamp}]{word.text}{ruby_text}")

        return '\n'.join(lines)

    def _format_timestamp(self, seconds: float) -> str:
        """將秒數格式化為 mm:ss.xx"""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        centisecs = int(round((seconds % 1) * 100))
        return f"{minutes:02d}:{secs:02d}.{centisecs:02d}"
