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
import json
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
from PyQt6 import QtWidgets, QtGui
from PyQt6.QtWidgets import QMessageBox, QSystemTrayIcon
from screeninfo import get_monitors

from helper.config_helper import ConfigHelper
from helper.db_helper import DBHelper
from helper.image_helper import ImageHelper
from model.data import MonitorSetting, MyImage
from tray.view.tray_setting import Ui_TraySetting


@unique
class ChangeType(Enum):
    Order = 0
    Random = 1


class TraySetting(QtWidgets.QWidget, Ui_TraySetting):
    _config_section_background = "background"
    _config_key_change_type = "changeType"
    _config_key_last_order_image_offset = "lastOrderImageOffset"
    _monitor_start_y = 0
    _monitor_settings = []  # 显示器设定列表

    def _init_(self, parent=None):
        super(TraySetting, self)._init_(parent)
        self.setupUi(self)

        # 初始化数据
        self._db_helper = DBHelper(self)
        self._config_helper = ConfigHelper(self)
        fl = self._config_helper.get_config_key(self._config_section_background, "filter")
        if fl:
            fl = fl.replace('\\"', '"')[1:-1]
            self._fl = json.loads(fl)
            self.textEdit_sqlWhere.setText(fl)
        else:
            self._fl = {}
        self._time_interval = int(
            self._config_helper.get_config_key(self._config_section_background, "timeIntervalInMin"))
        self.lineEdit_min.setText(str(self._time_interval))

        self._current_image = None

        self.pushButton_save.pressed.connect(self._save)
        self.pushButton_cancel.pressed.connect(self.hide)

        # 系统托盘
        self._tray = QtWidgets.QSystemTrayIcon()
        self._tray.setIcon(QtGui.QIcon("images/tranIcon.png"))
        self._tray.setToolTip("壁纸切换")
        # self._tray.activated[QSystemTrayIcon.ActivationReason].connect(self._on_tray_click)
        menu = QtWidgets.QMenu()

        # 创建显示器对应壁纸项
        self._monitors = get_monitors()
        self._levels = self._db_helper.get_model_data_list('level')
        self.create_monitor_menu(menu)

        # 壁纸切换方式
        self._change_type_actions = list()
        self.create_change_type_menu(menu)

        switch_next = QtGui.QAction("切换下一张", self)
        switch_next.triggered.connect(self._change_background)
        menu.addAction(switch_next)
        # 加载默认参数
        type_value = self._config_helper.get_config_key(
            self._config_section_background,
            self._config_key_change_type,
            ChangeType.Order.value
        )
        self._change_type = ChangeType(int(type_value))
        self._update_change_type_action(self._change_type)
        offset = self._config_helper.get_config_key(
            self._config_section_background,
            self._config_key_last_order_image_offset,
            0
        )
        self._last_order_image_offset = int(offset)
        self.lineEdit_order_offset.setText(str(offset))

        menu.addSeparator()
        setting = QtGui.QAction("设置", self)
        setting.triggered.connect(self.show)
        menu.addAction(setting)
        close = QtGui.QAction("退出", self)
        close.triggered.connect(self.close)
        menu.addAction(close)
        self._tray.setContextMenu(menu)
        self._tray.show()

        threading.Thread(target=self._change_windows_background_timely, daemon=True).start()

    def create_monitor_menu(self, menu):
        """
        创建多显示器的菜单项
        :param menu:
        :return:
        """
        start_y = 0
        monitors = get_monitors()
        for i in range(len(monitors)):
            monitor = monitors[i]
            desc_action = QtGui.QAction("", self)
            desc_action.triggered.connect(partial(self._open_file_in_directory_and_copy_file_name, i))
            menu.addAction(desc_action)

            if monitor.width > monitor.height:
                screen_state = '横屏'
            else:
                screen_state = '竖屏'
            level_menu = menu.addMenu(f" {monitor.name} {screen_state} - 等级")
            level_actions = []
            for level in self._levels:
                level_action = level_menu.addAction(level.name)
                level_action.setCheckable(True)
                level_action.triggered.connect(partial(self._set_level, i, level.id))
                level_actions.append(level_action)
            menu.addSeparator()

            self._monitor_settings.append(
                MonitorSetting(monitor=monitor, image_desc_action=desc_action, image_level_actions=level_actions)
            )
            start_y = min(start_y, monitor.y)
        self._monitor_start_y = start_y

    def create_change_type_menu(self, menu):
        change_type_menu = menu.addMenu("切换方式")
        change_order = self._create_type_action("顺序", ChangeType.Order)
        change_type_menu.addAction(change_order)
        self._change_type_actions.append(change_order)
        change_random = self._create_type_action("随机", ChangeType.Random)
        change_type_menu.addAction(change_random)
        self._change_type_actions.append(change_random)

    def _create_type_action(self, name, change_type):
        action = QtGui.QAction(name, self)
        action.setCheckable(True)
        action.triggered.connect(partial(self._set_change_type, change_type))
        return action

    def _set_change_type(self, change_type: ChangeType):
        self._change_type = change_type
        self._update_change_type_action(change_type)

    def _update_change_type_action(self, change_type: ChangeType):
        if change_type == ChangeType.Order:
            self._change_type_actions[0].setChecked(True)
            self._change_type_actions[1].setChecked(False)
        elif change_type == ChangeType.Random:
            self._change_type_actions[0].setChecked(False)
            self._change_type_actions[1].setChecked(True)
        self._config_helper.add_config_key(
            self._config_section_background,
            self._config_key_change_type,
            change_type.value
        )

    def _save(self):
        fl = self.textEdit_sqlWhere.toPlainText()
        self._fl = json.loads(fl)
        time_interval = self.lineEdit_min.text()
        self._time_interval = int(time_interval)
        self._config_helper.add_config_key("background", "filter", json.dumps(fl))
        self._config_helper.add_config_key("background", "timeIntervalInMin", time_interval)
        self._last_order_image_offset = int(self.lineEdit_order_offset.text())
        self._config_helper.add_config_key(
            self._config_section_background,
            self._config_key_last_order_image_offset,
            self._last_order_image_offset
        )
        self.hide()

    def _change_windows_background_timely(self):
        while True:
            sleep_second = self._time_interval * 60
            if self._change_background():
                print(f'睡眠{sleep_second}s')
                time.sleep(sleep_second)

    def _change_background(self):
        """
        修改桌面壁纸
        :return:
        """
        images = []
        start_y_list = []
        i = 0
        while i < len(self._monitor_settings):
            setting = self._monitor_settings[i]
            image, index, count = self._get_image(setting.monitor.width >= setting.monitor.height)
            if image and os.path.exists(image.full_path()):
                setting.image = image
            else:
                continue
            filename = image.full_path().split('/')[-1]
            desc = f"[{index}/{count}] {','.join(image.authors)} - {filename}"
            if len(desc) > 50:
                desc = f"{desc[0:46]}..."
            setting.image_desc_action.setText(desc)
            self._update_level_action(i, image.level)

            try:
                image_data = ImageHelper.get_sized_image(
                    image.full_path(),
                    width=setting.monitor.width,
                    height=setting.monitor.height
                )
            except IOError as e:
                print(f'读取图片错误 - {e}')
                return False
            if image_data:
                images.append(image_data)
                start_y_list.append(setting.monitor.y - self._monitor_start_y)
            i += 1
        final_image_name = "final.jpg"
        ImageHelper.merge_horizontal_img(images, start_y_list, final_image_name)

        if len(images) != len(self._monitor_settings):
            QMessageBox.information(self, "提示", "sql 语句限制过多，获取不到图片",  QMessageBox.StandardButton.Ok)
            return False

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
        fl = self._fl
        if is_horizontal:
            fl['$expr'] = {'$gte': ['$width', '$height']}
        else:
            fl['$expr'] = {'$lte': ['$width', '$height']}
        image_count = self._db_helper.get_count(fl)
        if not image_count:
            return
        if self._change_type == ChangeType.Order:
            offset = self._get_order_offset(image_count)
        else:
            offset = random.randint(0, image_count)
        img = MyImage.from_dict(self._db_helper.img_col.find(fl).skip(offset).limit(1)[0])
        print(f'where: {json.dumps(fl)}, id: {img.id}, width: {img.width}, height: {img.height}, path: {img.path}')
        return img, offset, image_count

    def _get_order_offset(self, image_count):
        """
        获取顺序切换时下一张图片的偏移量
        :param image_count: 图片总数
        :return: 偏移量
        """
        if self._last_order_image_offset < image_count - 1:
            offset = self._last_order_image_offset + 1
        else:
            offset = 0
        self._last_order_image_offset = offset
        self._config_helper.add_config_key(
            self._config_section_background,
            self._config_key_last_order_image_offset,
            self._last_order_image_offset
        )
        if self.isHidden():
            self.lineEdit_order_offset.setText(str(offset))
        return offset

    def _update_level_action(self, index, level):
        """
        更新当前显示器壁纸等级状态
        :param index: 显示器索引
        :param level: 等级 id
        :return:
        """
        level_actions = self._monitor_settings[index].image_level_actions
        for i in range(len(self._levels)):
            level = self._levels[i]
            level_actions[i].setChecked(level.id == level)

    def _on_tray_click(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.Trigger:
            self.show()
            return

    def _open_file_in_directory_and_copy_file_name(self, index):
        image = self._monitor_settings[index].image
        file_path = image.full_path().replace('/', '\\')
        ex = f"explorer /select,{file_path}"
        os.system(ex)
        pyperclip.copy(image.filename)

    def _set_level(self, index, level):
        image = self._monitor_settings[index].image
        image.level = level
        self._db_helper.update_image(image)
        self._update_level_action(index, level)
