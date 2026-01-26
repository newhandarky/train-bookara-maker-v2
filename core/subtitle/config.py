"""
字幕樣式設定
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class SubtitleConfig:
    """字幕配置"""

    fontname: str = 'Arial'
    fontsize: int = 20
    primary_color: str = '#FFFFFF'
    secondary_color: str = '#000000'
    spacing: int = 0
    bold: bool = False
    italic: bool = False
    ruby_fontname: str = ''
    ruby_fontsize: int = 0  # 0 表示自動（依據主字級）
    ruby_color: str = '#DDDDDD'
    ruby_offset_y: int = 24
    outline: int = 2
    shadow: int = 2
    position: str = 'bottom'  # top, center, bottom
    margin_l: int = 0
    margin_r: int = 0
    top_margin: int = 30
    bottom_margin: int = 30
    lead_in_sec: float = 0.7
    tail_hold_sec: float = 0.3
    color_groups: Dict[str, Dict[str, str]] = field(
        default_factory=lambda: {
            'A': {'name': 'A', 'primary_color': '#FF0000', 'secondary_color': '#808080'},
            'B': {'name': 'B', 'primary_color': '#0000FF', 'secondary_color': '#808080'},
        }
    )
    enabled_groups: List[str] = field(default_factory=lambda: ['A', 'B'])
    color_history: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """轉為字典"""
        return {
            'fontname': self.fontname,
            'fontsize': self.fontsize,
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'spacing': self.spacing,
            'bold': self.bold,
            'italic': self.italic,
            'ruby_fontname': self.ruby_fontname,
            'ruby_fontsize': self.ruby_fontsize,
            'ruby_color': self.ruby_color,
            'ruby_offset_y': self.ruby_offset_y,
            'outline': self.outline,
            'shadow': self.shadow,
            'position': self.position,
            'margin_l': self.margin_l,
            'margin_r': self.margin_r,
            'top_margin': self.top_margin,
            'bottom_margin': self.bottom_margin,
            'lead_in_sec': self.lead_in_sec,
            'tail_hold_sec': self.tail_hold_sec,
            'color_groups': self.color_groups,
            'enabled_groups': self.enabled_groups,
            'color_history': self.color_history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SubtitleConfig':
        """由字典建立設定"""
        if not data:
            return cls()
        default = cls().to_dict()
        default.update(data)
        config = cls(**default)
        config.color_groups = cls._normalize_groups(config.color_groups)
        if not config.enabled_groups:
            config.enabled_groups = list(config.color_groups.keys())[:2] or ['A']
        if not isinstance(config.color_history, list):
            config.color_history = []
        return config

    @staticmethod
    def _normalize_groups(groups: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
        """補齊群組欄位"""
        normalized = {}
        for group_id, group in (groups or {}).items():
            if not isinstance(group, dict):
                group = {}
            name = group.get('name') or group_id
            normalized[group_id] = {
                'name': name,
                'primary_color': group.get('primary_color', '#FFFFFF'),
                'secondary_color': group.get('secondary_color', '#808080'),
            }
        return normalized
