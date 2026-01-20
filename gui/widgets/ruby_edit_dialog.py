"""
Ruby 編輯對話框

作用：
- 編輯單一文字的假名
"""

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)


class RubyEditDialog(QDialog):
    """Ruby 編輯對話框"""

    def __init__(self, text: str, ruby: str, parent=None):
        super().__init__(parent)
        # 文字內容
        self.text = text
        # 假名內容
        self.ruby = ruby
        # 輸入框
        self.ruby_input = None
        # 初始化 UI
        self._setup_ui()

    def _setup_ui(self):
        """建立 UI"""
        self.setWindowTitle("編輯假名")
        self.resize(320, 140)

        layout = QVBoxLayout()

        text_label = QLabel(f"文字：{self.text}")
        layout.addWidget(text_label)

        self.ruby_input = QLineEdit(self.ruby)
        self.ruby_input.setPlaceholderText("輸入假名（留空表示不顯示）")
        self.ruby_input.returnPressed.connect(self.accept)
        layout.addWidget(self.ruby_input)

        button_layout = QHBoxLayout()
        ok_btn = QPushButton("確定")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_ruby(self) -> str:
        """取得假名內容"""
        if not self.ruby_input:
            return ''
        return self.ruby_input.text()
