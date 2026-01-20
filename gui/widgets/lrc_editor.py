"""
LRC 編輯表格

作用：
- 顯示 LRC 時間軸資料
- 編輯時間戳、文字、假名
"""

from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QVBoxLayout, QHBoxLayout, QPushButton

from core.lrc import LrcLine, LrcTimeline, LrcWord, RubyPair
from gui.widgets.timestamp_editor import TimeStampEditor


class LrcTimelineEditor(QTableWidget):
    """LRC 編輯表格"""

    # 時間變更訊號（line_idx, word_idx, start, end）
    timing_changed = pyqtSignal(int, int, float, float)
    # 文字變更訊號（line_idx, word_idx, text）
    text_changed = pyqtSignal(int, int, str)
    # 假名變更訊號（line_idx, word_idx, ruby）
    ruby_changed = pyqtSignal(int, int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        # LRC 時間軸
        self.timeline: Optional[LrcTimeline] = None  # LRC 時間軸
        # 內部更新鎖
        self._is_updating = False  # 內部更新鎖
        # 列索引映射
        self._row_map = {}  # (line_idx, word_idx) -> row
        # 初始化 UI
        self._setup_ui()
        # 監聽文字變更
        self.itemChanged.connect(self._on_item_changed)

    def _setup_ui(self):
        """設定表格欄位"""
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(['行', '時間', '字', '假名'])
        self.setColumnWidth(0, 60)
        self.setColumnWidth(1, 200)

        header = self.horizontalHeader()  # 表頭物件
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
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
            for word_idx, word in enumerate(line.words):
                row = self.rowCount()  # 目前列數
                self.insertRow(row)
                self._row_map[(line_idx, word_idx)] = row

                # 行號
                line_item = QTableWidgetItem(str(line_idx + 1))  # 行號項目
                line_item.setFlags(Qt.ItemIsEnabled)
                self.setItem(row, 0, line_item)

                # 時間編輯器
                time_editor = TimeStampEditor(word.start_time, word.end_time, self)  # 時間編輯器
                time_editor.changed.connect(
                    lambda start, end, li=line_idx, wi=word_idx: self._on_time_changed(li, wi, start, end)
                )
                self.setCellWidget(row, 1, time_editor)

                # 文字欄
                text_item = QTableWidgetItem(word.text)  # 文字項目
                text_item.setData(Qt.UserRole, ('text', line_idx, word_idx))
                self.setItem(row, 2, text_item)

                # 假名欄
                ruby_text = word.ruby_pair.ruby if word.ruby_pair else ''  # 假名文字
                ruby_item = QTableWidgetItem(ruby_text)  # 假名項目
                ruby_item.setData(Qt.UserRole, ('ruby', line_idx, word_idx))
                self.setItem(row, 3, ruby_item)

        self._is_updating = False

    def update_word_time(self, line_idx: int, word_idx: int, start_time: float, end_time: float):
        """更新指定詞的時間"""
        if not self.timeline:
            return
        word = self.timeline.lines[line_idx].words[word_idx]  # 目標詞
        word.start_time = start_time
        word.end_time = end_time

        row = self._row_map.get((line_idx, word_idx))
        if row is None:
            return
        time_editor = self.cellWidget(row, 1)
        if isinstance(time_editor, TimeStampEditor):
            time_editor.set_times(start_time, end_time)

    def highlight_word(self, line_idx: int, word_idx: int):
        """高亮指定詞"""
        row = self._row_map.get((line_idx, word_idx))
        if row is None:
            return
        self.setCurrentCell(row, 2)
        self.selectRow(row)
        self.scrollToItem(self.item(row, 2))

    def _on_time_changed(self, line_idx: int, word_idx: int, start_time: float, end_time: float):
        """時間變更事件"""
        if not self.timeline:
            return
        word = self.timeline.lines[line_idx].words[word_idx]  # 目標詞
        word.start_time = start_time
        word.end_time = end_time
        self.timing_changed.emit(line_idx, word_idx, start_time, end_time)

    def _on_item_changed(self, item: QTableWidgetItem):
        """文字或假名變更事件"""
        if self._is_updating or not self.timeline:
            return
        data = item.data(Qt.UserRole)  # 內部標記
        if not data:
            return

        field, line_idx, word_idx = data  # 欄位與索引
        if field == 'text':
            self._on_text_changed(line_idx, word_idx, item.text())
        elif field == 'ruby':
            self._on_ruby_changed(line_idx, word_idx, item.text())

    def _on_text_changed(self, line_idx: int, word_idx: int, text: str):
        """文字內容變更"""
        word = self.timeline.lines[line_idx].words[word_idx]  # 目標詞
        word.text = text
        self.text_changed.emit(line_idx, word_idx, text)

    def _on_ruby_changed(self, line_idx: int, word_idx: int, ruby_text: str):
        """假名內容變更"""
        word = self.timeline.lines[line_idx].words[word_idx]  # 目標詞
        if ruby_text:
            word.ruby_pair = RubyPair(kanji=word.text, ruby=ruby_text)
        else:
            word.ruby_pair = None
        self.ruby_changed.emit(line_idx, word_idx, ruby_text)

    def add_line(self, text: str = ''):
        """新增一行歌詞"""
        if not self.timeline:
            self.timeline = LrcTimeline()  # 新時間軸

        # 新增預設詞
        word = LrcWord(text=text, start_time=0.0, end_time=0.5)  # 新詞
        line = LrcLine(words=[word])  # 新行
        self.timeline.add_line(line)
        self.refresh()

    def delete_line(self, line_idx: int):
        """刪除指定行"""
        if not self.timeline:
            return
        if line_idx < 0 or line_idx >= len(self.timeline.lines):
            return
        self.timeline.remove_line(line_idx)
        self.refresh()


class LrcEditorDialog(QDialog):
    """LRC 編輯對話框"""

    def __init__(self, timeline: LrcTimeline, parent=None):
        super().__init__(parent)
        # 時間軸
        self.timeline = timeline  # 時間軸
        # UI 元件
        self.editor = LrcTimelineEditor(self)  # 編輯器
        # 空時間軸補一行
        if not self.timeline.lines:
            word = LrcWord(text='', start_time=0.0, end_time=0.5)  # 預設詞
            line = LrcLine(words=[word])  # 預設行
            self.timeline.add_line(line)
        # 初始化 UI
        self._setup_ui()

    def _setup_ui(self):
        """設定對話框 UI"""
        self.setWindowTitle("LRC 編輯器")
        self.resize(900, 600)

        layout = QVBoxLayout()  # 主版面
        self.editor.set_timeline(self.timeline)
        layout.addWidget(self.editor)

        # 按鈕區
        button_layout = QHBoxLayout()  # 按鈕列

        add_btn = QPushButton("新增一行")  # 新增按鈕
        add_btn.clicked.connect(self._on_add_line)
        button_layout.addWidget(add_btn)

        delete_btn = QPushButton("刪除所選行")  # 刪除按鈕
        delete_btn.clicked.connect(self._on_delete_line)
        button_layout.addWidget(delete_btn)

        close_btn = QPushButton("關閉")  # 關閉按鈕
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _on_add_line(self):
        """新增一行"""
        self.editor.add_line()

    def _on_delete_line(self):
        """刪除目前所選行"""
        current_row = self.editor.currentRow()  # 目前列
        if current_row < 0:
            return
        line_item = self.editor.item(current_row, 0)  # 行號項目
        if not line_item:
            return
        line_idx = int(line_item.text()) - 1  # 行索引
        self.editor.delete_line(line_idx)
