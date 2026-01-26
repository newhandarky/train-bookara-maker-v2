"""
LRC -> ASS 轉換器
"""

from typing import Dict, Optional

from core.lrc import LrcTimeline
from .config import SubtitleConfig


class LrcToAssConverter:
    """LRC -> ASS 轉換器"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = SubtitleConfig.from_dict(config) if config else SubtitleConfig()

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
        top_alignment = self._position_to_alignment('top')
        bottom_alignment = self._position_to_alignment('bottom')
        ruby_fontname = self.config.ruby_fontname or self.config.fontname
        ruby_fontsize = (
            self.config.ruby_fontsize
            if self.config.ruby_fontsize and self.config.ruby_fontsize > 0
            else max(1, int(self.config.fontsize * 0.5))
        )

        lines = [
            '[V4+ Styles]',
            'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, '
            'BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, '
            'BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
        ]

        spacing = int(self.config.spacing or 0)
        bold_flag = -1 if getattr(self.config, 'bold', False) else 0
        italic_flag = -1 if getattr(self.config, 'italic', False) else 0

        for group_id in self._get_enabled_groups():
            group = self.config.color_groups.get(group_id, {})
            primary_color = self._rgb_to_ass(
                group.get('primary_color', self.config.primary_color)
            )
            secondary_color = self._rgb_to_ass(
                group.get('secondary_color', self.config.secondary_color)
            )
            ruby_color = self._rgb_to_ass(
                self.config.ruby_color or group.get('secondary_color', self.config.secondary_color)
            )

            lines.append(
                'Style: '
                f'{group_id}_Top,'
                f'{self.config.fontname},{self.config.fontsize},'
                f'{primary_color},{secondary_color},&H00000000,&H00000000,'
                f'{bold_flag},{italic_flag},0,0,100,100,{spacing},0,1,'
                f'{self.config.outline},{self.config.shadow},{top_alignment},'
                f'{self.config.margin_l},{self.config.margin_r},{self.config.top_margin},1'
            )
            lines.append(
                'Style: '
                f'{group_id}_Bottom,'
                f'{self.config.fontname},{self.config.fontsize},'
                f'{primary_color},{secondary_color},&H00000000,&H00000000,'
                f'{bold_flag},{italic_flag},0,0,100,100,{spacing},0,1,'
                f'{self.config.outline},{self.config.shadow},{bottom_alignment},'
                f'{self.config.margin_l},{self.config.margin_r},{self.config.bottom_margin},1'
            )
            ruby_top_margin = max(0, self.config.top_margin - self.config.ruby_offset_y)
            ruby_bottom_margin = self.config.bottom_margin + self.config.ruby_offset_y
            lines.append(
                'Style: '
                f'{group_id}_RubyTop,'
                f'{ruby_fontname},{ruby_fontsize},'
                f'{ruby_color},{ruby_color},&H00000000,&H00000000,'
                f'{bold_flag},{italic_flag},0,0,100,100,{spacing},0,1,'
                f'{self.config.outline},{self.config.shadow},{top_alignment},'
                f'{self.config.margin_l},{self.config.margin_r},{ruby_top_margin},1'
            )
            lines.append(
                'Style: '
                f'{group_id}_RubyBottom,'
                f'{ruby_fontname},{ruby_fontsize},'
                f'{ruby_color},{ruby_color},&H00000000,&H00000000,'
                f'{bold_flag},{italic_flag},0,0,100,100,{spacing},0,1,'
                f'{self.config.outline},{self.config.shadow},{bottom_alignment},'
                f'{self.config.margin_l},{self.config.margin_r},{ruby_bottom_margin},1'
            )

        return '\n'.join(lines)

    def _generate_events(self, timeline: LrcTimeline) -> str:
        """生成 [Events] 段"""
        lines = [
            '[Events]',
            'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text',
        ]

        enabled_groups = self._get_enabled_groups()

        for line_idx, line in enumerate(timeline.lines):
            if not line.words:
                continue

            group_id = line.group_id if line.group_id in enabled_groups else enabled_groups[0]
            position = 'Top' if line_idx % 2 == 0 else 'Bottom'
            style_name = f"{group_id}_{position}"
            start_time = line.words[0].start_time
            end_time = line.words[-1].end_time + self.config.tail_hold_sec

            lead_in = max(0.0, self.config.lead_in_sec)
            line_start = max(0.0, start_time - lead_in)

            karaoke_text = self._build_karaoke_text(line, line_start)
            dialogue = (
                f"Dialogue: 0,{self._format_ass_time(line_start)},"
                f"{self._format_ass_time(end_time)},{style_name},,0,0,0,,"
                f"{karaoke_text}"
            )
            lines.append(dialogue)

            ruby_text, has_ruby = self._build_ruby_text(line, line_start)
            if has_ruby:
                ruby_style = f"{group_id}_Ruby{position}"
                ruby_dialogue = (
                    f"Dialogue: 0,{self._format_ass_time(line_start)},"
                    f"{self._format_ass_time(end_time)},{ruby_style},,0,0,0,,"
                    f"{ruby_text}"
                )
                lines.append(ruby_dialogue)

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

    def _get_enabled_groups(self) -> list:
        """取得啟用的群組清單"""
        groups = self.config.enabled_groups or list(self.config.color_groups.keys())
        return groups if groups else ['A']

    def _build_karaoke_text(self, line, line_start: float) -> str:
        """組合行級別 \k 標籤字串"""
        parts = []
        prev_end = line_start

        for word in line.words:
            gap = max(0.0, word.start_time - prev_end)
            gap_cs = int(round(gap * 100))
            if gap_cs > 0:
                parts.append(f"{{\\k{gap_cs}}}")

            duration_cs = int(round(max(0.0, word.end_time - word.start_time) * 100))
            parts.append(f"{{\\k{duration_cs}}}{word.text}")
            prev_end = word.end_time

        return ''.join(parts)

    def _build_ruby_text(self, line, line_start: float) -> tuple:
        """組合 Ruby 行文字（僅顯示漢字假名）"""
        parts = []
        prev_end = line_start
        has_ruby = False
        space_char = chr(0x3000)

        for word in line.words:
            gap = max(0.0, word.start_time - prev_end)
            gap_cs = int(round(gap * 100))
            if gap_cs > 0:
                parts.append(f"{{\\k{gap_cs}}}")

            duration_cs = int(round(max(0.0, word.end_time - word.start_time) * 100))
            ruby_text = ''
            if word.ruby_pair and word.ruby_pair.ruby and self._is_kanji(word.text):
                ruby_text = word.ruby_pair.ruby
                has_ruby = True
            else:
                ruby_text = space_char

            parts.append(f"{{\\k{duration_cs}}}{ruby_text}")
            prev_end = word.end_time

        return ''.join(parts), has_ruby

    def _is_kanji(self, text: str) -> bool:
        """判斷文字是否含漢字"""
        if not text:
            return False
        code = ord(text[0])
        return (
            0x4E00 <= code <= 0x9FFF
            or 0x3400 <= code <= 0x4DBF
            or 0xF900 <= code <= 0xFAFF
        )
