"""
LRC 資料結構定義

作用：
- 定義 LRC 的核心資料結構
- 提供時間軸查詢能力
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RubyPair:
    """漢字與假名的對應資料"""

    kanji: str  # 漢字文字
    ruby: str  # 假名文字（平假名）


@dataclass
class LrcWord:
    """單一詞（或字）的時間資訊"""

    text: str  # 文字內容
    start_time: float  # 開始時間（秒）
    end_time: float  # 結束時間（秒）
    ruby_pair: Optional[RubyPair] = None  # 假名對應（可為空）


@dataclass
class LrcLine:
    """一行歌詞，包含多個詞（或字）"""

    words: List[LrcWord] = field(default_factory=list)  # 詞列表

    @property
    def text(self) -> str:
        """整行純文字內容（不含假名）"""
        return ''.join(word.text for word in self.words)

    @property
    def start_time(self) -> float:
        """這一行的開始時間"""
        if not self.words:
            return 0.0
        return self.words[0].start_time

    @property
    def end_time(self) -> float:
        """這一行的結束時間"""
        if not self.words:
            return 0.0
        return self.words[-1].end_time


class LrcTimeline:
    """LRC 完整時間軸"""

    def __init__(self):
        # 歌詞行列表
        self.lines: List[LrcLine] = []
        # 全局時間偏移（秒）
        self.offset: float = 0.0
        # 元資訊（藝人、歌名、專輯）
        self.metadata = {
            'artist': '',
            'title': '',
            'album': '',
        }

    def add_line(self, line: LrcLine):
        """新增一行歌詞"""
        self.lines.append(line)

    def remove_line(self, index: int):
        """刪除指定索引的歌詞行"""
        self.lines.pop(index)

    def get_word_at_time(self, time_seconds: float) -> Optional[LrcWord]:
        """在指定時間找到正在播放的詞（或字）"""
        for line in self.lines:
            for word in line.words:
                if word.start_time <= time_seconds < word.end_time:
                    return word
        return None
