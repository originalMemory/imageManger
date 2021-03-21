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
import os
import random
import threading
import time
from enum import Enum, unique
from functools import partial

import pyperclip
import win32api
import win32con
import win32gui
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QMessageBox, QSystemTrayIcon

from helper.config_helper import ConfigHelper
from helper.db_helper import DBHelper
from helper.display_helper import DisplayHelper
from helper.image_helper import ImageHelper
from tray.view.tray_setting import Ui_TraySetting


@unique
class ChangeType(Enum):
    Order = 0
    Random = 1


class TraySetting(QtWidgets.QWidget, Ui_TraySetting):
    __config_section_background = "background"
    __config_key_change_type = "changeType"
    __config_key_last_order_image_offset = "lastOrderImageOffset"
    _monitor_sizes = []  # 显示器屏幕尺寸列表
    _cur_images = []  # 当前展示图片列表
    _cur_image_path_actions = []  # 当前展示图片地址项
    _cur_image_level_actions = []  # 当前展示图片等级列表

    def __init__(self, parent=None):
        super(TraySetting, self).__init__(parent)
        self.setupUi(self)

        # 初始化数据
        self.__db_helper = DBHelper(self)
        self.__config_helper = ConfigHelper(self)
        self.__sql_where = self.__config_helper.get_config_key(self.__config_section_background, "sqlWhere")
        self.textEdit_sqlWhere.setText(self.__sql_where)
        self.__time_interval = int(
            self.__config_helper.get_config_key(self.__config_section_background, "timeIntervalInMin"))
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

        # 创建显示器对应壁纸项
        self.__levels = self.__db_helper.get_model_data_list('level')
        self.create_monitor_menu(menu)

        # 壁纸切换方式
        self.__change_type_actions = list()
        self.create_change_type_menu(menu)

        switch_next = QtWidgets.QAction("切换下一张", self)
        switch_next.triggered.connect(self.__change_background)
        menu.addAction(switch_next)
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

        threading.Thread(target=self.__change_windows_background_timely, daemon=True).start()

    def create_monitor_menu(self, menu):
        """
        创建多显示器的菜单项
        :param menu:
        :return:
        """
        self._monitor_sizes = DisplayHelper.monitor_sizes()
        for i in range(len(self._monitor_sizes)):
            action = QtWidgets.QAction("", self)
            action.triggered.connect(partial(self.__open_file_in_directory_and_copy_file_name, i))
            menu.addAction(action)
            self._cur_image_path_actions.append(action)

            # 更新等级
            if self._monitor_sizes[i][0] > self._monitor_sizes[i][1]:
                screen_state = '横屏'
            else:
                screen_state = '竖屏'
            level_menu = menu.addMenu(f" {i + 1} {screen_state} - 等级")
            actions = []
            for level in self.__levels:
                level_action = level_menu.addAction(level.name)
                level_action.setCheckable(True)
                level_action.triggered.connect(partial(self.__set_level, i, level.id))
                actions.append(level_action)
            self._cur_image_level_actions.append(actions)
            menu.addSeparator()

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

    def __change_windows_background_timely(self):
        while True:
            sleep_second = self.__time_interval * 60
            if self.__change_background():
                time.sleep(sleep_second)

    def __change_background(self):
        """
        修改桌面壁纸
        :return:
        """
        image_info_list = []
        for size in self._monitor_sizes:
            image_info = self._get_image(size[0] >= size[1])
            if len(image_info) and image_info[0] is not None and os.path.exists(image_info[0].path):
                image_info_list.append(image_info)
        self._cur_images = [i[0] for i in image_info_list]
        if len(image_info_list) != len(self._monitor_sizes):
            QMessageBox.information(self, "提示", "sql 语句限制过多，获取不到图片", QMessageBox.Ok)
            return False

        images = []
        for i in range(len(image_info_list)):
            image, index, count = image_info_list[i]
            desc = f"[{index}/{count}] {image.author} - {image.filename}"
            if len(desc) > 50:
                desc = f"{desc[0:46]}..."
            path_action = self._cur_image_path_actions[i]
            path_action.setText(desc)
            self.__update_level_action(i, image.level_id)

            image_data = ImageHelper.get_sized_image(image.path, size=self._monitor_sizes[i])
            if image_data:
                images.append(image_data)
        final_image_name = "final.jpg"
        ImageHelper.merge_horizontal_img(
            images,
            int(self.__config_helper.get_config_key(self.__config_section_background, 'vertical_offset', "0")),
            final_image_name
        )
        path = os.path.join(os.getcwd(), final_image_name)
        key = win32api.RegOpenKeyEx(win32con.HKEY_CURRENT_USER, "Control Panel\\Desktop", 0, win32con.KEY_SET_VALUE)
        win32api.RegSetValueEx(key, "WallpaperStyle", 0, win32con.REG_SZ, "0")
        win32api.RegSetValueEx(key, "TileWallpaper", 0, win32con.REG_SZ, "1")
        win32gui.SystemParametersInfo(win32con.SPI_SETDESKWALLPAPER, path, 1 + 2)
        return True

    def _get_image(self, is_horizontal):
        """
        从数据库获取下一张图片
        :param is_horizontal: 是否是横图
        :return: (图片信息，索引，总数)
        """
        sql_where = self.__sql_where
        if is_horizontal:
            operator = '>='
        else:
            operator = '<='
        sql_where += f' and width{operator}height'
        image_count = self.__db_helper.get_image_count(sql_where)
        if self.__change_type == ChangeType.Order:
            offset = self.__get_order_offset(image_count)
        else:
            offset = random.randint(0, image_count)
        image = self.__db_helper.get_one_image_with_where(sql_where, offset)
        print(f'where: {sql_where}, id: {image.id}, width: {image.width}, height: {image.height}, path: {image.path}')
        return image, offset, image_count

    def __get_order_offset(self, image_count):
        """
        获取顺序切换时下一张图片的偏移量
        :param image_count: 图片总数
        :return: 偏移量
        """
        if self.__last_order_image_offset < image_count - 1:
            offset = self.__last_order_image_offset + 1
        else:
            offset = 0
        self.__last_order_image_offset = offset
        self.__config_helper.add_config_key(
            self.__config_section_background,
            self.__config_key_last_order_image_offset,
            self.__last_order_image_offset
        )
        if self.isHidden():
            self.lineEdit_order_offset.setText(str(offset))
        return offset

    def __update_level_action(self, index, level_id):
        """
        更新当前显示器壁纸等级状态
        :param index: 显示器索引
        :param level_id: 等级 id
        :return:
        """
        level_actions = self._cur_image_level_actions[index]
        for i in range(len(self.__levels)):
            level = self.__levels[i]
            level_actions[i].setChecked(level.id == level_id)

    def __on_tray_click(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.Trigger:
            self.show()
            return

    def __open_file_in_directory_and_copy_file_name(self, index):
        image = self._cur_images[index]
        file_path = image.path.replace('/', '\\')
        ex = f"explorer /select,{file_path}"
        os.system(ex)
        pyperclip.copy(image.filename)

    def __set_level(self, index, level_id):
        image = self._cur_images[index]
        image.level_id = level_id
        self.__db_helper.update_image(image)
        self.__update_level_action(index, level_id)
