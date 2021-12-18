#!/user/bin/env python
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : file_helper
@author  : wuhoubo
@desc    : 文件处理
@create  : 2019/9/21 11:09:26
@update  :
"""
import datetime
import hashlib
import os
import re
import time

from shutil import copyfile

from PyQt6 import QtGui

from helper.config_helper import ConfigHelper


class FileHelper:

    @staticmethod
    def get_file_extension(file_path):
        return os.path.splitext(file_path)[-1]

    @staticmethod
    def time_stamp_to_time(timestamp):
        """
        把时间戳转化为时间
        :param timestamp: 时间戳 1479264792
        :return: 时间字符串 2016-11-16 10:53:12
        """
        stamp = time.localtime(timestamp)
        return time.strftime('%Y-%m-%d %H:%M:%S', stamp)

    @staticmethod
    def get_file_size_in_mb(file_path):
        """
        获取文件的大小,结果保留两位小数，单位为MB
        :param file_path: 文件路径
        :return:
        """
        if not os.path.exists(file_path):
            return 0
        size = os.path.getsize(file_path)
        size = size / float(1024 * 1024)
        return round(size, 2)

    @staticmethod
    def get_create_time_str(file_path):
        """
        获取文件创建时间字符串
        :param file_path: 文件路径
        :return:
        """
        t = os.path.getmtime(file_path)
        return FileHelper.time_stamp_to_time(t)

    @staticmethod
    def get_create_time(file_path):
        """
        获取文件创建时间
        :param file_path: 文件路径
        :return:
        """
        t = os.path.getmtime(file_path)
        return FileHelper.become_datetime(t)

    @staticmethod
    def become_datetime(dt):
        """
        将时间类型转换成datetime类型
        :param dt: 时间，可能为 datetime 或 str
        :return:
        """
        if isinstance(dt, datetime.datetime):
            return dt

        elif isinstance(dt, str):
            if dt.split(" ")[1:]:
                a_datetime = datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
            else:
                a_datetime = datetime.datetime.strptime(dt, "%Y-%m-%d")
            return a_datetime

        elif isinstance(dt, float):
            # 把时间戳转换成datetime类型
            a_datetime = datetime.datetime.fromtimestamp(dt)
            return a_datetime

    @staticmethod
    def open_file_directory(file_path):
        """
        打开文件所在目录并选中文件
        :param file_path: 文件路径
        :return:
        """
        file_path = file_path.replace('/', '\\')
        ex = f"explorer /select,{file_path}"
        os.system(ex)

    @staticmethod
    def copyfile_without_override(origin_file_path, dir_path, new_filename):
        filename = os.path.basename(origin_file_path)
        (shot_name, extension) = os.path.splitext(filename)
        if new_filename:
            filename = f"{new_filename}{extension}"
        target_file_path = os.path.join(dir_path, filename)
        no = 1
        while True:
            if not os.path.exists(target_file_path):
                break
            if new_filename:
                name = new_filename
            else:
                name = shot_name
            filename = f"{name}_{no}{extension}"
            target_file_path = os.path.join(dir_path, filename)
            no += 1

        copyfile(origin_file_path, os.path.join(dir_path, filename))

    @staticmethod
    def get_md5(file_path):
        f = open(file_path, 'rb')
        md5_obj = hashlib.md5()
        while True:
            d = f.read(8096)
            if not d:
                break
            md5_obj.update(d)
        hash_code = md5_obj.hexdigest()
        f.close()
        # md5 = str(hash_code).lower()
        return hash_code

    @staticmethod
    def get_full_path(relative_path):
        prefix = FileHelper.get_path_prefix()
        if not prefix or os.path.exists(relative_path):
            return relative_path
        else:
            return os.path.join(prefix, relative_path)

    @staticmethod
    def get_path_prefix():
        return ConfigHelper(None).get_config_key('common', 'pathPrefix')
