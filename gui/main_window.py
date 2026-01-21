"""
Main window for Train Bookara Maker v2
Phase 1.1.4: GUI Integration
"""

import os
import logging
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QMenuBar, QMenu, QStatusBar, QTabWidget, QStackedWidget,
    QFileDialog
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from pipeline import KaraokeProject, KaraokeWorkflow
from gui.widgets.import_dialog import ImportVideoDialog
from gui.widgets.output_options_dialog import OutputOptionsDialog
from gui.widgets.progress_dialog import ProgressDialog
from gui.widgets.lyrics_timing_panel import LyricsTimingPanel
from gui.widgets.preview_player import PreviewPlayer
from gui.workers import SeparationWorker, RenderWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """主視窗 - Train Bookara Maker v2"""
    
    def __init__(self):
        super().__init__()
        self.project = KaraokeProject()
        self.separation_worker = None
        self.init_ui()
        self.setup_menu()
        logger.info("MainWindow initialized")
    
    def init_ui(self):
        """初始化 UI"""
        self.setWindowTitle('Train Bookara Maker v2')  # 窗口標題
        self.setGeometry(100, 100, 1400, 900)
        
        # 中央 widget
        central_widget = QWidget()
        layout = QVBoxLayout()
        
        # 標題【改這裡】
        title = QLabel('Train Bookara Maker v2')
        title_font = QFont('Arial', 24, QFont.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 狀態顯示
        status_label = QLabel('目前狀態：空專案')
        self.status_label = status_label
        layout.addWidget(status_label)
        
        # 按鈕區
        button_layout = QHBoxLayout()
        
        import_btn = QPushButton('1. 匯入影片')
        import_btn.setMinimumHeight(50)
        import_btn.clicked.connect(self.on_import_video)
        button_layout.addWidget(import_btn)
        
        edit_btn = QPushButton('2. 編輯字幕')
        edit_btn.setMinimumHeight(50)
        edit_btn.setEnabled(True)
        edit_btn.clicked.connect(self.on_edit_lyrics)
        self.edit_btn = edit_btn
        button_layout.addWidget(edit_btn)

        preview_btn = QPushButton('3. 預覽影片')
        preview_btn.setMinimumHeight(50)
        preview_btn.setEnabled(False)
        preview_btn.clicked.connect(self.on_preview_player)
        self.preview_btn = preview_btn
        button_layout.addWidget(preview_btn)

        export_btn = QPushButton('4. 匯出影片')
        export_btn.setMinimumHeight(50)
        export_btn.setEnabled(True)
        export_btn.clicked.connect(self.on_export_video)
        self.export_btn = export_btn
        button_layout.addWidget(export_btn)
        
        layout.addLayout(button_layout)
        
        # 內容區（資訊 / 歌詞編輯）
        self.content_stack = QStackedWidget()

        # 專案資訊頁
        info_page = QWidget()
        info_layout = QVBoxLayout()

        log_label = QLabel('專案資訊：')
        info_layout.addWidget(log_label)

        self.info_label = QLabel(
            f'專案狀態：{self._format_state(self.project.get_state())}\n影片路徑：無\n音訊輸出：無'
        )
        info_layout.addWidget(self.info_label)
        info_layout.addStretch()
        info_page.setLayout(info_layout)

        # 歌詞編輯頁
        self.lyrics_panel = LyricsTimingPanel(self.project, self)
        self.lyrics_panel.lrc_loaded.connect(self._on_lrc_loaded)

        self.content_stack.addWidget(info_page)
        self.content_stack.addWidget(self.lyrics_panel)

        # 預覽播放器頁
        self.preview_player = PreviewPlayer(self)
        self.content_stack.addWidget(self.preview_player)
        self.content_stack.setCurrentIndex(0)

        layout.addWidget(self.content_stack)
        
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        # 狀態欄
        self.statusBar().showMessage('就緒')
    
    def setup_menu(self):
        """設置菜單欄"""
        menubar = self.menuBar()
        
        # File 菜單
        file_menu = menubar.addMenu('檔案')
        
        new_action = file_menu.addAction('新建專案')
        new_action.triggered.connect(self.on_new_project)
        
        open_action = file_menu.addAction('開啟專案')
        open_action.triggered.connect(self.on_open_project)
        
        save_action = file_menu.addAction('儲存專案')
        save_action.triggered.connect(self.on_save_project)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction('離開')
        exit_action.triggered.connect(self.close)
        
        # Help 菜單
        help_menu = menubar.addMenu('說明')
        about_action = help_menu.addAction('關於')
        about_action.triggered.connect(self.on_about)

        # View 菜單
        view_menu = menubar.addMenu('檢視')
        preview_action = view_menu.addAction('預覽播放器')
        preview_action.triggered.connect(self.on_preview_player)
    
    def on_import_video(self):
        """導入影片"""
        dialog = ImportVideoDialog(self)
        dialog.validation_error.connect(self.on_validation_error)
        
        if dialog.exec_() == ImportVideoDialog.Accepted:
            file_path = dialog.selected_file

            # 選擇輸出選項
            options_dialog = OutputOptionsDialog(self)
            if options_dialog.exec_() != OutputOptionsDialog.Accepted:
                return
            output_options = options_dialog.get_selected_outputs()  # 輸出選項
            
            # 更新專案狀態
            self.project.video_path = file_path
            self.project.project_name = Path(file_path).stem
            
            # 建立輸出目錄
            stems_dir = f"output/{self.project.project_name}/stems"
            os.makedirs(stems_dir, exist_ok=True)
            self.project.stems_dir = stems_dir
            
            # 開始分離（背景執行）
            self._start_separation(file_path, output_options)
            
            logger.info(f"Import started: {file_path}")

    def on_edit_lyrics(self):
        """編輯歌詞"""
        self.content_stack.setCurrentWidget(self.lyrics_panel)
        self.lyrics_panel.setFocus()
        self.statusBar().showMessage('已進入歌詞編輯')

    def on_preview_player(self):
        """開啟預覽播放器"""
        self._sync_preview_player()
        self.content_stack.setCurrentWidget(self.preview_player)
        self.preview_player.setFocus()
        self.statusBar().showMessage('已進入預覽播放器')

    def _sync_preview_player(self):
        """同步預覽播放器資料"""
        if self.project.video_path:
            self.preview_player.set_media(self.project.video_path)
        elif self.project.stems:
            audio_path = (
                self.project.stems.get('music')
                or self.project.stems.get('original')
            )
            if audio_path:
                self.preview_player.set_media(audio_path)
        if self.project.lrc_timeline:
            self.preview_player.set_timeline(self.project.lrc_timeline)
    
    def _start_separation(self, video_path: str, output_options: dict):
        """開始音源分離"""
        # 顯示進度對話框
        progress_dialog = ProgressDialog(self, "正在分離音訊...")
        progress_dialog.show()
        
        # 建立工作線程
        self.separation_worker = SeparationWorker(
            video_path,
            self.project.stems_dir,
            output_options,
        )
        self.separation_worker.progress.connect(progress_dialog.update)
        self.separation_worker.message.connect(lambda msg: progress_dialog.update(progress_dialog.progress_bar.value(), msg))
        self.separation_worker.finished.connect(
            lambda stems: self._on_separation_complete(stems, progress_dialog)
        )
        self.separation_worker.error.connect(
            lambda err: self._on_separation_error(err, progress_dialog)
        )
        self.separation_worker.start()
    
    def _on_separation_complete(self, stems: dict, progress_dialog):
        """分離完成"""
        progress_dialog.accept()
        
        self.project.stems = stems
        original_path = stems.get('original')
        if original_path:
            self.lyrics_panel.set_audio_file(original_path)
        self.statusBar().showMessage('音訊分離完成')
        
        # 更新 UI
        self.edit_btn.setEnabled(True)
        self._update_status()
        
        QMessageBox.information(
            self,
            '完成',
            f'音訊分離完成！\n\n輸出位置：\n{self.project.stems_dir}'
        )
        
        logger.info(f"Separation complete: {stems}")
    
    def _on_separation_error(self, error: str, progress_dialog):
        """分離出錯"""
        progress_dialog.reject()
        
        logger.error(f"Separation error: {error}")
        QMessageBox.critical(
            self,
            '錯誤',
            f'音訊分離失敗：\n{error}'
        )
        
        self.statusBar().showMessage('音訊分離失敗')

    def on_export_video(self):
        """匯出影片"""
        if not self.project.video_path:
            QMessageBox.warning(self, '提醒', '請先匯入影片')
            return
        if not self.project.lrc_timeline:
            QMessageBox.warning(self, '提醒', '請先載入字幕')
            return

        workflow = KaraokeWorkflow()
        ass_path = self._ensure_ass_file(workflow)
        if not ass_path:
            QMessageBox.warning(self, '提醒', '無法產生 ASS 字幕')
            return

        audio_path = self._get_default_audio_path()
        if not audio_path:
            audio_path, _ = QFileDialog.getOpenFileName(
                self,
                "選擇音訊檔案",
                "",
                "音訊檔案 (*.wav *.mp3 *.flac *.m4a);;所有檔案 (*)",
            )
            if not audio_path:
                return

        default_output = ""
        if self.project.project_name:
            default_output = f"output/{self.project.project_name}/export.mp4"

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "儲存輸出影片",
            default_output,
            "MP4 檔案 (*.mp4);;所有檔案 (*)",
        )
        if not output_path:
            return

        self._start_render(self.project.video_path, audio_path, ass_path, output_path)

    def _ensure_ass_file(self, workflow: KaraokeWorkflow) -> str:
        """確保 ASS 字幕存在"""
        if self.project.ass_file_path and Path(self.project.ass_file_path).exists():
            return self.project.ass_file_path

        stems_dir = self.project.stems_dir
        if not stems_dir:
            stems_dir = f"output/{self.project.project_name or 'export'}/stems"
            os.makedirs(stems_dir, exist_ok=True)
            self.project.stems_dir = stems_dir

        ass_path, ass_content = workflow.ensure_ass_file(self.project.lrc_timeline, stems_dir)
        self.project.ass_file_path = ass_path
        self.project.ass_content = ass_content
        return ass_path

    def _get_default_audio_path(self) -> Optional[str]:
        """取得預設音訊路徑"""
        if not self.project.stems:
            return None
        return (
            self.project.stems.get('music')
            or self.project.stems.get('original')
        )

    def _start_render(self, video_path: str, audio_path: str, subtitle_path: str, output_path: str):
        """開始影片輸出"""
        progress_dialog = ProgressDialog(self, "正在輸出影片...")
        progress_dialog.show()

        self.render_worker = RenderWorker(video_path, audio_path, subtitle_path, output_path)
        self.render_worker.progress.connect(progress_dialog.update)
        self.render_worker.message.connect(
            lambda msg: progress_dialog.update(progress_dialog.progress_bar.value(), msg)
        )
        self.render_worker.finished.connect(
            lambda out_path: self._on_render_complete(out_path, progress_dialog)
        )
        self.render_worker.error.connect(
            lambda err: self._on_render_error(err, progress_dialog)
        )
        self.render_worker.start()

    def _on_render_complete(self, output_path: str, progress_dialog):
        """輸出完成"""
        progress_dialog.accept()
        self.project.output_path = output_path
        self._update_status()
        self.statusBar().showMessage('影片輸出完成')
        QMessageBox.information(self, '完成', f'影片已輸出：\n{output_path}')

    def _on_render_error(self, error: str, progress_dialog):
        """輸出失敗"""
        progress_dialog.reject()
        QMessageBox.critical(self, '錯誤', f'影片輸出失敗：\n{error}')
    
    def on_validation_error(self, error_msg: str):
        """文件驗證錯誤"""
        logger.warning(f"File validation error: {error_msg}")
        QMessageBox.warning(self, '檔案驗證失敗', error_msg)

    def _format_state(self, state: str) -> str:
        """狀態轉中文顯示"""
        mapping = {
            'EMPTY': '空專案',
            'VIDEO_UPLOADED': '已匯入影片',
            'STEMS_READY': '音訊已準備',
            'LRC_READY': '字幕已準備',
            'SUBTITLE_CONVERTED': '字幕已轉換',
            'EXPORT_COMPLETE': '匯出完成',
        }
        return mapping.get(state, state)
    
    def _update_status(self):
        """更新狀態顯示"""
        state = self.project.get_state()
        state_text = self._format_state(state)
        self.status_label.setText(f'目前狀態：{state_text}')
        
        info = f"專案狀態：{state_text}\n"
        info += f"專案名稱：{self.project.project_name}\n"
        info += f"影片路徑：{self.project.video_path}\n"
        info += f"音訊輸出：{self.project.stems_dir}\n"
        if self.project.lrc_timeline:
            info += f"字幕行數：{len(self.project.lrc_timeline.lines)}"
        else:
            info += "字幕行數：無"

        self.info_label.setText(info)
        self._update_action_states()

    def _update_action_states(self):
        """更新按鈕狀態"""
        has_video = bool(self.project.video_path)
        has_lrc = bool(self.project.lrc_timeline)
        self.preview_btn.setEnabled(has_video and has_lrc)

    def _on_lrc_loaded(self, loaded: bool):
        """字幕載入狀態變更"""
        if not loaded:
            self.project.lrc_timeline = None
        self._update_action_states()
    
    def on_new_project(self):
        """新建專案"""
        self.project = KaraokeProject()
        self.lyrics_panel.set_project(self.project)
        self.content_stack.setCurrentIndex(0)
        self.edit_btn.setEnabled(True)
        self.export_btn.setEnabled(False)
        self._update_status()
        self.statusBar().showMessage('已建立新專案')
        logger.info("New project created")
    
    def on_open_project(self):
        """開啟專案（暫未實現）"""
        QMessageBox.information(self, '提示', '開啟專案功能尚未實作')
    
    def on_save_project(self):
        """保存專案"""
        if not self.project.project_name:
            QMessageBox.warning(self, '提醒', '請先匯入影片')
            return
        
        project_path = f"output/{self.project.project_name}/project.json"
        os.makedirs(os.path.dirname(project_path), exist_ok=True)
        self.project.save_to_json(project_path)
        
        self.statusBar().showMessage(f'專案已儲存：{project_path}')
        logger.info(f"Project saved: {project_path}")
    
    def on_about(self):
        """關於"""
        QMessageBox.about(
            self,
            '關於',
            'Train Bookara Maker v2\n\n'
            '日文伴唱影片製作工具。\n\n'
            'Phase 1.1：影片匯入與音訊分離'
        )
    
    def closeEvent(self, event):
        """關閉窗口"""
        reply = QMessageBox.question(
            self,
            '確認離開',
            '要在離開前儲存專案嗎？',
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
        )
        
        if reply == QMessageBox.Yes:
            self.on_save_project()
            event.accept()
        elif reply == QMessageBox.No:
            event.accept()
        else:
            event.ignore()
        
        logger.info("Application closed")


if __name__ == "__main__":
    import sys
    import logging
    from PyQt5.QtWidgets import QApplication
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
