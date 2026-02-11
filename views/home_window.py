from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class HomeWindow(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        title = QLabel("Home")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px;")

        layout.addWidget(title)
