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
import os
import time


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
