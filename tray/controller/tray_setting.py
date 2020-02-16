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
from enum import Enum, unique
from functools import partial

import pyperclip
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QMessageBox, QSystemTrayIcon

from helper.config_helper import ConfigHelper
from helper.db_helper import DBHelper
from tray.view.tray_setting import Ui_TraySetting


@unique
class ChangeType(Enum):
    Order = 0
    Random = 1


class TraySetting(QtWidgets.QWidget, Ui_TraySetting):

    __config_section_history = "history"
    __config_section_background = "background"
    __config_key_change_type = "changeType"
    __config_key_last_order_image_offset = "lastOrderImageOffset"

    def __init__(self, parent=None):
        super(TraySetting, self).__init__(parent)
        self.setupUi(self)

        # 初始化数据
        self.__db_helper = DBHelper(self)
        self.__config_helper = ConfigHelper(self)
        self.__sql_where = self.__config_helper.get_config_key(self.__config_section_background, "sqlWhere")
        self.textEdit_sqlWhere.setText(self.__sql_where)
        self.__time_interval = int(self.__config_helper.get_config_key(self.__config_section_background, "timeIntervalInMin"))
        self.lineEdit_min.setText(str(self.__time_interval))

        self.__current_image = None

        self.pushButton_save.pressed.connect(self.__save)
        self.pushButton_cancel.pressed.connect(self.hide)

        # 系统托盘
        self.__tray = QtWidgets.QSystemTrayIcon()
        self.__tray.setIcon(QtGui.QIcon("images/tranIcon.png"))
        self.__tray.setToolTip("壁纸切换")
        self.__tray.activated[QSystemTrayIcon.ActivationReason].connect(self.__on_tray_click)
        menu = QtWidgets.QMenu()
        self.__current_image_action = QtWidgets.QAction("", self)
        self.__current_image_action.triggered.connect(self.__open_file_in_directory_and_copy_file_name)
        menu.addAction(self.__current_image_action)

        # 更新等级
        level_menu = menu.addMenu("等级")
        self.__levels = self.__db_helper.get_model_data_list('level')
        self.__level_actions = list()
        for i in range(len(self.__levels)):
            level = self.__levels[i]
            level_action = level_menu.addAction(level.name)
            level_action.setCheckable(True)
            level_action.triggered.connect(partial(self.__set_level, level.id))
            self.__level_actions.append(level_action)

        # 壁纸切换方式
        menu.addSeparator()
        self.__change_type_actions = list()
        self.create_change_type_menu(menu)
        # 加载默认参数
        type_value = self.__config_helper.get_config_key(
            self.__config_section_background,
            self.__config_key_change_type,
            ChangeType.Order.value
        )
        self.__change_type = ChangeType(int(type_value))
        self.__update_change_type_action(self.__change_type)
        offset = self.__config_helper.get_config_key(
            self.__config_section_background,
            self.__config_key_last_order_image_offset,
            0
        )
        self.__last_order_image_offset = int(offset)

        menu.addSeparator()
        setting = QtWidgets.QAction("设置", self)
        setting.triggered.connect(self.show)
        menu.addAction(setting)
        close = QtWidgets.QAction("退出", self)
        close.triggered.connect(self.close)
        menu.addAction(close)
        self.__tray.setContextMenu(menu)
        self.__tray.show()

        threading.Thread(target=self.__change_windows_background, daemon=True).start()

    def create_change_type_menu(self, menu):
        change_type_menu = menu.addMenu("切换方式")
        change_order = self.__create_type_action("顺序", ChangeType.Order)
        change_type_menu.addAction(change_order)
        self.__change_type_actions.append(change_order)
        change_random = self.__create_type_action("随机", ChangeType.Random)
        change_type_menu.addAction(change_random)
        self.__change_type_actions.append(change_random)

    def __create_type_action(self, name, change_type):
        action = QtWidgets.QAction(name, self)
        action.setCheckable(True)
        action.triggered.connect(partial(self.__set_change_type, change_type))
        return action

    def __set_change_type(self, change_type: ChangeType):
        self.__change_type = change_type
        self.__update_change_type_action(change_type)

    def __update_change_type_action(self, change_type: ChangeType):
        if change_type == ChangeType.Order:
            self.__change_type_actions[0].setChecked(True)
            self.__change_type_actions[1].setChecked(False)
        elif change_type == ChangeType.Random:
            self.__change_type_actions[0].setChecked(False)
            self.__change_type_actions[1].setChecked(True)
        self.__config_helper.add_config_key(
            self.__config_section_background,
            self.__config_key_change_type,
            change_type.value
        )

    def __save(self):
        self.__sql_where = self.textEdit_sqlWhere.toPlainText()
        time_interval = self.lineEdit_min.text()
        self.__time_interval = int(time_interval)
        self.__config_helper.add_config_key("background", "sqlWhere", self.__sql_where)
        self.__config_helper.add_config_key("background", "timeIntervalInMin", time_interval)
        self.__last_order_image_offset = int(self.lineEdit_order_offset.text())
        self.__config_helper.add_config_key(
            self.__config_section_background,
            self.__config_key_last_order_image_offset,
            self.__last_order_image_offset
        )
        self.hide()

    def __change_windows_background(self):
        SPI_SETDESKWALLPAPER = 20
        while True:
            sleep_second = self.__time_interval * 60
            image_count = self.__db_helper.get_image_count(self.__sql_where)
            if self.__change_type == ChangeType.Order:
                offset = self.__get_order_offset(image_count)
            else:
                offset = random.randint(0, image_count)
            image = self.__db_helper.get_one_image_with_where(self.__sql_where, offset)
            if not image:
                QMessageBox.information(self, "提示", "sql 语句限制过多，获取不到图片", QMessageBox.Ok)
                time.sleep(sleep_second)
                continue

            if not os.path.exists(image.path):
                continue
            self.__current_image = image
            print(image)
            # 更换背景图
            ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, image.path, 0)

            image_info = f"[{offset}/{image_count}] {image.author} - {image.filename}"
            if len(image_info) > 50:
                image_info = f"{image_info[0:46]}..."
            self.__current_image_action.setText(image_info)
            self.__update_level_action(image.level_id)
            time.sleep(sleep_second)

    def __get_order_offset(self, image_count):
        if self.__last_order_image_offset < image_count - 1:
            offset = self.__last_order_image_offset + 1
        else:
            offset = 0
        self.__last_order_image_offset = offset
        self.__config_helper.add_config_key(
            self.__config_section_history,
            self.__config_key_last_order_image_offset,
            self.__last_order_image_offset
        )
        if self.isHidden():
            self.lineEdit_order_offset.setText(str(offset))
        return offset

    def __update_level_action(self, level_id):
        for i in range(len(self.__levels)):
            level = self.__levels[i]
            if level.id == level_id:
                self.__level_actions[i].setChecked(True)
            else:
                self.__level_actions[i].setChecked(False)

    def __on_tray_click(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.Trigger:
            self.show()
            return

    def __open_file_in_directory_and_copy_file_name(self):
        if not self.__current_image:
            return
        file_path = self.__current_image.path.replace('/', '\\')
        ex = f"explorer /select,{file_path}"
        os.system(ex)
        pyperclip.copy(self.__current_image.filename)

    def __set_level(self, level_id):
        self.__current_image.level_id = level_id
        self.__db_helper.update_image(self.__current_image)
        self.__update_level_action(level_id)
