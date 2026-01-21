"""
LRC -> ASS 轉換器
"""

from typing import Dict, Optional

from core.lrc import LrcTimeline
from .config import SubtitleConfig


class LrcToAssConverter:
    """LRC -> ASS 轉換器"""

    def __init__(self, config: Optional[Dict] = None):
        default_config = SubtitleConfig()
        if config:
            merged = default_config.to_dict()
            merged.update(config)
            self.config = SubtitleConfig(**merged)
        else:
            self.config = default_config

    def convert(self, timeline: LrcTimeline) -> str:
        """轉換為 ASS 內容"""
        ass_lines = []
        ass_lines.append(self._generate_script_info(timeline))
        ass_lines.append(self._generate_styles())
        ass_lines.append(self._generate_events(timeline))
        return '\n'.join(ass_lines)

    def save_file(self, ass_content: str, file_path: str):
        """保存 ASS 文件"""
        with open(file_path, 'w', encoding='utf-8') as file_handle:
            file_handle.write(ass_content)

    def _generate_script_info(self, timeline: LrcTimeline) -> str:
        """生成 [Script Info] 段"""
        lines = [
            '[Script Info]',
            'Title: ' + timeline.metadata.get('title', 'Karaoke'),
            'ScriptType: v4.00+',
            'Collisions: Normal',
            'PlayResX: 384',
            'PlayResY: 288',
        ]
        return '\n'.join(lines)

    def _generate_styles(self) -> str:
        """生成 [V4+ Styles] 段"""
        primary_color = self._rgb_to_ass(self.config.primary_color)
        secondary_color = self._rgb_to_ass(self.config.secondary_color)
        alignment = self._position_to_alignment(self.config.position)

        lines = [
            '[V4+ Styles]',
            'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, '
            'BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, '
            'BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
            (
                'Style: Default,'
                f'{self.config.fontname},{self.config.fontsize},'
                f'{primary_color},{secondary_color},&H00000000,&H00000000,'
                '0,0,0,0,100,100,0,0,1,'
                f'{self.config.outline},{self.config.shadow},{alignment},0,0,0,1'
            ),
        ]
        return '\n'.join(lines)

    def _generate_events(self, timeline: LrcTimeline) -> str:
        """生成 [Events] 段"""
        lines = [
            '[Events]',
            'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text',
        ]

        for line in timeline.lines:
            for word in line.words:
                start_time = self._format_ass_time(word.start_time)
                end_time = self._format_ass_time(word.end_time)
                text = word.text
                dialogue = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}"
                lines.append(dialogue)

        return '\n'.join(lines)

    def _rgb_to_ass(self, rgb_hex: str) -> str:
        """RGB #RRGGBB -> ASS &H00BBGGRR"""
        rgb = rgb_hex.lstrip('#')
        r = rgb[0:2]
        g = rgb[2:4]
        b = rgb[4:6]
        return f"&H00{b}{g}{r}"

    def _format_ass_time(self, seconds: float) -> str:
        """秒 -> ASS 時間格式：h:mm:ss.xx"""
        hours = int(seconds) // 3600
        minutes = (int(seconds) % 3600) // 60
        secs = int(seconds) % 60
        centisecs = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"

    def _position_to_alignment(self, position: str) -> int:
        """位置 -> ASS 對齊"""
        mapping = {
            'top': 8,
            'center': 5,
            'bottom': 2,
        }
        return mapping.get(position, 2)
