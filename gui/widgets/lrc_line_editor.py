"""
LRC 句子編輯表格

作用：
- 以「一行一句」方式顯示
- Ruby 只顯示在漢字上方
- 提供字級游標與鍵盤操作
"""

from typing import Optional
import html
import re
from functools import partial

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QHeaderView,
)

from core.lrc import LrcLine, LrcParser, LrcTimeline, LrcWord, RubyPair
from gui.widgets.ruby_edit_dialog import RubyEditDialog


class LrcLineEditor(QTableWidget):
    """LRC 句子編輯表格"""

    # 句子變更訊號（line_idx, text）
    line_text_changed = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        # LRC 時間軸
        self.timeline: Optional[LrcTimeline] = None  # LRC 時間軸
        # 內部更新鎖
        self._is_updating = False  # 內部更新鎖
        # 解析器
        self._parser = LrcParser()  # 歌詞解析器
        # 行索引映射
        self._row_map = {}  # line_idx -> row
        # 游標位置
        self._current_line_idx = 0  # 目前行
        self._current_word_idx = 0  # 目前字
        # 初始化 UI
        self._setup_ui()
        # 監聽文字變更
        self.itemChanged.connect(self._on_item_changed)
        self.cellClicked.connect(self._on_cell_clicked)

    def _setup_ui(self):
        """設定表格欄位"""
        self.setFocusPolicy(Qt.StrongFocus)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(['行', '時間', '顯示', '句子'])
        self.setColumnWidth(0, 60)
        self.setColumnWidth(1, 140)

        header = self.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        self.verticalHeader().setDefaultSectionSize(48)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setStyleSheet(
            "QTableWidget { color: #f5f5f5; }"
            "QTableWidget::item { color: #f5f5f5; }"
            "QTableWidget::item:selected { color: #f5f5f5; }"
            "QHeaderView::section { color: #f5f5f5; }"
        )

    def set_timeline(self, timeline: LrcTimeline):
        """設定時間軸並刷新"""
        self.timeline = timeline
        self.refresh()

    def refresh(self):
        """刷新表格內容"""
        self._is_updating = True
        self.setRowCount(0)
        self._row_map = {}

        if not self.timeline:
            self._is_updating = False
            return

        for line_idx, line in enumerate(self.timeline.lines):
            row = self.rowCount()
            self.insertRow(row)
            self._row_map[line_idx] = row

            # 行號
            line_item = QTableWidgetItem(str(line_idx + 1))
            line_item.setFlags(Qt.ItemIsEnabled)
            self.setItem(row, 0, line_item)

            # 時間顯示（唯讀）
            time_text = self._format_time_range(line)
            time_item = QTableWidgetItem(time_text)
            time_item.setFlags(Qt.ItemIsEnabled)
            self.setItem(row, 1, time_item)

            # Ruby 顯示
            display_label = QLabel(self._build_ruby_html(line, line_idx))
            display_label.setTextFormat(Qt.RichText)
            display_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            display_label.setStyleSheet("color: #f5f5f5;")
            display_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
            display_label.setOpenExternalLinks(False)
            display_label.linkActivated.connect(
                partial(self._on_display_link_clicked, line_idx),
            )
            self.setCellWidget(row, 2, display_label)

            # 句子文字（可編輯，純文字）
            text_item = QTableWidgetItem(line.text)
            text_item.setData(Qt.UserRole, ('text', line_idx))
            self.setItem(row, 3, text_item)

        self._is_updating = False
        self._ensure_cursor()
        self._update_line_display(self._current_line_idx)

    def update_word_time(self, line_idx: int, word_idx: int, start_time: float, end_time: float):
        """更新指定詞的時間"""
        if not self.timeline:
            return
        line = self.timeline.lines[line_idx]
        word = line.words[word_idx]
        word.start_time = start_time
        word.end_time = end_time
        self._update_line_time(line_idx)

    def highlight_word(self, line_idx: int, word_idx: int):
        """高亮指定字"""
        self.set_cursor(line_idx, word_idx)

    def set_cursor(self, line_idx: int, word_idx: int):
        """設定游標位置"""
        if not self.timeline or not self.timeline.lines:
            return
        line_idx = max(0, min(line_idx, len(self.timeline.lines) - 1))
        words = self.timeline.lines[line_idx].words
        if not words:
            return
        word_idx = max(0, min(word_idx, len(words) - 1))

        prev_line_idx = self._current_line_idx
        self._current_line_idx = line_idx
        self._current_word_idx = word_idx

        # 更新顯示
        self._update_line_display(prev_line_idx)
        self._update_line_display(self._current_line_idx)

        row = self._row_map.get(self._current_line_idx)
        if row is not None:
            self.setCurrentCell(row, 3)
            self.selectRow(row)
            self.scrollToItem(self.item(row, 3))
        self.setFocus()

    def _on_item_changed(self, item: QTableWidgetItem):
        """文字變更事件"""
        if self._is_updating or not self.timeline:
            return
        data = item.data(Qt.UserRole)
        if not data:
            return

        field, line_idx = data
        if field != 'text':
            return
        self._on_line_text_changed(line_idx, item.text())

    def _on_cell_clicked(self, row: int, _column: int):
        """滑鼠點擊行時更新游標"""
        if not self.timeline:
            return
        line_idx = next((idx for idx, mapped in self._row_map.items() if mapped == row), row)
        self.set_cursor(line_idx, 0)

    def _on_display_link_clicked(self, line_idx: int, link: str):
        """點擊顯示區文字時定位游標"""
        if not link.startswith('w'):
            return
        try:
            word_idx = int(link[1:])
        except ValueError:
            return
        self.set_cursor(line_idx, word_idx)

    def _on_line_text_changed(self, line_idx: int, text: str):
        """句子內容變更"""
        line = self.timeline.lines[line_idx]
        line.words = self._parse_line_words(text)
        self._update_line_display(line_idx)
        self.set_cursor(line_idx, 0)
        self.line_text_changed.emit(line_idx, text)

    def _parse_line_words(self, text: str) -> list:
        """將句子解析為詞列表（含假名）"""
        if not text:
            return []
        words = self._parser.parse_txt_line(text, auto_ruby=True)
        return [LrcWord(w.text, w.start_time, w.end_time, w.ruby_pair) for w in words]

    def _update_line_display(self, line_idx: int):
        """更新行顯示"""
        if not self.timeline:
            return
        if line_idx < 0 or line_idx >= len(self.timeline.lines):
            return
        line = self.timeline.lines[line_idx]
        row = self._row_map.get(line_idx)
        if row is None:
            return

        # 更新時間
        time_item = self.item(row, 1)
        if time_item:
            time_item.setText(self._format_time_range(line))

        # 更新 Ruby 顯示
        display_label = self.cellWidget(row, 2)
        if isinstance(display_label, QLabel):
            display_label.setText(self._build_ruby_html(line, line_idx))

        # 更新句子文字
        text_item = self.item(row, 3)
        if text_item:
            self._is_updating = True
            text_item.setText(line.text)
            self._is_updating = False

    def _update_line_time(self, line_idx: int):
        """更新行時間顯示"""
        if not self.timeline:
            return
        line = self.timeline.lines[line_idx]
        row = self._row_map.get(line_idx)
        if row is None:
            return
        time_item = self.item(row, 1)
        if time_item:
            time_item.setText(self._format_time_range(line))

    def _format_time_range(self, line: LrcLine) -> str:
        """格式化時間區間"""
        start = self._format_time(line.start_time)
        end = self._format_time(line.end_time)
        return f"{start} ~ {end}"

    def _format_time(self, seconds: float) -> str:
        """格式化時間"""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        centisecs = int(round((seconds % 1) * 100))
        return f"{minutes:02d}:{secs:02d}.{centisecs:02d}"

    def _build_ruby_html(self, line: LrcLine, line_idx: int) -> str:
        """建立 Ruby 顯示 HTML"""
        ruby_cells = []
        text_cells = []
        text_parts = []
        has_ruby = False
        highlight_idx = self._current_word_idx if line_idx == self._current_line_idx else None

        base_style = "color:#f5f5f5;"
        highlight_style = "color:#ffd54f; font-weight:600;"

        for index, word in enumerate(line.words):
            ruby_text = word.ruby_pair.ruby if word.ruby_pair else ''
            show_ruby = bool(ruby_text) and self._has_kanji(word.text)
            if show_ruby:
                has_ruby = True

            word_text = html.escape(word.text)
            ruby_text = html.escape(ruby_text)
            if highlight_idx is not None and index == highlight_idx:
                word_text = f"<span style='{highlight_style}'>{word_text}</span>"
                ruby_text = f"<span style='{highlight_style}'>{ruby_text}</span>"
            else:
                word_text = f"<span style='{base_style}'>{word_text}</span>"
                ruby_text = f"<span style='{base_style}'>{ruby_text}</span>"

            link_text = f"<a href='w{index}' style='text-decoration:none;'>{word_text}</a>"

            text_parts.append(link_text)
            text_cells.append(f"<td align='center'>{link_text}</td>")
            ruby_cells.append(f"<td align='center'>{ruby_text if show_ruby else '&nbsp;'}</td>")

        if not text_parts:
            return ''
        if not has_ruby:
            return ''.join(text_parts)

        return (
            "<table cellspacing='0' cellpadding='0'>"
            "<tr>" + ''.join(ruby_cells) + "</tr>"
            "<tr>" + ''.join(text_cells) + "</tr>"
            "</table>"
        )

    def _has_kanji(self, text: str) -> bool:
        """判斷是否包含漢字"""
        return bool(re.search(r'[\u3400-\u9FFF]', text))

    def _ensure_cursor(self):
        """確保游標有效"""
        if not self.timeline or not self.timeline.lines:
            return
        self._current_line_idx = max(0, min(self._current_line_idx, len(self.timeline.lines) - 1))
        current_line = self.timeline.lines[self._current_line_idx]
        if not current_line.words:
            self._current_word_idx = 0
            return
        self._current_word_idx = max(0, min(self._current_word_idx, len(current_line.words) - 1))

    def keyPressEvent(self, event):
        """鍵盤操作"""
        if not self.timeline or not self.timeline.lines:
            super().keyPressEvent(event)
            return

        key = event.key()
        if key in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
            self._handle_cursor_move(key)
            return
        if key == Qt.Key_F2 or (event.modifiers() & Qt.ControlModifier and key == Qt.Key_R):
            self.edit_current_ruby()
            return

        super().keyPressEvent(event)

    def _handle_cursor_move(self, key):
        """處理游標移動"""
        line_idx = self._current_line_idx
        word_idx = self._current_word_idx

        if key == Qt.Key_Left:
            if word_idx > 0:
                word_idx -= 1
            elif line_idx > 0:
                line_idx -= 1
                word_idx = max(0, len(self.timeline.lines[line_idx].words) - 1)
        elif key == Qt.Key_Right:
            line_words = self.timeline.lines[line_idx].words
            if word_idx < len(line_words) - 1:
                word_idx += 1
            elif line_idx < len(self.timeline.lines) - 1:
                line_idx += 1
                word_idx = 0
        elif key == Qt.Key_Up:
            if line_idx > 0:
                line_idx -= 1
                word_idx = min(word_idx, len(self.timeline.lines[line_idx].words) - 1)
        elif key == Qt.Key_Down:
            if line_idx < len(self.timeline.lines) - 1:
                line_idx += 1
                word_idx = min(word_idx, len(self.timeline.lines[line_idx].words) - 1)

        self.set_cursor(line_idx, word_idx)

    def edit_current_ruby(self):
        """編輯目前字的假名"""
        if not self.timeline or not self.timeline.lines:
            return
        current_line = self.timeline.lines[self._current_line_idx]
        if not current_line.words:
            return

        word = current_line.words[self._current_word_idx]
        dialog = RubyEditDialog(
            word.text,
            word.ruby_pair.ruby if word.ruby_pair else '',
            self,
        )
        if dialog.exec_() != dialog.Accepted:
            return

        ruby_text = dialog.get_ruby().strip()
        if ruby_text:
            word.ruby_pair = RubyPair(kanji=word.text, ruby=ruby_text)
        else:
            word.ruby_pair = None

        self._update_line_display(self._current_line_idx)
