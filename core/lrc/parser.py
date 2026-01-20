"""
LRC 解析器

作用：
- 解析 LRC 文字或檔案內容
- 支援 .txt 歌詞載入
- 轉換為 LrcTimeline 結構
"""

import os
import re
from typing import List, Optional, Tuple

from .model import LrcLine, LrcTimeline, LrcWord, RubyPair
from .ruby_generator import RubyGenerator


class LrcParser:
    """歌詞解析器"""

    def __init__(self, default_word_duration: float = 0.5):
        # 預設詞時長（秒）
        self.default_word_duration = default_word_duration

    def parse_file(self, file_path: str, auto_ruby: bool = True) -> LrcTimeline:
        """依副檔名自動解析檔案"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.txt':
            return self.parse_txt_file(file_path, auto_ruby=auto_ruby)
        if ext == '.lrc':
            return self.parse_lrc_file(file_path)
        if ext == '.bookara':
            raise NotImplementedError('尚未支援 .bookara 格式')
        raise ValueError(f'Unsupported format: {ext}')

    def parse_lrc_file(self, file_path: str) -> LrcTimeline:
        """解析 LRC 檔案"""
        content = self._read_text_file(file_path)
        return self.parse_string(content)

    def parse_txt_file(self, file_path: str, auto_ruby: bool = True) -> LrcTimeline:
        """解析 TXT 歌詞檔案"""
        content = self._read_text_file(file_path)
        return self.parse_txt_string(content, auto_ruby=auto_ruby)

    def parse_string(self, content: str) -> LrcTimeline:
        """解析 LRC 字串內容"""
        timeline = LrcTimeline()  # 時間軸物件

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            # 元資訊
            if line.startswith('[ar:') and line.endswith(']'):
                timeline.metadata['artist'] = line[4:-1]
                continue
            if line.startswith('[ti:') and line.endswith(']'):
                timeline.metadata['title'] = line[4:-1]
                continue
            if line.startswith('[al:') and line.endswith(']'):
                timeline.metadata['album'] = line[4:-1]
                continue
            if line.startswith('[offset:') and line.endswith(']'):
                offset_ms_str = line[8:-1]
                if offset_ms_str:
                    timeline.offset = float(offset_ms_str) / 1000.0
                continue

            # 歌詞行
            timestamp, text = self._parse_lrc_line(line)
            if timestamp is None:
                continue
            lrc_line = self._parse_content(timestamp, text)
            timeline.add_line(lrc_line)

        return timeline

    def parse_txt_string(self, content: str, auto_ruby: bool = True) -> LrcTimeline:
        """解析 TXT 字串內容（每行一句）"""
        timeline = LrcTimeline()  # 時間軸物件
        ruby_generator = RubyGenerator() if auto_ruby else None

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            words: List[LrcWord] = []
            for word_text, ruby_text in self._iter_text_with_ruby(line, ruby_generator):
                word = LrcWord(
                    text=word_text,
                    start_time=0.0,
                    end_time=self.default_word_duration,
                    ruby_pair=RubyPair(kanji=word_text, ruby=ruby_text) if ruby_text else None,
                )
                words.append(word)

            timeline.add_line(LrcLine(words=words))

        return timeline

    def parse_txt_line(self, line: str, auto_ruby: bool = True) -> List[LrcWord]:
        """解析單行 TXT 句子"""
        ruby_generator = RubyGenerator() if auto_ruby else None
        words: List[LrcWord] = []
        for word_text, ruby_text in self._iter_text_with_ruby(line, ruby_generator):
            word = LrcWord(
                text=word_text,
                start_time=0.0,
                end_time=self.default_word_duration,
                ruby_pair=RubyPair(kanji=word_text, ruby=ruby_text) if ruby_text else None,
            )
            words.append(word)
        return words

    def _parse_lrc_line(self, line: str) -> Tuple[Optional[float], str]:
        """
        解析單行 LRC：
        格式：[mm:ss.xx]內容
        """
        pattern = r'^\[(\d{2}):(\d{2})\.(\d{2})\](.*)$'
        match = re.match(pattern, line)
        if not match:
            return None, ''

        minutes_str, seconds_str, centisecs_str, content = match.groups()
        # 轉為秒數
        timestamp = int(minutes_str) * 60 + int(seconds_str) + int(centisecs_str) / 100.0
        return timestamp, content

    def _parse_content(self, start_time: float, content: str) -> LrcLine:
        """解析 LRC 歌詞內容並建立 LrcLine"""
        words: List[LrcWord] = []  # 詞列表
        current_time = start_time  # 時間游標

        for word_text, ruby_text in self._iter_text_with_ruby(content):
            ruby_pair = RubyPair(kanji=word_text, ruby=ruby_text) if ruby_text else None
            word = LrcWord(
                text=word_text,
                start_time=current_time,
                end_time=current_time + self.default_word_duration,
                ruby_pair=ruby_pair,
            )
            words.append(word)
            current_time += self.default_word_duration

        return LrcLine(words=words)

    def _iter_text_with_ruby(
        self,
        content: str,
        ruby_generator: Optional[RubyGenerator] = None,
    ):
        """逐字解析文字與假名"""
        pattern = re.compile(r'([^\{\}]+)\{([^}]*)\}|([^{}])')
        for match in pattern.finditer(content):
            text_with_ruby = match.group(1)
            ruby_text = match.group(2)
            plain_text = match.group(3)

            word_text = text_with_ruby if text_with_ruby is not None else plain_text
            if word_text is None:
                continue

            if ruby_text is not None and ruby_text != '':
                yield word_text, ruby_text
                continue

            if ruby_generator:
                generated = ruby_generator.generate_ruby(word_text)
                yield word_text, generated if generated else ''
            else:
                yield word_text, ''

    def _read_text_file(self, file_path: str) -> str:
        """讀取文字檔案並嘗試編碼"""
        encodings = ['utf-8-sig', 'utf-8', 'gbk']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file_handle:
                    return file_handle.read()
            except UnicodeDecodeError:
                continue
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file_handle:
            return file_handle.read()
