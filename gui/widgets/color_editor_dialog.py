"""
顏色編輯器對話框
"""

from typing import List

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QLineEdit,
    QColorDialog,
    QWidget,
)


class ColorEditorDialog(QDialog):
    """顏色編輯器對話框"""

    def __init__(self, title: str, current_hex: str, history: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._history = [c.upper() for c in (history or [])]
        self._is_updating = False
        self._color = QColor(current_hex or '#FFFFFF')
        self._setup_ui()
        self._load_color(self._color)

    def _setup_ui(self):
        layout = QVBoxLayout()

        preview_row = QHBoxLayout()
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(120, 40)
        self.preview_label.setStyleSheet("border: 1px solid #333;")
        preview_row.addWidget(QLabel("預覽"))
        preview_row.addWidget(self.preview_label)
        preview_row.addStretch()
        layout.addLayout(preview_row)

        self._rgb_controls = {}
        for channel, label in [('r', 'R'), ('g', 'G'), ('b', 'B')]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 255)
            spin = QSpinBox()
            spin.setRange(0, 255)
            row.addWidget(slider)
            row.addWidget(spin)
            layout.addLayout(row)
            slider.valueChanged.connect(lambda value, ch=channel: self._on_rgb_changed(ch, value))
            spin.valueChanged.connect(lambda value, ch=channel: self._on_rgb_changed(ch, value))
            self._rgb_controls[channel] = (slider, spin)

        hex_row = QHBoxLayout()
        hex_row.addWidget(QLabel("Hex"))
        self.hex_edit = QLineEdit()
        self.hex_edit.setPlaceholderText("#RRGGBB")
        self.hex_edit.textChanged.connect(self._on_hex_changed)
        hex_row.addWidget(self.hex_edit)
        pick_btn = QPushButton("色盤/取色")
        pick_btn.clicked.connect(self._pick_color)
        hex_row.addWidget(pick_btn)
        layout.addLayout(hex_row)

        self.history_container = QWidget()
        self.history_layout = QHBoxLayout()
        self.history_layout.setContentsMargins(0, 0, 0, 0)
        self.history_container.setLayout(self.history_layout)
        layout.addWidget(QLabel("最近使用"))
        layout.addWidget(self.history_container)
        self._refresh_history_buttons()

        button_row = QHBoxLayout()
        button_row.addStretch()
        ok_btn = QPushButton("確認")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(ok_btn)
        button_row.addWidget(cancel_btn)
        layout.addLayout(button_row)

        self.setLayout(layout)

    def _refresh_history_buttons(self):
        while self.history_layout.count():
            item = self.history_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        for color in self._history[:12]:
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setStyleSheet(f"background:{color}; border:1px solid #333;")
            btn.clicked.connect(lambda _checked=False, c=color: self._load_color(QColor(c)))
            self.history_layout.addWidget(btn)
        self.history_layout.addStretch()

    def _pick_color(self):
        color = QColorDialog.getColor(self._color, self, "選擇顏色")
        if color.isValid():
            self._load_color(color)

    def _on_rgb_changed(self, channel: str, value: int):
        if self._is_updating:
            return
        r, g, b = self._color.red(), self._color.green(), self._color.blue()
        if channel == 'r':
            r = value
        elif channel == 'g':
            g = value
        else:
            b = value
        self._load_color(QColor(r, g, b))

    def _on_hex_changed(self, text: str):
        if self._is_updating:
            return
        text = text.strip()
        if not text:
            return
        if not text.startswith('#'):
            text = f"#{text}"
        if len(text) != 7:
            return
        color = QColor(text)
        if color.isValid():
            self._load_color(color)

    def _load_color(self, color: QColor):
        if not color.isValid():
            return
        self._is_updating = True
        self._color = color
        r, g, b = color.red(), color.green(), color.blue()
        self._rgb_controls['r'][0].setValue(r)
        self._rgb_controls['r'][1].setValue(r)
        self._rgb_controls['g'][0].setValue(g)
        self._rgb_controls['g'][1].setValue(g)
        self._rgb_controls['b'][0].setValue(b)
        self._rgb_controls['b'][1].setValue(b)
        hex_text = color.name().upper()
        self.hex_edit.setText(hex_text)
        self.preview_label.setStyleSheet(f"background:{hex_text}; border: 1px solid #333;")
        self._is_updating = False

    def get_color_hex(self) -> str:
        return self._color.name().upper()

    def get_history(self) -> List[str]:
        color = self.get_color_hex()
        history = [color] + [c for c in self._history if c != color]
        return history[:20]
