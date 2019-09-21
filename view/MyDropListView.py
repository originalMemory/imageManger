#!/user/bin/env python
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : MyDropListView
@author  : wuhoubo
@desc    : 
@create  : 2019/8/25 17:57:16
@update  :
"""
from PyQt5 import QtWidgets, QtGui


class MyDropListView(QtWidgets.QListView):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:
        e.accept()

    def dropEvent(self, e: QtGui.QDropEvent) -> None:
        urls = e.mimeData().urls()
        self.model().clear()
        for url in urls:
            self.model().add_dir(url.toLocalFile())
