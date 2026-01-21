"""
Worker threads for background tasks
Phase 1.1.4: 後台任務線程
"""

import logging
from typing import Dict, Optional

from PyQt5.QtCore import QThread, pyqtSignal

from core.audio.separator import AudioSeparator
from core.video import VideoRenderer

logger = logging.getLogger(__name__)


class SeparationWorker(QThread):
    """音源分離工作線程"""
    
    # 信號
    progress = pyqtSignal(int)  # 進度百分比 (0-100)
    message = pyqtSignal(str)   # 狀態訊息
    finished = pyqtSignal(dict) # 完成，返回 stems 路徑字典
    error = pyqtSignal(str)     # 錯誤訊息
    
    def __init__(self, video_path: str, output_dir: str, output_options: dict):
        super().__init__()
        self.video_path = video_path  # 影片路徑
        self.output_dir = output_dir  # 輸出資料夾
        self.output_options = output_options  # 輸出選項
        self.separator = None  # 分離器
    
    def run(self):
        """執行分離"""
        try:
            self.message.emit("初始化音訊分離器...")
            self.progress.emit(5)
            
            self.separator = AudioSeparator()
            
            self.message.emit("處理影片中...")
            self.progress.emit(20)
            
            # 進行分離
            stems = self.separator.process_video(
                self.video_path,
                self.output_dir,
                self.output_options,
            )  # stems 路徑字典
            
            self.progress.emit(100)
            self.message.emit("音訊分離完成！")
            self.finished.emit(stems)
        
        except Exception as e:
            logger.error(f"Separation error: {e}")
            self.error.emit(str(e))
            self.progress.emit(0)


class RenderWorker(QThread):
    """影片輸出工作線程"""

    progress = pyqtSignal(int)  # 進度百分比 (0-100)
    message = pyqtSignal(str)   # 狀態訊息
    finished = pyqtSignal(str)  # 完成，回傳輸出路徑
    error = pyqtSignal(str)     # 錯誤訊息

    def __init__(self, video_path: str, audio_path: str, subtitle_path: str, output_path: str):
        super().__init__()
        self.video_path = video_path
        self.audio_path = audio_path
        self.subtitle_path = subtitle_path
        self.output_path = output_path
        self.renderer = VideoRenderer()

    def run(self):
        """執行輸出"""
        try:
            self.message.emit("開始輸出影片...")
            self.progress.emit(0)

            def on_progress(value: int):
                self.progress.emit(value)

            success = self.renderer.render(
                self.video_path,
                self.audio_path,
                self.subtitle_path,
                self.output_path,
                progress_callback=on_progress,
            )

            if success:
                self.progress.emit(100)
                self.message.emit("影片輸出完成！")
                self.finished.emit(self.output_path)
            else:
                self.error.emit("FFmpeg 輸出失敗")
        except Exception as exc:
            logger.error(f"Render error: {exc}")
            self.error.emit(str(exc))
            self.progress.emit(0)


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    # 測試：worker = SeparationWorker("test.mp4", "output")
    # worker.finished.connect(print)
    # worker.start()
    sys.exit(app.exec_())
