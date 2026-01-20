"""
輸出選項對話框

作用：
- 選擇要輸出的音訊檔案
"""

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QCheckBox,
)


class OutputOptionsDialog(QDialog):
    """輸出選項對話框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # 勾選項目
        self.checkboxes = {}
        # 初始化 UI
        self._setup_ui()

    def _setup_ui(self):
        """建立 UI"""
        self.setWindowTitle("選擇輸出音訊")
        self.resize(360, 240)

        layout = QVBoxLayout()

        layout.addWidget(QLabel("請選擇要輸出的音訊檔案："))

        self._add_checkbox(layout, "original", "original.wav（原始音訊）", True)
        self._add_checkbox(layout, "music", "music.wav（去人聲音樂）", True)
        self._add_checkbox(layout, "vocal", "vocal.wav（人聲）", False)
        self._add_checkbox(layout, "drums", "drums.wav（鼓）", False)
        self._add_checkbox(layout, "bass", "bass.wav（貝斯）", False)
        self._add_checkbox(layout, "other", "other.wav（其他）", False)

        button_layout = QHBoxLayout()
        ok_btn = QPushButton("確定")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _add_checkbox(self, layout, key: str, text: str, checked: bool):
        """新增勾選項"""
        checkbox = QCheckBox(text)
        checkbox.setChecked(checked)
        layout.addWidget(checkbox)
        self.checkboxes[key] = checkbox

    def get_selected_outputs(self) -> dict:
        """取得勾選結果"""
        return {key: checkbox.isChecked() for key, checkbox in self.checkboxes.items()}
