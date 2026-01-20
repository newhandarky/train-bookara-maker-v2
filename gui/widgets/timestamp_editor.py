"""
時間戳編輯器

作用：
- 編輯開始/結束時間（mm:ss.xx）
- 發出時間變更訊號
"""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QLabel
from PyQt5.QtCore import QRegExp


class TimeStampEditor(QWidget):
    """時間戳編輯器（開始/結束）"""

    # 變更訊號（start_time, end_time）
    changed = pyqtSignal(float, float)

    def __init__(self, start_time: float, end_time: float, parent=None):
        super().__init__(parent)
        # 開始時間
        self.start_time = start_time
        # 結束時間
        self.end_time = end_time
        # 上次有效開始時間
        self._last_valid_start = start_time
        # 上次有效結束時間
        self._last_valid_end = end_time
        # 初始化 UI
        self._setup_ui()

    def _setup_ui(self):
        """建立 UI"""
        # 版面配置
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # 時間格式驗證器
        time_validator = QRegExpValidator(QRegExp(r'^\d{2}:\d{2}\.\d{2}$'))

        # 開始時間輸入
        self.start_edit = QLineEdit(self._format_time(self.start_time))
        self.start_edit.setValidator(time_validator)
        self.start_edit.editingFinished.connect(self._on_edit_finished)
        layout.addWidget(self.start_edit)

        # 分隔符號
        layout.addWidget(QLabel('~'))

        # 結束時間輸入
        self.end_edit = QLineEdit(self._format_time(self.end_time))
        self.end_edit.setValidator(time_validator)
        self.end_edit.editingFinished.connect(self._on_edit_finished)
        layout.addWidget(self.end_edit)

        self.setLayout(layout)

    def set_times(self, start_time: float, end_time: float):
        """設定時間並更新 UI"""
        # 更新時間
        self.start_time = start_time
        self.end_time = end_time
        # 更新備援值
        self._last_valid_start = start_time
        self._last_valid_end = end_time
        # 更新輸入框
        self.start_edit.setText(self._format_time(start_time))
        self.end_edit.setText(self._format_time(end_time))

    def _format_time(self, seconds: float) -> str:
        """秒數轉換為 mm:ss.xx"""
        minutes = int(seconds) // 60  # 分鐘
        secs = int(seconds) % 60  # 秒數
        centisecs = int(round((seconds % 1) * 100))  # 厘秒
        return f"{minutes:02d}:{secs:02d}.{centisecs:02d}"

    def _parse_time(self, time_str: str) -> float:
        """將 mm:ss.xx 轉為秒數"""
        parts = time_str.split(':')  # 分割分鐘與秒
        minutes = int(parts[0])  # 分鐘
        secs_parts = parts[1].split('.')  # 分割秒與厘秒
        secs = int(secs_parts[0])  # 秒數
        centisecs = int(secs_parts[1])  # 厘秒
        return minutes * 60 + secs + centisecs / 100.0

    def _on_edit_finished(self):
        """編輯完成後驗證與更新"""
        try:
            # 解析輸入
            start_time = self._parse_time(self.start_edit.text())  # 開始時間
            end_time = self._parse_time(self.end_edit.text())  # 結束時間

            # 基本檢查
            if end_time <= start_time:
                raise ValueError("結束時間必須大於開始時間")

            # 更新狀態
            self.start_time = start_time
            self.end_time = end_time
            self._last_valid_start = start_time
            self._last_valid_end = end_time

            # 發送訊號
            self.changed.emit(start_time, end_time)
        except Exception:
            # 還原到上次有效值
            self.start_edit.setText(self._format_time(self._last_valid_start))
            self.end_edit.setText(self._format_time(self._last_valid_end))
