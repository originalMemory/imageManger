#!/user/bin/env python
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : config_helper
@author  : wuhoubo
@desc    : config 帮助类
@create  : 2019/12/15 16:25:25
@update  :
"""
import os
from configparser import ConfigParser

from PyQt5.QtWidgets import QMessageBox


class ConfigHelper:

    __config_filename = "config.ini"

    def __init__(self, context):
        self.context = context

    def __get_config(self) -> ConfigParser:
        """
        获取 config 配置
        :return: 可空 ConfigParser 对象
        """
        config = ConfigParser()
        if os.path.exists(self.__config_filename):
            try:
                config.read(self.__config_filename, encoding='utf-8')
                return config
            except Exception as e:
                QMessageBox.information(self.context, "提示", str(e), QMessageBox.Ok)
        else:
            QMessageBox.information(self.context, "提示", "配置文件不存在", QMessageBox.Ok)

    def add_config_key(self, section, key, value):
        """
        添加配置参数
        :param section:
        :param key:
        :param value:
        :return:
        """
        config = self.__get_config()
        if not config:
            return
        if not config.has_section(section):
            config.add_section(section)
        value = str(value)
        value = value.replace('%', '%%')
        config[section][key] = value
        with open(self.__config_filename, 'w', encoding='utf-8') as f:
            config.write(f)

    def get_config_key(self, section, key, default_value=""):
        """
        获取配置参数
        :param section:
        :param key:
        :param default_value: 默认值
        :return: 配置参数的值（字符串）
        """
        config = self.__get_config()
        if not config:
            return default_value
        if config.has_section(section) and config.has_option(section, key):
            value = config.get(section, key)
            value = value.replace('%%', '%')
            return value
        else:
            return default_value
