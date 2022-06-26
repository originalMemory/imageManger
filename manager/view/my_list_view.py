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

from PyQt6 import QtWidgets, QtGui
from PyQt6.QtCore import Qt

from helper.file_helper import FileHelper


class MyListView(QtWidgets.QListView):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.__context_menu = QtWidgets.QMenu()
        self.__key_delegate = None
        self.__action_show_file_directory_delegate = None
        self.__create_context_menu()

    def set_key_press_delegate(self, delegate):
        self.__key_delegate = delegate

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if self.__key_delegate is None or not self.__key_delegate(event):
            super().keyPressEvent(event)

    def __create_context_menu(self):
        """
        创建右键菜单
        :return:
        """
        # 必须将ContextMenuPolicy设置为Qt.CustomContextMenu
        # 否则无法使用customContextMenuRequested信号
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.__show_context_menu)

        # 创建 menu
        open_file_directory = self.__context_menu.addAction("打开文件所在目录")
        open_file_directory.triggered.connect(self.__show_file_directory)

    def __show_context_menu(self, pos):
        """
        右键点击时调用参数
        :param pos:
        :return:
        """
        print(pos)
        self.__context_menu.move(QtGui.QCursor().pos())
        self.__context_menu.show()

    def set_action_show_file_directory_delegate(self, delegate):
        """
        打开文件所在目录 action 执行内容
        :param delegate:
        :return:
        """
        self.__action_show_file_directory_delegate = delegate

    def __show_file_directory(self):
        self.__action_show_file_directory_delegate()
