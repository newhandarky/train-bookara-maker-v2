"""
字幕顏色群組設定面板
"""

from typing import Dict, List, Optional
from pathlib import Path
import shutil

from PyQt5.QtCore import Qt, QRectF, QEvent, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QFontDatabase, QFontMetricsF, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QCheckBox,
    QGroupBox,
    QSpinBox,
    QDoubleSpinBox,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QComboBox,
    QMessageBox,
    QSizePolicy,
)

from core.subtitle import SubtitleConfig
from gui.widgets.color_editor_dialog import ColorEditorDialog


class KaraokeStylePreview(QWidget):
    """字幕樣式預覽元件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._font_family = 'Arial'
        self._font_size = 20
        self._outline = 2
        self._shadow = 2
        self._spacing = 0
        self._bold = False
        self._italic = False
        self._primary = QColor('#FFFFFF')
        self._secondary = QColor('#808080')
        self._sample_text = '永'
        self._preview_scale = 1.6
        self.setFixedWidth(220)
        self.setMinimumHeight(130)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def set_style(
        self,
        font_family: str,
        font_size: int,
        outline: int,
        shadow: int,
        spacing: int,
        bold: bool,
        italic: bool,
        primary: QColor,
        secondary: QColor,
    ):
        self._font_family = font_family or 'Arial'
        self._font_size = max(1, int(font_size))
        self._outline = max(0, int(outline))
        self._shadow = max(0, int(shadow))
        self._spacing = int(spacing)
        self._bold = bool(bold)
        self._italic = bool(italic)
        self._primary = primary if primary.isValid() else QColor('#FFFFFF')
        self._secondary = secondary if secondary.isValid() else QColor('#808080')
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        rect = self.rect()
        painter.fillRect(rect, QColor('#d0d0d0'))
        border_pen = QPen(QColor('#000000'))
        border_pen.setWidth(1)
        painter.setPen(border_pen)
        painter.drawRect(rect.adjusted(0, 0, -1, -1))

        content = rect.adjusted(8, 8, -8, -8)
        label_font = QFont(self._font_family, max(9, int(self._font_size * 0.45)))
        label_metrics = QFontMetricsF(label_font)
        label_height = label_metrics.height()
        label_y = content.top() + label_metrics.ascent()

        box_top = content.top() + int(label_height) + 4
        gap = 8
        box_width = int((content.width() - gap) / 2)
        box_height = max(10, content.bottom() - box_top)

        left_rect = QRectF(content.left(), box_top, box_width, box_height)
        right_rect = QRectF(content.left() + box_width + gap, box_top, box_width, box_height)

        painter.setFont(label_font)
        painter.setPen(QColor('#b0b0b0'))
        painter.drawText(QRectF(left_rect.left(), content.top(), left_rect.width(), label_height), Qt.AlignLeft, "唱前")
        painter.drawText(QRectF(right_rect.left(), content.top(), right_rect.width(), label_height), Qt.AlignLeft, "唱後")

        self._draw_sample(painter, left_rect, self._secondary)
        self._draw_sample(painter, right_rect, self._primary)

    def _draw_sample(self, painter: QPainter, rect: QRectF, color: QColor):
        sample_font = QFont(self._font_family, max(1, int(self._font_size * self._preview_scale)))
        sample_font.setLetterSpacing(QFont.AbsoluteSpacing, self._spacing)
        sample_font.setBold(self._bold)
        sample_font.setItalic(self._italic)
        painter.setFont(sample_font)
        metrics = QFontMetricsF(sample_font)

        text_width = metrics.horizontalAdvance(self._sample_text)
        text_height = metrics.height()
        x = rect.center().x() - text_width / 2
        y = rect.center().y() + (metrics.ascent() - metrics.descent()) / 2

        path = QPainterPath()
        path.addText(x, y, sample_font, self._sample_text)

        if self._shadow > 0:
            painter.save()
            painter.translate(self._shadow, self._shadow)
            painter.fillPath(path, QColor(0, 0, 0, 150))
            painter.restore()

        if self._outline > 0:
            self._draw_triple_outline(painter, path)

        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawPath(path)

    def _draw_triple_outline(self, painter: QPainter, path: QPainterPath):
        widths = [2.0, 2.0, 2.0]
        colors = [QColor('#FFFFFF'), QColor('#000000'), QColor('#FFFFFF')]
        for width, color in zip(widths, colors):
            pen = QPen(color)
            pen.setWidthF(max(1.0, width))
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)


class ColorGroupPanel(QWidget):
    """字幕顏色群組設定面板"""

    config_changed = pyqtSignal(dict)

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.config = SubtitleConfig.from_dict(project.subtitle_config if project else {})
        self._group_controls: Dict[str, QWidget] = {}
        self._current_group_id: Optional[str] = None
        self._fonts_dir = Path('resources/fonts')
        self._fonts_dir.mkdir(parents=True, exist_ok=True)
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        """建立 UI"""
        layout = QHBoxLayout()

        # 左側：群組清單
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("群組清單"))
        self.group_list = QListWidget()
        self.group_list.currentRowChanged.connect(self._on_group_selected)
        left_panel.addWidget(self.group_list)

        group_btn_row = QHBoxLayout()
        add_btn = QPushButton("新增")
        add_btn.clicked.connect(self._add_group)
        dup_btn = QPushButton("複製")
        dup_btn.clicked.connect(self._duplicate_group)
        del_btn = QPushButton("刪除")
        del_btn.clicked.connect(self._delete_group)
        group_btn_row.addWidget(add_btn)
        group_btn_row.addWidget(dup_btn)
        group_btn_row.addWidget(del_btn)
        left_panel.addLayout(group_btn_row)

        left_container = QWidget()
        left_container.setLayout(left_panel)
        layout.addWidget(left_container, 1)

        # 右側：設定區
        right_panel = QVBoxLayout()

        # 群組設定
        group_box = QGroupBox("群組設定")
        group_layout = QHBoxLayout()
        group_form_layout = QVBoxLayout()

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("群組名稱"))
        self.group_name_edit = QLineEdit()
        name_row.addWidget(self.group_name_edit)
        group_form_layout.addLayout(name_row)

        self.group_enabled_checkbox = QCheckBox("啟用此群組")
        group_form_layout.addWidget(self.group_enabled_checkbox)

        primary_row = QHBoxLayout()
        primary_row.addWidget(QLabel("唱中顏色"))
        self.group_primary_edit = QLineEdit()
        primary_btn = QPushButton("編輯")
        primary_btn.clicked.connect(lambda: self._edit_group_color('primary_color'))
        primary_row.addWidget(self.group_primary_edit)
        primary_row.addWidget(primary_btn)
        group_form_layout.addLayout(primary_row)

        secondary_row = QHBoxLayout()
        secondary_row.addWidget(QLabel("未唱顏色"))
        self.group_secondary_edit = QLineEdit()
        secondary_btn = QPushButton("編輯")
        secondary_btn.clicked.connect(lambda: self._edit_group_color('secondary_color'))
        secondary_row.addWidget(self.group_secondary_edit)
        secondary_row.addWidget(secondary_btn)
        group_form_layout.addLayout(secondary_row)

        group_form_layout.addStretch()

        self.style_preview = KaraokeStylePreview()
        group_layout.addLayout(group_form_layout, 1)
        group_layout.addWidget(self.style_preview, 0, Qt.AlignTop)
        group_box.setLayout(group_layout)
        right_panel.addWidget(group_box)

        # 字幕樣式
        style_box = QGroupBox("字幕樣式")
        style_layout = QVBoxLayout()

        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("字型"))
        self.font_combo = QComboBox()
        font_row.addWidget(self.font_combo, 1)
        import_font_btn = QPushButton("匯入字型")
        import_font_btn.clicked.connect(self._import_font)
        reload_font_btn = QPushButton("重新掃描")
        reload_font_btn.clicked.connect(self._scan_fonts)
        font_row.addWidget(import_font_btn)
        font_row.addWidget(reload_font_btn)
        style_layout.addLayout(font_row)

        font_style_row = QHBoxLayout()
        font_style_row.addWidget(QLabel("字型樣式"))
        self.bold_checkbox = QCheckBox("粗體")
        self.italic_checkbox = QCheckBox("斜體")
        font_style_row.addWidget(self.bold_checkbox)
        font_style_row.addWidget(self.italic_checkbox)
        font_style_row.addStretch()
        style_layout.addLayout(font_style_row)

        fontsize_row = QHBoxLayout()
        fontsize_row.addWidget(QLabel("字級"))
        self.fontsize_spin = QSpinBox()
        self.fontsize_spin.setRange(1, 200)
        fontsize_row.addWidget(self.fontsize_spin)
        style_layout.addLayout(fontsize_row)

        outline_row = QHBoxLayout()
        outline_row.addWidget(QLabel("描邊"))
        self.outline_spin = QSpinBox()
        self.outline_spin.setRange(0, 20)
        outline_row.addWidget(self.outline_spin)
        style_layout.addLayout(outline_row)

        shadow_row = QHBoxLayout()
        shadow_row.addWidget(QLabel("陰影"))
        self.shadow_spin = QSpinBox()
        self.shadow_spin.setRange(0, 20)
        shadow_row.addWidget(self.shadow_spin)
        style_layout.addLayout(shadow_row)

        spacing_row = QHBoxLayout()
        spacing_row.addWidget(QLabel("字距"))
        self.spacing_spin = QSpinBox()
        self.spacing_spin.setRange(-20, 50)
        spacing_row.addWidget(self.spacing_spin)
        style_layout.addLayout(spacing_row)

        margin_lr_row = QHBoxLayout()
        margin_lr_row.addWidget(QLabel("左邊界"))
        self.margin_l_spin = QSpinBox()
        self.margin_l_spin.setRange(0, 200)
        margin_lr_row.addWidget(self.margin_l_spin)
        margin_lr_row.addWidget(QLabel("右邊界"))
        self.margin_r_spin = QSpinBox()
        self.margin_r_spin.setRange(0, 200)
        margin_lr_row.addWidget(self.margin_r_spin)
        style_layout.addLayout(margin_lr_row)

        margin_tb_row = QHBoxLayout()
        margin_tb_row.addWidget(QLabel("上邊界"))
        self.top_margin_spin = QSpinBox()
        self.top_margin_spin.setRange(0, 200)
        margin_tb_row.addWidget(self.top_margin_spin)
        margin_tb_row.addWidget(QLabel("下邊界"))
        self.bottom_margin_spin = QSpinBox()
        self.bottom_margin_spin.setRange(0, 200)
        margin_tb_row.addWidget(self.bottom_margin_spin)
        style_layout.addLayout(margin_tb_row)

        timing_row = QHBoxLayout()
        timing_row.addWidget(QLabel("行首提早顯示 (s)"))
        self.lead_in_spin = QDoubleSpinBox()
        self.lead_in_spin.setRange(0, 10)
        self.lead_in_spin.setSingleStep(0.1)
        timing_row.addWidget(self.lead_in_spin)
        timing_row.addWidget(QLabel("行尾延長顯示 (s)"))
        self.tail_hold_spin = QDoubleSpinBox()
        self.tail_hold_spin.setRange(0, 10)
        self.tail_hold_spin.setSingleStep(0.1)
        timing_row.addWidget(self.tail_hold_spin)
        style_layout.addLayout(timing_row)

        style_box.setLayout(style_layout)
        right_panel.addWidget(style_box)

        # Ruby 設定
        ruby_box = QGroupBox("Ruby 設定")
        ruby_layout = QVBoxLayout()

        ruby_font_row = QHBoxLayout()
        ruby_font_row.addWidget(QLabel("Ruby 字型（留空跟主字）"))
        self.ruby_font_edit = QLineEdit()
        ruby_font_row.addWidget(self.ruby_font_edit)
        ruby_layout.addLayout(ruby_font_row)

        ruby_size_row = QHBoxLayout()
        ruby_size_row.addWidget(QLabel("Ruby 字級（0=自動）"))
        self.ruby_fontsize_spin = QSpinBox()
        self.ruby_fontsize_spin.setRange(0, 200)
        ruby_size_row.addWidget(self.ruby_fontsize_spin)
        ruby_layout.addLayout(ruby_size_row)

        ruby_color_row = QHBoxLayout()
        ruby_color_row.addWidget(QLabel("Ruby 顏色"))
        self.ruby_color_edit = QLineEdit()
        ruby_color_btn = QPushButton("編輯")
        ruby_color_btn.clicked.connect(self._edit_ruby_color)
        ruby_color_row.addWidget(self.ruby_color_edit)
        ruby_color_row.addWidget(ruby_color_btn)
        ruby_layout.addLayout(ruby_color_row)

        ruby_offset_row = QHBoxLayout()
        ruby_offset_row.addWidget(QLabel("Ruby 上移偏移"))
        self.ruby_offset_spin = QSpinBox()
        self.ruby_offset_spin.setRange(0, 200)
        ruby_offset_row.addWidget(self.ruby_offset_spin)
        ruby_layout.addLayout(ruby_offset_row)

        ruby_box.setLayout(ruby_layout)
        right_panel.addWidget(ruby_box)

        action_row = QHBoxLayout()
        apply_btn = QPushButton("套用到專案")
        apply_btn.clicked.connect(self._apply_to_project)
        export_btn = QPushButton("匯出群組設定")
        export_btn.clicked.connect(self._export_groups)
        import_btn = QPushButton("匯入群組設定")
        import_btn.clicked.connect(self._import_groups)
        action_row.addWidget(apply_btn)
        action_row.addWidget(export_btn)
        action_row.addWidget(import_btn)
        action_row.addStretch()
        right_panel.addLayout(action_row)
        right_panel.addStretch()

        right_container = QWidget()
        right_container.setLayout(right_panel)
        layout.addWidget(right_container, 3)

        self.setLayout(layout)

        # 即時預覽
        self.group_primary_edit.textChanged.connect(self._update_style_preview)
        self.group_secondary_edit.textChanged.connect(self._update_style_preview)
        self.font_combo.currentTextChanged.connect(self._update_style_preview)
        self.fontsize_spin.valueChanged.connect(self._update_style_preview)
        self.outline_spin.valueChanged.connect(self._update_style_preview)
        self.shadow_spin.valueChanged.connect(self._update_style_preview)
        self.spacing_spin.valueChanged.connect(self._update_style_preview)
        self.bold_checkbox.toggled.connect(self._update_style_preview)
        self.italic_checkbox.toggled.connect(self._update_style_preview)

        # 字型下拉可用上下鍵快速切換
        self.font_combo.installEventFilter(self)

    def _load_config(self):
        self.config = SubtitleConfig.from_dict(self.project.subtitle_config if self.project else {})
        self._scan_fonts()
        self._refresh_group_list()
        self._load_style_settings()
        self._load_ruby_settings()
        self._update_style_preview()

    def _refresh_group_list(self):
        self.group_list.clear()
        for group_id, group in self.config.color_groups.items():
            name = group.get('name') or group_id
            item = QListWidgetItem(name)
            item.setData(0x0100, group_id)
            if group_id not in self.config.enabled_groups:
                item.setForeground(QColor('#888888'))
            self.group_list.addItem(item)
        if self.group_list.count() > 0:
            self.group_list.setCurrentRow(0)

    def _on_group_selected(self, row: int):
        item = self.group_list.item(row)
        if not item:
            return
        self._sync_group_fields_to_config()
        group_id = item.data(0x0100)
        self._current_group_id = group_id
        group = self.config.color_groups.get(group_id, {})
        self.group_name_edit.setText(group.get('name', group_id))
        self.group_primary_edit.setText(group.get('primary_color', '#FFFFFF'))
        self.group_secondary_edit.setText(group.get('secondary_color', '#808080'))
        self.group_enabled_checkbox.setChecked(group_id in self.config.enabled_groups)
        self._update_style_preview()

    def _add_group(self):
        group_id = self._generate_group_id()
        self.config.color_groups[group_id] = {
            'name': group_id,
            'primary_color': '#FFFFFF',
            'secondary_color': '#808080',
        }
        self.config.enabled_groups.append(group_id)
        self._refresh_group_list()
        self._select_group(group_id)

    def _duplicate_group(self):
        if not self._current_group_id:
            return
        base = self.config.color_groups.get(self._current_group_id, {})
        group_id = self._generate_group_id()
        self.config.color_groups[group_id] = {
            'name': f"{base.get('name', group_id)}_copy",
            'primary_color': base.get('primary_color', '#FFFFFF'),
            'secondary_color': base.get('secondary_color', '#808080'),
        }
        self.config.enabled_groups.append(group_id)
        self._refresh_group_list()
        self._select_group(group_id)

    def _delete_group(self):
        if not self._current_group_id:
            return
        if len(self.config.color_groups) <= 1:
            QMessageBox.warning(self, "提醒", "至少需要保留一個群組")
            return
        reply = QMessageBox.question(
            self,
            "確認刪除",
            "確定要刪除目前這個群組嗎？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self.config.color_groups.pop(self._current_group_id, None)
        if self._current_group_id in self.config.enabled_groups:
            self.config.enabled_groups.remove(self._current_group_id)
        self._current_group_id = None
        self._refresh_group_list()

    def _select_group(self, group_id: str):
        for idx in range(self.group_list.count()):
            item = self.group_list.item(idx)
            if item and item.data(0x0100) == group_id:
                self.group_list.setCurrentRow(idx)
                break

    def _generate_group_id(self) -> str:
        index = 1
        while True:
            candidate = f"G{index}"
            if candidate not in self.config.color_groups:
                return candidate
            index += 1

    def _edit_group_color(self, field: str):
        if not self._current_group_id:
            return
        group = self.config.color_groups.get(self._current_group_id, {})
        current = group.get(field, '#FFFFFF')
        dialog = ColorEditorDialog("編輯顏色", current, self.config.color_history, self)
        if dialog.exec_() != dialog.Accepted:
            return
        color_hex = dialog.get_color_hex()
        self.config.color_history = dialog.get_history()
        group[field] = color_hex
        self.config.color_groups[self._current_group_id] = group
        if field == 'primary_color':
            self.group_primary_edit.setText(color_hex)
        else:
            self.group_secondary_edit.setText(color_hex)
        self._update_style_preview()

    def _edit_ruby_color(self):
        current = self.ruby_color_edit.text().strip() or '#DDDDDD'
        dialog = ColorEditorDialog("編輯 Ruby 顏色", current, self.config.color_history, self)
        if dialog.exec_() != dialog.Accepted:
            return
        color_hex = dialog.get_color_hex()
        self.config.color_history = dialog.get_history()
        self.ruby_color_edit.setText(color_hex)

    def _load_style_settings(self):
        self.font_combo.setCurrentText(self.config.fontname or 'Arial')
        self.fontsize_spin.setValue(self.config.fontsize or 20)
        self.outline_spin.setValue(self.config.outline or 0)
        self.shadow_spin.setValue(self.config.shadow or 0)
        self.spacing_spin.setValue(self.config.spacing or 0)
        self.bold_checkbox.setChecked(bool(getattr(self.config, 'bold', False)))
        self.italic_checkbox.setChecked(bool(getattr(self.config, 'italic', False)))
        self.margin_l_spin.setValue(self.config.margin_l or 0)
        self.margin_r_spin.setValue(self.config.margin_r or 0)
        self.top_margin_spin.setValue(self.config.top_margin or 0)
        self.bottom_margin_spin.setValue(self.config.bottom_margin or 0)
        self.lead_in_spin.setValue(self.config.lead_in_sec or 0.0)
        self.tail_hold_spin.setValue(self.config.tail_hold_sec or 0.0)

    def _load_ruby_settings(self):
        self.ruby_font_edit.setText(self.config.ruby_fontname or '')
        self.ruby_fontsize_spin.setValue(self.config.ruby_fontsize or 0)
        self.ruby_color_edit.setText(self.config.ruby_color or '#DDDDDD')
        self.ruby_offset_spin.setValue(self.config.ruby_offset_y or 0)

    def _apply_to_project(self):
        self._sync_group_fields_to_config()

        if not self.config.enabled_groups:
            self.config.enabled_groups = list(self.config.color_groups.keys())[:1] or ['A']

        self.config.fontname = self.font_combo.currentText().strip() or 'Arial'
        self.config.fontsize = int(self.fontsize_spin.value())
        self.config.outline = int(self.outline_spin.value())
        self.config.shadow = int(self.shadow_spin.value())
        self.config.spacing = int(self.spacing_spin.value())
        self.config.bold = bool(self.bold_checkbox.isChecked())
        self.config.italic = bool(self.italic_checkbox.isChecked())
        self.config.margin_l = int(self.margin_l_spin.value())
        self.config.margin_r = int(self.margin_r_spin.value())
        self.config.top_margin = int(self.top_margin_spin.value())
        self.config.bottom_margin = int(self.bottom_margin_spin.value())
        self.config.lead_in_sec = float(self.lead_in_spin.value())
        self.config.tail_hold_sec = float(self.tail_hold_spin.value())

        self.config.ruby_fontname = self.ruby_font_edit.text().strip()
        self.config.ruby_fontsize = int(self.ruby_fontsize_spin.value())
        self.config.ruby_color = self.ruby_color_edit.text().strip() or '#DDDDDD'
        self.config.ruby_offset_y = int(self.ruby_offset_spin.value())

        if self.project is not None:
            self.project.subtitle_config = self.config.to_dict()

        self._refresh_group_list()
        self.config_changed.emit(self.config.to_dict())

    def _sync_group_fields_to_config(self):
        if not self._current_group_id:
            return
        group = self.config.color_groups.get(self._current_group_id, {})
        group['name'] = self.group_name_edit.text().strip() or self._current_group_id
        group['primary_color'] = self.group_primary_edit.text().strip() or '#FFFFFF'
        group['secondary_color'] = self.group_secondary_edit.text().strip() or '#808080'
        self.config.color_groups[self._current_group_id] = group
        if self.group_enabled_checkbox.isChecked():
            if self._current_group_id not in self.config.enabled_groups:
                self.config.enabled_groups.append(self._current_group_id)
        else:
            if self._current_group_id in self.config.enabled_groups:
                self.config.enabled_groups.remove(self._current_group_id)

    def _scan_fonts(self):
        # Load custom fonts from folder
        if self._fonts_dir.exists():
            for font_path in self._fonts_dir.glob('*'):
                if font_path.suffix.lower() in {'.ttf', '.otf'}:
                    QFontDatabase.addApplicationFont(str(font_path))
        db = QFontDatabase()
        families = db.families()
        families = self._filter_font_families(db, families)
        current = self.config.fontname or 'Arial'
        self.font_combo.blockSignals(True)
        self.font_combo.clear()
        self.font_combo.addItems(families)
        if current not in families:
            self.font_combo.insertItem(0, current)
        self.font_combo.setCurrentText(current)
        self.font_combo.blockSignals(False)
        self._update_style_preview()

    @staticmethod
    def _filter_font_families(db: QFontDatabase, families: List[str]) -> List[str]:
        preferred_gothic = [
            'Hiragino Kaku Gothic ProN',
            'Hiragino Kaku Gothic Pro',
            'Hiragino Sans',
            'Hiragino Sans GB',
            'ヒラギノ角ゴ ProN',
            'ヒラギノ角ゴ Pro',
            'ヒラギノ角ゴシック',
            'Noto Sans JP',
            'Noto Sans CJK JP',
            'Source Han Sans JP',
            'Source Han Sans',
            '源ノ角ゴシック',
            'UD Kaku Gothic',
            'UD Kaku Gothic Large',
            'UDKakugo',
            'UDKakugo_Large',
            'UD角ゴ_ラージ',
            'Yu Gothic',
            'YuGothic',
            'Yu Gothic UI',
            'Meiryo',
            'MS Gothic',
        ]
        common_fonts = {
            'Arial',
            'Helvetica',
            'Helvetica Neue',
            'Times New Roman',
            'Verdana',
            'Tahoma',
            'Trebuchet MS',
            'Georgia',
            'Courier New',
        }
        filtered = []
        for family in families:
            if family in preferred_gothic:
                filtered.append(family)
                continue
            if family in common_fonts:
                filtered.append(family)
                continue
            try:
                systems = db.writingSystems(family)
            except Exception:
                systems = []
            if QFontDatabase.Japanese in systems:
                filtered.append(family)
        preferred = [name for name in preferred_gothic if name in filtered]
        rest = sorted([name for name in filtered if name not in preferred])
        ordered = preferred + rest
        return ordered or families

    def eventFilter(self, source, event):
        if source is self.font_combo and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Up, Qt.Key_Down):
                delta = -1 if event.key() == Qt.Key_Up else 1
                count = self.font_combo.count()
                if count > 0:
                    new_index = (self.font_combo.currentIndex() + delta) % count
                    self.font_combo.setCurrentIndex(new_index)
                return True
        return super().eventFilter(source, event)

    def _update_style_preview(self):
        if not hasattr(self, "style_preview"):
            return
        font_family = self.font_combo.currentText().strip() or 'Arial'
        primary = self._safe_color(self.group_primary_edit.text().strip(), '#FFFFFF')
        secondary = self._safe_color(self.group_secondary_edit.text().strip(), '#808080')
        self.style_preview.set_style(
            font_family=font_family,
            font_size=int(self.fontsize_spin.value()),
            outline=int(self.outline_spin.value()),
            shadow=int(self.shadow_spin.value()),
            spacing=int(self.spacing_spin.value()),
            bold=bool(self.bold_checkbox.isChecked()),
            italic=bool(self.italic_checkbox.isChecked()),
            primary=primary,
            secondary=secondary,
        )

    @staticmethod
    def _safe_color(value: str, fallback: str) -> QColor:
        color = QColor(value)
        if not color.isValid():
            color = QColor(fallback)
        return color

    def _import_font(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "選擇字型檔案",
            "",
            "字型檔案 (*.ttf *.otf);;所有檔案 (*)",
        )
        if not file_paths:
            return
        for path in file_paths:
            target = self._fonts_dir / Path(path).name
            try:
                shutil.copy2(path, target)
            except Exception as exc:
                QMessageBox.warning(self, "匯入失敗", f"無法匯入字型：{path}\n{exc}")
        self._scan_fonts()

    def _export_groups(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "匯出群組設定",
            "",
            "JSON (*.json);;所有檔案 (*)",
        )
        if not file_path:
            return
        data = {
            'color_groups': self.config.color_groups,
            'enabled_groups': self.config.enabled_groups,
        }
        try:
            import json

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "完成", "群組設定已匯出")
        except Exception as exc:
            QMessageBox.warning(self, "匯出失敗", str(exc))

    def _import_groups(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "匯入群組設定",
            "",
            "JSON (*.json);;所有檔案 (*)",
        )
        if not file_path:
            return
        try:
            import json

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            groups = data.get('color_groups') or {}
            enabled = data.get('enabled_groups') or []
            self.config.color_groups = SubtitleConfig._normalize_groups(groups)
            self.config.enabled_groups = [g for g in enabled if g in self.config.color_groups]
            if not self.config.enabled_groups:
                self.config.enabled_groups = list(self.config.color_groups.keys())[:1]
            self._refresh_group_list()
            QMessageBox.information(self, "完成", "群組設定已匯入")
        except Exception as exc:
            QMessageBox.warning(self, "匯入失敗", str(exc))

    def set_project(self, project):
        """更新專案"""
        self.project = project
        self._load_config()
