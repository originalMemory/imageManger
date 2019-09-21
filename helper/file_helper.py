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
import os


class FileHelper:

    @staticmethod
    def get_file_extension(file_path):
        return os.path.splitext(file_path)[-1]