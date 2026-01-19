"""
Progress dialog widget
Phase 1.1.4: 進度對話框
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class ProgressDialog(QDialog):
    """進度對話框"""
    
    cancel_requested = pyqtSignal()
    
    def __init__(self, parent=None, title="Processing"):
        super().__init__(parent)
        self.init_ui(title)
        self.setWindowTitle(title)
        self.resize(400, 150)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
    
    def init_ui(self, title):
        """初始化 UI"""
        layout = QVBoxLayout()
        
        # 標題
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(title_label)
        
        # 進度條
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)
        
        # 狀態標籤
        self.status_label = QLabel("Starting...")
        layout.addWidget(self.status_label)
        
        # 取消按鈕
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.on_cancel)
        layout.addWidget(cancel_btn)
        
        self.setLayout(layout)
    
    def update(self, progress: int, message: str = ""):
        """更新進度"""
        self.progress_bar.setValue(progress)
        if message:
            self.status_label.setText(message)
    
    def on_cancel(self):
        """取消操作"""
        self.cancel_requested.emit()
        self.reject()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    dialog = ProgressDialog(title="Processing Video...")
    dialog.show()
    sys.exit(app.exec_())
