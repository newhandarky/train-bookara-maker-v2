"""
Video import dialog widget
Phase 1.1.1: 文件上傳 UI
"""

import os
import logging
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QProgressBar, QMessageBox, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class ImportVideoDialog(QDialog):
    """導入影片對話框"""
    
    # 信號
    file_selected = pyqtSignal(str)  # 文件路徑
    validation_error = pyqtSignal(str)  # 驗證錯誤
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_file = None
        self.init_ui()
        self.setWindowTitle("匯入影片")
        self.resize(500, 200)
    
    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout()
        
        # 標題
        title = QLabel("選擇 MP4 影片檔案")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        # 文件路徑顯示
        file_layout = QHBoxLayout()
        self.file_path_label = QLineEdit()
        self.file_path_label.setReadOnly(True)
        self.file_path_label.setPlaceholderText("尚未選擇檔案")
        file_layout.addWidget(QLabel("檔案："))
        file_layout.addWidget(self.file_path_label)
        layout.addLayout(file_layout)
        
        # 按鈕
        button_layout = QHBoxLayout()
        
        browse_btn = QPushButton("瀏覽")
        browse_btn.clicked.connect(self.on_browse_clicked)
        button_layout.addWidget(browse_btn)
        
        button_layout.addStretch()
        
        ok_btn = QPushButton("確定")
        ok_btn.clicked.connect(self.on_ok_clicked)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 進度條（隱藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def on_browse_clicked(self):
        """瀏覽文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            '選擇 MP4 檔案',
            '',
            'MP4 Files (*.mp4);;All Files (*)'
        )
        
        if file_path:
            if self.validate_file(file_path):
                self.selected_file = file_path
                self.file_path_label.setText(file_path)
                logger.info(f"File selected: {file_path}")
            else:
                self.selected_file = None
                self.file_path_label.setText("")
    
    def validate_file(self, file_path: str) -> bool:
        """
        驗證文件
        
        檢查項目：
        - 文件存在性
        - 文件格式（.mp4）
        - 文件大小（< 500MB）
        """
        try:
            path = Path(file_path)
            
            # 檢查存在性
            if not path.exists():
                error_msg = f"檔案不存在：{file_path}"
                logger.error(error_msg)
                self.validation_error.emit(error_msg)
                return False
            
            # 檢查格式
            if path.suffix.lower() != '.mp4':
                error_msg = f"格式錯誤，需為 .mp4：{path.suffix}"
                logger.error(error_msg)
                self.validation_error.emit(error_msg)
                return False
            
            # 檢查大小
            file_size_mb = path.stat().st_size / (1024 * 1024)
            if file_size_mb > 500:
                error_msg = f"檔案過大：{file_size_mb:.1f}MB（上限 500MB）"
                logger.error(error_msg)
                self.validation_error.emit(error_msg)
                return False
            
            logger.info(f"File validation passed: {file_path} ({file_size_mb:.1f}MB)")
            return True
        
        except Exception as e:
            error_msg = f"檔案驗證失敗：{e}"
            logger.error(error_msg)
            self.validation_error.emit(error_msg)
            return False
    
    def on_ok_clicked(self):
        """確認選擇"""
        if self.selected_file:
            self.file_selected.emit(self.selected_file)
            self.accept()
        else:
            QMessageBox.warning(self, "提醒", "請先選擇檔案")


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    dialog = ImportVideoDialog()
    dialog.show()
    sys.exit(app.exec_())
