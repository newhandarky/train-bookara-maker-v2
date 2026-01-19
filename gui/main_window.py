"""
Main window for Train Bookara Maker v2
Phase 1.1.4: GUI Integration
"""

import os
import logging
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QMenuBar, QMenu, QStatusBar, QTabWidget
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from pipeline.project import KaraokeProject
from gui.widgets.import_dialog import ImportVideoDialog
from gui.widgets.progress_dialog import ProgressDialog
from gui.workers import SeparationWorker

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
        self.setWindowTitle('Train Bookara Maker v2')  # 【改這裡】窗口標題
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
        status_label = QLabel('Current Status: Empty Project')
        self.status_label = status_label
        layout.addWidget(status_label)
        
        # 按鈕區
        button_layout = QHBoxLayout()
        
        import_btn = QPushButton('1. Import Video')
        import_btn.setMinimumHeight(50)
        import_btn.clicked.connect(self.on_import_video)
        button_layout.addWidget(import_btn)
        
        edit_btn = QPushButton('2. Edit Lyrics')
        edit_btn.setMinimumHeight(50)
        edit_btn.setEnabled(False)
        self.edit_btn = edit_btn
        button_layout.addWidget(edit_btn)
        
        export_btn = QPushButton('3. Export Video')
        export_btn.setMinimumHeight(50)
        export_btn.setEnabled(False)
        self.export_btn = export_btn
        button_layout.addWidget(export_btn)
        
        layout.addLayout(button_layout)
        
        # 日誌區
        log_label = QLabel('Project Information:')
        layout.addWidget(log_label)
        
        self.info_label = QLabel(f'Project State: {self.project.get_state()}\nVideo Path: None\nStems: None')
        layout.addWidget(self.info_label)
        
        layout.addStretch()
        
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        # 狀態欄
        self.statusBar().showMessage('Ready')
    
    def setup_menu(self):
        """設置菜單欄"""
        menubar = self.menuBar()
        
        # File 菜單
        file_menu = menubar.addMenu('File')
        
        new_action = file_menu.addAction('New Project')
        new_action.triggered.connect(self.on_new_project)
        
        open_action = file_menu.addAction('Open Project')
        open_action.triggered.connect(self.on_open_project)
        
        save_action = file_menu.addAction('Save Project')
        save_action.triggered.connect(self.on_save_project)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction('Exit')
        exit_action.triggered.connect(self.close)
        
        # Help 菜單
        help_menu = menubar.addMenu('Help')
        about_action = help_menu.addAction('About')
        about_action.triggered.connect(self.on_about)
    
    def on_import_video(self):
        """導入影片"""
        dialog = ImportVideoDialog(self)
        dialog.validation_error.connect(self.on_validation_error)
        
        if dialog.exec_() == ImportVideoDialog.Accepted:
            file_path = dialog.selected_file
            
            # 更新專案狀態
            self.project.video_path = file_path
            self.project.project_name = Path(file_path).stem
            
            # 建立輸出目錄
            stems_dir = f"output/{self.project.project_name}/stems"
            os.makedirs(stems_dir, exist_ok=True)
            self.project.stems_dir = stems_dir
            
            # 開始分離（背景執行）
            self._start_separation(file_path)
            
            logger.info(f"Import started: {file_path}")
    
    def _start_separation(self, video_path: str):
        """開始音源分離"""
        # 顯示進度對話框
        progress_dialog = ProgressDialog(self, "Separating Audio...")
        progress_dialog.show()
        
        # 建立工作線程
        self.separation_worker = SeparationWorker(video_path, self.project.stems_dir)
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
        self.statusBar().showMessage('Audio separation complete')
        
        # 更新 UI
        self.edit_btn.setEnabled(True)
        self._update_status()
        
        QMessageBox.information(
            self,
            'Success',
            f'Audio separation complete!\n\nStems saved to:\n{self.project.stems_dir}'
        )
        
        logger.info(f"Separation complete: {stems}")
    
    def _on_separation_error(self, error: str, progress_dialog):
        """分離出錯"""
        progress_dialog.reject()
        
        logger.error(f"Separation error: {error}")
        QMessageBox.critical(
            self,
            'Error',
            f'Separation failed:\n{error}'
        )
        
        self.statusBar().showMessage('Separation failed')
    
    def on_validation_error(self, error_msg: str):
        """文件驗證錯誤"""
        logger.warning(f"File validation error: {error_msg}")
        QMessageBox.warning(self, 'Validation Error', error_msg)
    
    def _update_status(self):
        """更新狀態顯示"""
        state = self.project.get_state()
        self.status_label.setText(f'Current Status: {state}')
        
        info = f"Project State: {state}\n"
        info += f"Project Name: {self.project.project_name}\n"
        info += f"Video Path: {self.project.video_path}\n"
        info += f"Stems Dir: {self.project.stems_dir}"
        
        self.info_label.setText(info)
    
    def on_new_project(self):
        """新建專案"""
        self.project = KaraokeProject()
        self.edit_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self._update_status()
        self.statusBar().showMessage('New project created')
        logger.info("New project created")
    
    def on_open_project(self):
        """開啟專案（暫未實現）"""
        QMessageBox.information(self, 'Info', 'Open project feature coming soon')
    
    def on_save_project(self):
        """保存專案"""
        if not self.project.project_name:
            QMessageBox.warning(self, 'Warning', 'Please import a video first')
            return
        
        project_path = f"output/{self.project.project_name}/project.json"
        os.makedirs(os.path.dirname(project_path), exist_ok=True)
        self.project.save_to_json(project_path)
        
        self.statusBar().showMessage(f'Project saved: {project_path}')
        logger.info(f"Project saved: {project_path}")
    
    def on_about(self):
        """關於"""
        QMessageBox.about(
            self,
            'About',
            'Train Bookara Maker v2\n\n'
            'A tool for creating synchronized karaoke videos with Japanese lyrics.\n\n'
            'Phase 1.1: Video Import & Audio Separation'
        )
    
    def closeEvent(self, event):
        """關閉窗口"""
        reply = QMessageBox.question(
            self,
            'Confirm Exit',
            'Do you want to save the project before exiting?',
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
