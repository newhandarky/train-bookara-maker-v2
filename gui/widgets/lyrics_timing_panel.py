"""
歌詞時間標記面板

作用：
- 載入音訊與歌詞
- 邊播邊按空白鍵標記時間
- 回退修正與輸出 LRC
"""

from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt, QUrl, QEvent, pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QSlider,
    QComboBox,
    QMessageBox,
    QShortcut,
    QApplication,
    QLineEdit,
    QTextEdit,
    QPlainTextEdit,
    QSplitter,
)

from core.lrc import LrcParser, LrcTimeline, LrcWriter, LrcLine, LrcValidator, ValidationError
from core.subtitle import LrcToAssConverter, SubtitleConfig
from gui.widgets.lrc_line_editor import LrcLineEditor
from gui.widgets.lrc_editor import LrcEditorDialog


class LyricsTimingPanel(QWidget):
    """歌詞標記操作面板"""

    # 字幕載入狀態變更訊號（是否已載入）
    lrc_loaded = pyqtSignal(bool)

    def __init__(self, project, parent=None):
        super().__init__(parent)
        # 專案狀態
        self.project = project
        # LRC 解析器
        self.parser = LrcParser()
        # LRC 寫入器
        self.writer = LrcWriter()
        # ASS 轉換器設定
        project_config = project.subtitle_config if project else None
        self.subtitle_config = SubtitleConfig.from_dict(project_config)
        # 時間軸
        self.timeline: Optional[LrcTimeline] = None
        # 單字索引列表
        self._word_positions: List[Tuple[int, int]] = []
        # 目前索引
        self._current_index = 0
        # 位置索引映射
        self._word_index_map = {}
        # 預設時長（秒）
        self._default_duration = 0.5
        # 空白鍵標記狀態
        self._space_is_down = False
        self._pending_index = None
        # 句子編輯狀態
        self._active_line_idx = None
        self._is_sentence_updating = False
        # 初始化 UI
        self._setup_ui()
        # 初始化播放器
        self._setup_player()
        # 快捷鍵
        self._setup_shortcuts()
        # 鍵盤事件攔截（空白鍵按下/放開）
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)

    def set_project(self, project):
        """更新專案狀態"""
        self.project = project
        self.timeline = None
        self.editor.set_timeline(LrcTimeline())
        self._reset_mark_state()
        self._active_line_idx = None
        self._sync_sentence_editor(-1)
        self.lrc_loaded.emit(False)
        self.set_subtitle_config(project.subtitle_config if project else {})

    def _setup_ui(self):
        """建立 UI"""
        self.setFocusPolicy(Qt.StrongFocus)

        layout = QVBoxLayout()

        # 檔案操作列
        file_layout = QHBoxLayout()
        self.open_audio_btn = QPushButton("開啟音訊")
        self.open_audio_btn.clicked.connect(self._on_open_audio)
        file_layout.addWidget(self.open_audio_btn)

        self.audio_label = QLabel("音訊：未選擇")
        file_layout.addWidget(self.audio_label)

        self.open_lyrics_btn = QPushButton("開啟字幕（.txt）")
        self.open_lyrics_btn.clicked.connect(self._on_open_lyrics)
        file_layout.addWidget(self.open_lyrics_btn)

        self.lyrics_label = QLabel("字幕：未選擇")
        file_layout.addWidget(self.lyrics_label)

        self.export_lrc_btn = QPushButton("輸出 LRC")  # 輸出按鈕
        self.export_lrc_btn.clicked.connect(self._on_export_lrc)
        file_layout.addWidget(self.export_lrc_btn)

        self.export_ass_btn = QPushButton("輸出 ASS")
        self.export_ass_btn.clicked.connect(self._on_export_ass)
        file_layout.addWidget(self.export_ass_btn)

        self.detail_edit_btn = QPushButton("字級編輯")  # 字級編輯按鈕
        self.detail_edit_btn.clicked.connect(self.open_detail_editor)
        file_layout.addWidget(self.detail_edit_btn)

        self.add_line_btn = QPushButton("新增行")
        self.add_line_btn.clicked.connect(self._on_add_line)
        file_layout.addWidget(self.add_line_btn)

        self.delete_line_btn = QPushButton("刪除行")
        self.delete_line_btn.clicked.connect(self._on_delete_line)
        file_layout.addWidget(self.delete_line_btn)

        layout.addLayout(file_layout)

        # 播放控制列
        control_layout = QHBoxLayout()
        self.play_btn = QPushButton("播放")
        self.play_btn.clicked.connect(self._on_toggle_play)
        control_layout.addWidget(self.play_btn)

        self.back_btn = QPushButton("◀ 10s")
        self.back_btn.clicked.connect(lambda: self._seek_by(-10.0))
        control_layout.addWidget(self.back_btn)

        self.forward_btn = QPushButton("10s ▶")
        self.forward_btn.clicked.connect(lambda: self._seek_by(10.0))
        control_layout.addWidget(self.forward_btn)

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5x", "0.75x", "1x"])
        self.speed_combo.currentTextChanged.connect(self._on_speed_change)
        control_layout.addWidget(self.speed_combo)

        self.time_label = QLabel("00:00.00 / 00:00.00")
        control_layout.addWidget(self.time_label)

        layout.addLayout(control_layout)

        # 進度條
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.sliderMoved.connect(self._on_seek_slider)
        layout.addWidget(self.position_slider)

        # LRC 表格 + 句子編輯側欄
        self.editor = LrcLineEditor(self)
        self.editor.line_text_changed.connect(self._on_line_text_changed)
        self.editor.cursor_changed.connect(self._on_cursor_changed)
        self.editor.set_group_options(self._get_enabled_group_options())

        side_panel = QWidget()
        side_layout = QVBoxLayout()
        side_layout.setContentsMargins(6, 0, 0, 0)

        self.sentence_label = QLabel("句子編輯")
        side_layout.addWidget(self.sentence_label)

        self.sentence_edit = QLineEdit()
        self.sentence_edit.setPlaceholderText("請輸入句子")
        self.sentence_edit.setEnabled(False)
        self.sentence_edit.editingFinished.connect(self._on_sentence_edit_finished)
        side_layout.addWidget(self.sentence_edit)
        side_layout.addStretch()
        side_panel.setLayout(side_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.editor)
        splitter.addWidget(side_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        layout.setStretch(0, 0)
        layout.setStretch(1, 0)
        layout.setStretch(2, 0)
        layout.setStretch(3, 1)

        self.setLayout(layout)

    def _setup_player(self):
        """初始化播放器"""
        self.player = QMediaPlayer()
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)

    def _setup_shortcuts(self):
        """設定快捷鍵"""
        QShortcut(QKeySequence(Qt.Key_Q), self, activated=lambda: self._adjust_speed(-0.1))
        QShortcut(QKeySequence(Qt.Key_W), self, activated=lambda: self._adjust_speed(0.1))
        QShortcut(QKeySequence(Qt.Key_Z), self, activated=lambda: self._seek_by(-5.0))
        QShortcut(QKeySequence(Qt.Key_X), self, activated=lambda: self._seek_by(5.0))

    def _on_open_audio(self):
        """載入音訊檔案"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇音訊檔案",
            "",
            "音訊檔案 (*.wav *.mp3 *.flac *.m4a);;所有檔案 (*)",
        )
        if not file_path:
            return

        self.set_audio_file(file_path)

    def set_audio_file(self, file_path: str):
        """設定音訊檔案"""
        if not file_path:
            return
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
        self.audio_label.setText(f"音訊：{file_path}")
        self.player.setPosition(0)

    def _on_open_lyrics(self):
        """載入字幕檔案（.txt）"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇字幕檔案",
            "",
            "字幕檔案 (*.txt *.lrc);;所有檔案 (*)",
        )
        if not file_path:
            return

        try:
            self.timeline = self.parser.parse_file(file_path, auto_ruby=True)
        except Exception as exc:
            QMessageBox.critical(self, "錯誤", f"載入字幕失敗：\n{exc}")
            return

        self.project.lrc_timeline = self.timeline
        self.editor.set_timeline(self.timeline)
        self.lyrics_label.setText(f"字幕：{file_path}")
        self._build_word_positions()
        self._reset_mark_state()
        self._highlight_current_word()
        self.lrc_loaded.emit(True)
        if self.timeline.lines:
            self._active_line_idx = 0
            self._sync_sentence_editor(0)
        else:
            self._active_line_idx = None
            self._sync_sentence_editor(-1)

    def _on_export_lrc(self):
        """輸出 LRC 檔案"""
        if not self.timeline:
            QMessageBox.warning(self, "提醒", "尚未載入字幕")
            return

        if not self._confirm_export_with_validation("LRC"):
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "儲存 LRC 檔案",
            "",
            "LRC 檔案 (*.lrc);;所有檔案 (*)",
        )
        if not file_path:
            return

        self.writer.write_file(self.timeline, file_path)
        QMessageBox.information(self, "完成", f"LRC 已輸出：\n{file_path}")

    def _on_export_ass(self):
        """輸出 ASS 檔案"""
        if not self.timeline:
            QMessageBox.warning(self, "提醒", "尚未載入字幕")
            return

        if not self._confirm_export_with_validation("ASS"):
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "儲存 ASS 檔案",
            "",
            "ASS 檔案 (*.ass);;所有檔案 (*)",
        )
        if not file_path:
            return

        converter = LrcToAssConverter(self.subtitle_config.to_dict())
        ass_content = converter.convert(self.timeline)
        converter.save_file(ass_content, file_path)
        self.project.ass_content = ass_content
        self.project.ass_file_path = file_path
        QMessageBox.information(self, "完成", f"ASS 已輸出：\n{file_path}")

    def _confirm_export_with_validation(self, target_label: str) -> bool:
        """輸出前驗證並允許強制輸出"""
        if not self.timeline:
            return False

        validator = LrcValidator()
        is_valid, errors = validator.validate(self.timeline)
        filtered = [err for err in errors if err.error_type != 'EMPTY_LINE']
        if is_valid or not filtered:
            return True

        detail_text = self._format_validation_errors(filtered)
        dialog = QMessageBox(self)
        dialog.setWindowTitle("驗證結果")
        dialog.setIcon(QMessageBox.Warning)
        dialog.setText(f"{target_label} 驗證未通過，仍要輸出嗎？")
        dialog.setDetailedText(detail_text)
        dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dialog.setDefaultButton(QMessageBox.No)
        dialog.button(QMessageBox.Yes).setText("仍要輸出")
        dialog.button(QMessageBox.No).setText("返回修正")
        return dialog.exec_() == QMessageBox.Yes

    def _format_validation_errors(self, errors: List[ValidationError]) -> str:
        """格式化驗證錯誤清單"""
        lines = []
        for error in errors:
            line_no = error.line_index + 1
            if error.word_index >= 0:
                word_no = error.word_index + 1
                location = f"第{line_no}行 第{word_no}字"
            else:
                location = f"第{line_no}行"
            lines.append(f"{location}：{error.message}")
        return "\n".join(lines)

    def _on_line_text_changed(self, _line_idx: int, _text: str):
        """句子內容變更時重新建立索引"""
        self._build_word_positions()
        self._reset_mark_state()
        self._highlight_current_word()
        if self._active_line_idx is not None:
            self._sync_sentence_editor(self._active_line_idx)

    def _on_cursor_changed(self, line_idx: int, word_idx: int):
        """游標變更時同步標記索引"""
        index = self._word_index_map.get((line_idx, word_idx))
        if index is not None:
            self._current_index = index
        self._active_line_idx = line_idx
        self._sync_sentence_editor(line_idx)

    def _sync_sentence_editor(self, line_idx: int):
        """同步句子編輯欄內容"""
        if not self.timeline or line_idx < 0 or line_idx >= len(self.timeline.lines):
            self._is_sentence_updating = True
            self.sentence_edit.setText("")
            self.sentence_edit.setEnabled(False)
            self._is_sentence_updating = False
            return

        line = self.timeline.lines[line_idx]
        self._is_sentence_updating = True
        self.sentence_edit.setEnabled(True)
        self.sentence_edit.setText(line.text)
        self._is_sentence_updating = False

    def _on_sentence_edit_finished(self):
        """句子編輯完成"""
        if self._is_sentence_updating:
            return
        if not self.timeline or self._active_line_idx is None:
            return
        self.editor.set_line_text(self._active_line_idx, self.sentence_edit.text())

    def _on_add_line(self):
        """插入新行（在當前行上方）"""
        if not self.timeline:
            self.timeline = LrcTimeline()
            self.project.lrc_timeline = self.timeline
            self.editor.set_timeline(self.timeline)

        row = self.editor.currentRow()
        line_idx = self.editor.get_line_index_by_row(row)
        if line_idx is None:
            line_idx = len(self.timeline.lines)
        insert_idx = max(0, line_idx)

        self.timeline.lines.insert(insert_idx, LrcLine(words=[]))
        self.editor.refresh()
        self._build_word_positions()
        self._reset_mark_state()
        self.editor.set_cursor(insert_idx, 0)

    def _on_delete_line(self):
        """刪除當前行"""
        if not self.timeline or not self.timeline.lines:
            QMessageBox.warning(self, "提醒", "尚無可刪除的行")
            return

        row = self.editor.currentRow()
        line_idx = self.editor.get_line_index_by_row(row)
        if line_idx is None:
            QMessageBox.warning(self, "提醒", "請先選擇要刪除的行")
            return

        reply = QMessageBox.question(
            self,
            "確認刪除",
            "確定要刪除目前這一行嗎？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.timeline.remove_line(line_idx)
        self.editor.refresh()
        self._build_word_positions()
        self._reset_mark_state()

        if not self.timeline.lines:
            self._active_line_idx = None
            self._sync_sentence_editor(-1)
            return

        new_idx = min(line_idx, len(self.timeline.lines) - 1)
        self.editor.set_cursor(new_idx, 0)

    def set_subtitle_config(self, config: dict):
        """更新字幕設定"""
        self.subtitle_config = SubtitleConfig.from_dict(config)
        self.editor.set_group_options(self._get_enabled_group_options())

    def _get_enabled_group_options(self):
        """取得啟用群組選項（id, name）"""
        options = {}
        groups = self.subtitle_config.color_groups or {}
        for group_id in self.subtitle_config.enabled_groups or []:
            group = groups.get(group_id, {})
            options[group_id] = group.get('name', group_id)
        if not options:
            for group_id, group in groups.items():
                options[group_id] = group.get('name', group_id)
                break
        return options

    def _on_toggle_play(self):
        """播放/暫停"""
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.play_btn.setText("播放")
        else:
            if self.player.mediaStatus() == QMediaPlayer.NoMedia:
                QMessageBox.warning(self, "提醒", "請先載入音訊")
                return
            self.player.play()
            self.play_btn.setText("暫停")

    def _on_position_changed(self, position_ms: int):
        """播放進度變更"""
        if not self.position_slider.isSliderDown():
            self.position_slider.setValue(position_ms)
        self._update_time_label(position_ms)

    def _on_duration_changed(self, duration_ms: int):
        """音訊長度變更"""
        self.position_slider.setRange(0, duration_ms)
        self._update_time_label(self.player.position())

    def _on_seek_slider(self, position_ms: int):
        """拖動進度條"""
        self.player.setPosition(position_ms)

    def _on_speed_change(self, speed_text: str):
        """播放速度變更"""
        rate = float(speed_text.replace('x', ''))
        self.player.setPlaybackRate(rate)

    def _adjust_speed(self, delta: float):
        """快捷鍵調整速度"""
        current_rate = self.player.playbackRate()
        new_rate = min(1.0, max(0.5, current_rate + delta))
        self.player.setPlaybackRate(new_rate)
        self.speed_combo.setCurrentText(f"{new_rate:g}x")

    def _seek_by(self, seconds: float):
        """快進/快退"""
        if self.player.mediaStatus() == QMediaPlayer.NoMedia:
            return
        new_pos = max(0, self.player.position() + int(seconds * 1000))
        self.player.setPosition(new_pos)

    def _update_time_label(self, position_ms: int):
        """更新時間顯示"""
        duration_ms = self.player.duration()
        current_str = self._format_time(position_ms / 1000.0)
        duration_str = self._format_time(duration_ms / 1000.0) if duration_ms else "00:00.00"
        self.time_label.setText(f"{current_str} / {duration_str}")

    def _format_time(self, seconds: float) -> str:
        """格式化時間為 mm:ss.xx"""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        centisecs = int(round((seconds % 1) * 100))
        return f"{minutes:02d}:{secs:02d}.{centisecs:02d}"

    def _build_word_positions(self):
        """建立單字索引列表"""
        self._word_positions = []
        self._word_index_map = {}
        if not self.timeline:
            return
        for line_idx, line in enumerate(self.timeline.lines):
            for word_idx, _word in enumerate(line.words):
                self._word_index_map[(line_idx, word_idx)] = len(self._word_positions)
                self._word_positions.append((line_idx, word_idx))

    def _reset_mark_state(self):
        """重置標記狀態"""
        self._current_index = 0
        self._pending_index = None
        self._space_is_down = False

    def _highlight_current_word(self):
        """高亮目前字"""
        if not self._word_positions:
            return
        line_idx, word_idx = self._word_positions[self._current_index]
        self.editor.highlight_word(line_idx, word_idx)

    def _start_mark(self):
        """空白鍵按下：記錄起始時間"""
        if not self.timeline:
            QMessageBox.warning(self, "提醒", "請先載入字幕")
            return
        if self.player.mediaStatus() == QMediaPlayer.NoMedia:
            QMessageBox.warning(self, "提醒", "請先載入音訊")
            return
        if self._current_index >= len(self._word_positions):
            QMessageBox.information(self, "提示", "已完成所有標記")
            return

        current_time = self.player.position() / 1000.0
        line_idx, word_idx = self._word_positions[self._current_index]

        # 更新目前字的開始時間
        self.editor.update_word_time(
            line_idx,
            word_idx,
            current_time,
            current_time + self._default_duration,
        )

        # 更新上一字的結束時間
        if self._current_index > 0:
            prev_line_idx, prev_word_idx = self._word_positions[self._current_index - 1]
            prev_word = self.timeline.lines[prev_line_idx].words[prev_word_idx]
            self.editor.update_word_time(
                prev_line_idx,
                prev_word_idx,
                prev_word.start_time,
                current_time,
            )

        self._pending_index = self._current_index
        self._space_is_down = True
        self._highlight_current_word()

    def _finish_mark(self):
        """空白鍵放開：記錄結束時間"""
        if not self.timeline:
            return
        if self._pending_index is None:
            return

        current_time = self.player.position() / 1000.0
        line_idx, word_idx = self._word_positions[self._pending_index]
        word = self.timeline.lines[line_idx].words[word_idx]
        end_time = max(current_time, word.start_time + 0.01)

        self.editor.update_word_time(
            line_idx,
            word_idx,
            word.start_time,
            end_time,
        )

        self._current_index = self._pending_index + 1
        self._pending_index = None
        self._space_is_down = False

        if self._current_index < len(self._word_positions):
            self._highlight_current_word()

    def eventFilter(self, obj, event):
        """攔截空白鍵按下/放開事件"""
        if not self.isVisible() or not self.window().isActiveWindow():
            return super().eventFilter(obj, event)

        if event.type() in (QEvent.KeyPress, QEvent.KeyRelease) and event.key() == Qt.Key_Space:
            focus_widget = QApplication.focusWidget()
            if isinstance(focus_widget, (QLineEdit, QTextEdit, QPlainTextEdit)):
                return super().eventFilter(obj, event)
            if event.isAutoRepeat():
                return True
            if event.type() == QEvent.KeyPress and not self._space_is_down:
                self._start_mark()
                return True
            if event.type() == QEvent.KeyRelease and self._space_is_down:
                self._finish_mark()
                return True

        return super().eventFilter(obj, event)

    def open_detail_editor(self):
        """開啟字級細部編輯"""
        if not self.timeline:
            QMessageBox.warning(self, "提醒", "尚未載入字幕")
            return
        dialog = LrcEditorDialog(self.timeline, self)
        dialog.exec_()
        self.editor.refresh()
        self._build_word_positions()
