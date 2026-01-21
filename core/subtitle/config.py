"""
字幕樣式設定
"""

from dataclasses import dataclass


@dataclass
class SubtitleConfig:
    """字幕配置"""

    fontname: str = 'Arial'
    fontsize: int = 20
    primary_color: str = '#FFFFFF'
    secondary_color: str = '#000000'
    outline: int = 2
    shadow: int = 2
    position: str = 'bottom'  # top, center, bottom

    def to_dict(self) -> dict:
        """轉為字典"""
        return {
            'fontname': self.fontname,
            'fontsize': self.fontsize,
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'outline': self.outline,
            'shadow': self.shadow,
            'position': self.position,
        }
