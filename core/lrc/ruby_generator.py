"""
假名自動標注工具

作用：
- 將文字轉為平假名
- 提供自動假名標注能力
"""

import re
from typing import Optional

try:
    from pykakasi import kakasi
except ImportError:
    kakasi = None


class RubyGenerator:
    """假名生成器"""

    def __init__(self):
        # kakasi 轉換器（可能為 None）
        self._converter = None
        if kakasi:
            converter = kakasi()
            converter.setMode('J', 'H')  # 日文轉平假名
            converter.setMode('K', 'H')  # 片假名轉平假名
            converter.setMode('H', 'H')  # 平假名保持
            self._converter = converter.getConverter()

    def generate_ruby(self, text: str) -> str:
        """產生平假名（若無法生成則回傳空字串）"""
        if not text:
            return ''

        # 純平假名/片假名不自動標注
        if self._is_hiragana(text):
            return ''
        if self._is_katakana(text):
            return ''

        # 英數與符號不自動生成
        if self._is_ascii_or_symbol(text):
            return ''

        # 有 kakasi 則使用自動轉換
        if self._converter:
            return self._converter.do(text)

        return ''

    def _is_hiragana(self, text: str) -> bool:
        """判斷是否為平假名"""
        return bool(re.fullmatch(r'[\u3040-\u309F]+', text))

    def _is_katakana(self, text: str) -> bool:
        """判斷是否為片假名"""
        return bool(re.fullmatch(r'[\u30A0-\u30FF]+', text))

    def _is_ascii_or_symbol(self, text: str) -> bool:
        """判斷是否為英數或符號"""
        return bool(re.fullmatch(r'[0-9A-Za-z\s\W]+', text))

    def _katakana_to_hiragana(self, text: str) -> str:
        """片假名轉平假名"""
        chars = []
        for char in text:
            code = ord(char)
            if 0x30A1 <= code <= 0x30F6:
                chars.append(chr(code - 0x60))
            else:
                chars.append(char)
        return ''.join(chars)
