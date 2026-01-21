"""
預覽播放器元件
"""

from typing import Optional

from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSlider,
    QLabel,
    QComboBox,
)

from core.lrc import LrcTimeline


class PreviewPlayer(QWidget):
    """預覽播放器"""

    position_changed = pyqtSignal(float)  # 當前播放位置（秒）

    def __init__(self, parent=None):
        super().__init__(parent)
        # 播放器
        self.player = QMediaPlayer()
        # LRC 時間軸
        self.timeline: Optional[LrcTimeline] = None
        # 初始化 UI
        self._setup_ui()
        # 設置信號
        self._setup_signals()

    def _setup_ui(self):
        """設置 UI"""
        layout = QVBoxLayout()

        # 視訊顯示區域
        self.video_widget = QVideoWidget()
        self.player.setVideoOutput(self.video_widget)
        layout.addWidget(self.video_widget)

        # 控制欄
        control_layout = QHBoxLayout()

        self.play_btn = QPushButton("播放")
        self.play_btn.clicked.connect(self._on_play)
        control_layout.addWidget(self.play_btn)

        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.sliderMoved.connect(self._on_seek)
        control_layout.addWidget(self.progress_slider)

        self.time_label = QLabel("00:00 / 00:00")
        control_layout.addWidget(self.time_label)

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5x", "0.75x", "1x", "1.25x", "1.5x", "2x"])
        self.speed_combo.currentTextChanged.connect(self._on_speed_change)
        control_layout.addWidget(self.speed_combo)

        layout.addLayout(control_layout)

        # 歌詞顯示
        self.lyrics_label = QLabel("歌詞將在此顯示")
        self.lyrics_label.setAlignment(Qt.AlignCenter)
        self.lyrics_label.setStyleSheet(
            "background-color: #2a2a2a;"
            "color: #f5f5f5;"
            "padding: 16px;"
            "font-size: 20px;"
        )
        layout.addWidget(self.lyrics_label)

        self.setLayout(layout)

    def _setup_signals(self):
        """設置信號"""
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)

    def set_media(self, file_path: str):
        """設置媒體檔案（影片或音訊）"""
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))

    def set_timeline(self, timeline: Optional[LrcTimeline]):
        """設置 LRC 時間軸"""
        self.timeline = timeline

    def _on_play(self):
        """播放/暫停"""
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.play_btn.setText("播放")
        else:
            self.player.play()
            self.play_btn.setText("暫停")

    def _on_position_changed(self, position_ms: int):
        """播放位置改變"""
        position_sec = position_ms / 1000.0

        if not self.progress_slider.isSliderDown():
            self.progress_slider.setValue(position_ms)

        self._update_time_label()
        self._update_lyrics(position_sec)
        self.position_changed.emit(position_sec)

    def _on_duration_changed(self, duration_ms: int):
        """時長改變"""
        self.progress_slider.setMaximum(duration_ms)
        self._update_time_label()

    def _on_seek(self, position_ms: int):
        """拖動進度條"""
        self.player.setPosition(position_ms)

    def _on_speed_change(self, speed_str: str):
        """改變播放速度"""
        rate = float(speed_str.replace('x', ''))
        self.player.setPlaybackRate(rate)

    def _update_time_label(self):
        """更新時間顯示"""
        current_ms = self.player.position()
        duration_ms = self.player.duration()

        current_sec = current_ms // 1000
        duration_sec = duration_ms // 1000

        current_str = f"{current_sec // 60:02d}:{current_sec % 60:02d}"
        duration_str = f"{duration_sec // 60:02d}:{duration_sec % 60:02d}"

        self.time_label.setText(f"{current_str} / {duration_str}")

    def _update_lyrics(self, position_sec: float):
        """更新歌詞顯示"""
        if not self.timeline:
            return
        current_word = self.timeline.get_word_at_time(position_sec)
        if not current_word:
            return
        ruby_text = current_word.ruby_pair.ruby if current_word.ruby_pair else ""
        if ruby_text:
            self.lyrics_label.setText(f"{current_word.text} ({ruby_text})")
        else:
            self.lyrics_label.setText(current_word.text)
