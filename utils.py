# utils.py - PyQt5 Compatible
from PyQt5.QtWidgets import QPushButton, QLineEdit, QTextEdit
from PyQt5.QtGui import QCursor, QPixmap
from PyQt5.QtCore import Qt

class RoundedButton(QPushButton):
    def __init__(self, text="", icon_path=None, parent=None):
        super().__init__(text, parent)
        if icon_path:
            self.setIcon(QPixmap(icon_path))
        self.setCursor(QCursor(Qt.PointingHandCursor))

class RoundedTextInput(QLineEdit):
    def __init__(self, placeholder="", password=False, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        if password:
            self.setEchoMode(QLineEdit.Password)
        self.setCursor(QCursor(Qt.IBeamCursor))

class MultilineRoundedTextInput(QTextEdit):
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setCursor(QCursor(Qt.IBeamCursor))