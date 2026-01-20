"""
歌詞時間標記面板

作用：
- 載入音訊與歌詞
- 邊播邊按空白鍵標記時間
- 回退修正與輸出 LRC
"""

from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt, QUrl
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
)

from core.lrc import LrcParser, LrcTimeline, LrcWriter
from gui.widgets.lrc_line_editor import LrcLineEditor
from gui.widgets.lrc_editor import LrcEditorDialog


class LyricsTimingPanel(QWidget):
    """歌詞標記操作面板"""

    def __init__(self, project, parent=None):
        super().__init__(parent)
        # 專案狀態
        self.project = project
        # LRC 解析器
        self.parser = LrcParser()
        # LRC 寫入器
        self.writer = LrcWriter()
        # 時間軸
        self.timeline: Optional[LrcTimeline] = None
        # 單字索引列表
        self._word_positions: List[Tuple[int, int]] = []
        # 目前索引
        self._current_index = 0
        # 預設時長（秒）
        self._default_duration = 0.5
        # 初始化 UI
        self._setup_ui()
        # 初始化播放器
        self._setup_player()
        # 快捷鍵
        self._setup_shortcuts()

    def set_project(self, project):
        """更新專案狀態"""
        self.project = project
        self.timeline = None
        self.editor.set_timeline(LrcTimeline())
        self._reset_mark_state()

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

        self.detail_edit_btn = QPushButton("字級編輯")  # 字級編輯按鈕
        self.detail_edit_btn.clicked.connect(self.open_detail_editor)
        file_layout.addWidget(self.detail_edit_btn)

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
        self.speed_combo.addItems(["0.5x", "0.75x", "1x", "1.25x", "1.5x", "2x"])
        self.speed_combo.currentTextChanged.connect(self._on_speed_change)
        control_layout.addWidget(self.speed_combo)

        self.time_label = QLabel("00:00.00 / 00:00.00")
        control_layout.addWidget(self.time_label)

        layout.addLayout(control_layout)

        # 進度條
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.sliderMoved.connect(self._on_seek_slider)
        layout.addWidget(self.position_slider)

        # LRC 表格
        self.editor = LrcLineEditor(self)
        self.editor.line_text_changed.connect(self._on_line_text_changed)
        layout.addWidget(self.editor)

        self.setLayout(layout)

    def _setup_player(self):
        """初始化播放器"""
        self.player = QMediaPlayer()
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)

    def _setup_shortcuts(self):
        """設定快捷鍵"""
        QShortcut(QKeySequence(Qt.Key_Space), self, activated=self.mark_current_time)
        QShortcut(QKeySequence(Qt.Key_Q), self, activated=lambda: self._adjust_speed(-0.1))
        QShortcut(QKeySequence(Qt.Key_W), self, activated=lambda: self._adjust_speed(0.1))

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

    def _on_export_lrc(self):
        """輸出 LRC 檔案"""
        if not self.timeline:
            QMessageBox.warning(self, "提醒", "尚未載入字幕")
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

    def _on_line_text_changed(self, _line_idx: int, _text: str):
        """句子內容變更時重新建立索引"""
        self._build_word_positions()
        self._reset_mark_state()
        self._highlight_current_word()

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
        new_rate = min(2.0, max(0.5, current_rate + delta))
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
        if not self.timeline:
            return
        for line_idx, line in enumerate(self.timeline.lines):
            for word_idx, _word in enumerate(line.words):
                self._word_positions.append((line_idx, word_idx))

    def _reset_mark_state(self):
        """重置標記狀態"""
        self._current_index = 0

    def _highlight_current_word(self):
        """高亮目前字"""
        if not self._word_positions:
            return
        line_idx, word_idx = self._word_positions[self._current_index]
        self.editor.highlight_word(line_idx, word_idx)

    def mark_current_time(self):
        """標記目前時間"""
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

        self._current_index += 1

        if self._current_index < len(self._word_positions):
            self._highlight_current_word()

    def open_detail_editor(self):
        """開啟字級細部編輯"""
        if not self.timeline:
            QMessageBox.warning(self, "提醒", "尚未載入字幕")
            return
        dialog = LrcEditorDialog(self.timeline, self)
        dialog.exec_()
        self.editor.refresh()
        self._build_word_positions()
