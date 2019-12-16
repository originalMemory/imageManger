#!/user/bin/env python
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : traySetting
@author  : wuhoubo
@desc    : 系统托盘参数设置
@create  : 2019/12/15 14:24:52
@update  :
"""
import ctypes
import os
import random
import threading
import time

import pyperclip
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QMessageBox, QSystemTrayIcon

from helper.config_helper import ConfigHelper
from helper.db_helper import DBHelper
from tray.view.tray_setting import Ui_TraySetting


class TraySetting(QtWidgets.QWidget, Ui_TraySetting):

    def __init__(self, parent=None):
        super(TraySetting, self).__init__(parent)
        self.setupUi(self)

        # 初始化数据
        self.db_helper = DBHelper(self)
        self.config_helper = ConfigHelper(self)
        self.sql_where = self.config_helper.get_config_key("background", "sqlWhere")
        self.textEdit_sqlWhere.setText(self.sql_where)
        self.time_interval = int(self.config_helper.get_config_key("background", "timeIntervalInMin"))
        self.lineEdit_min.setText(str(self.time_interval))

        self.current_image = None

        self.pushButton_save.pressed.connect(self.__save)
        self.pushButton_cancel.pressed.connect(self.hide)

        # 系统托盘
        self.tray = QtWidgets.QSystemTrayIcon()
        self.tray.setIcon(QtGui.QIcon("images/tranIcon.png"))
        self.tray.setToolTip("壁纸切换")
        self.tray.activated[QSystemTrayIcon.ActivationReason].connect(self.__on_tray_click)
        self.menu = QtWidgets.QMenu()
        self.current_image_action = QtWidgets.QAction("", self)
        self.current_image_action.triggered.connect(self.__open_file_in_directory_and_copy_file_name)
        self.menu.addAction(self.current_image_action)
        self.menu.addSeparator()
        setting = QtWidgets.QAction("设置", self)
        setting.triggered.connect(self.show)
        self.menu.addAction(setting)
        close = QtWidgets.QAction("退出", self)
        close.triggered.connect(self.close)
        self.menu.addAction(close)
        self.tray.setContextMenu(self.menu)
        self.tray.show()
        self.tray.showMessage("标题", "开始切换壁纸", icon=1)

        self.change_th = threading.Thread(target=self.__change_windows_background)
        self.change_th.start()

    def __save(self):
        self.sql_where = self.textEdit_sqlWhere.toPlainText()
        self.time_interval = int(self.lineEdit_min.text())
        self.config_helper.add_config_key("background", "sqlWhere", self.sql_where)
        self.config_helper.add_config_key("background", "timeIntervalInMin", self.time_interval)
        self.hide()

    def __change_windows_background(self):
        SPI_SETDESKWALLPAPER = 20
        while True:
            image_count = self.db_helper.get_image_count(self.sql_where)
            offset = random.randint(0, image_count)
            sleep_second = self.time_interval * 60
            image = self.db_helper.get_one_image_with_where(self.sql_where, offset)
            if not image:
                QMessageBox.information(self, "提示", "sql 语句限制过多，获取不到图片", QMessageBox.Ok)
                time.sleep(sleep_second)
                continue

            if not os.path.exists(image.path):
                continue
            self.current_image = image
            print(image)
            # 更换背景图
            ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, image.path, 0)
            image_info = f"{image.author} - {image.filename}"
            if len(image_info) > 50:
                image_info = f"{image_info[0:46]}..."
            self.current_image_action.setText(image_info)
            time.sleep(sleep_second)

    def __on_tray_click(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.Trigger:
            self.show()
            return

    def __open_file_in_directory_and_copy_file_name(self):
        if not self.current_image:
            return
        file_path = self.current_image.path.replace('/', '\\')
        ex = f"explorer /select,{file_path}"
        os.system(ex)
        pyperclip.copy(self.current_image.filename)
