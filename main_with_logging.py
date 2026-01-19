"""
train-bookara-maker-v2 - Main Entry Point
"""

import sys
import logging

from PyQt5.QtWidgets import QApplication

from gui.main_window import MainWindow

# 設定 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bookara-maker.log'),  # 寫到檔案
        logging.StreamHandler(sys.stdout)           # 也輸出到 terminal
    ]
)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
