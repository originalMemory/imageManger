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
from PyQt5.QtCore import Qt


class MyListView(QtWidgets.QListView):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.__key_delegate = None

    def set_key_press_delegate(self, delegate):
        self.__key_delegate = delegate

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if self.__key_delegate is None or not self.__key_delegate(event):
            super().keyPressEvent(event)
