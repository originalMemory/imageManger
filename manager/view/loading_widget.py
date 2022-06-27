#!/user/bin/env python3
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : loading_widget.py
@author  : illusion
@desc    :
@create  : 2022-06-26 13:49:53
"""
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QFont, QFontMetrics, QMovie, QMoveEvent
from PyQt6.QtWidgets import QMainWindow, QLabel, QHBoxLayout, QWidget, QPushButton, QVBoxLayout, QProgressBar


class LoadingMask(QMainWindow):
    def __init__(self, parent):
        super(LoadingMask, self).__init__(parent)

        self.label_tip = QLabel()
        font = QFont('Microsoft YaHei', 11, QFont.Weight.Normal)
        self.label_tip.setFont(font)
        width = 200
        self.label_tip.setFixedWidth(width)
        self.label_tip.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.movie = QMovie('images/loading.gif')
        self.label_img = QLabel()
        self.label_img.setMovie(self.movie)
        self.label_img.setFixedSize(QSize(160, 160))
        self.label_img.setScaledContents(True)
        self.movie.start()

        self.pb = QProgressBar()
        self.pb.setFixedWidth(width)

        layout = QVBoxLayout()
        widget = QWidget()
        widget.setLayout(layout)
        layout.addWidget(self.label_img)
        layout.addWidget(self.pb)
        layout.addWidget(self.label_tip)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.setCentralWidget(widget)
        self.setWindowOpacity(0.5)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.hide()

    def show_with_param(self, tip='加载中', progress=None):
        self.update(tip, progress)
        self.move(self.parent().geometry().x(), self.parent().geometry().y())
        self.setFixedSize(QSize(self.parent().geometry().width(), self.parent().geometry().height()))
        self.show()

    def update(self, tip=None, progress=None):
        if not self.label_tip.text():
            self.label_tip.hide()
        if not self.pb.value():
            self.pb.hide()
        if tip:
            metrics = QFontMetrics(self.label_tip.font())
            new_tip = metrics.elidedText(tip, Qt.TextElideMode.ElideRight, self.label_tip.width())
            self.label_tip.setText(new_tip)
            self.label_tip.show()
        if progress is not None:
            self.pb.setValue(progress)
            self.pb.show()

    @staticmethod
    def showToast(window, tip='加载中...', duration=500):
        mask = LoadingMask(window, tip=tip)
        mask.show_with_param(tip, duration)


if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    widget = QWidget()
    widget.setFixedSize(500, 500)
    widget.setStyleSheet('QWidget{background-color:white;}')

    button = QPushButton('button')
    layout = QHBoxLayout()
    layout.addWidget(button)
    widget.setLayout(layout)

    loading_mask = LoadingMask(widget, '../../images/loading.gif', '加载中')
    loading_mask.show()
    widget.installEventFilter(loading_mask)
    widget.show()

    sys.exit(app.exec())
