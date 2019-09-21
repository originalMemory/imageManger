#!/user/bin/env python
# coding=utf-8
"""
@project : PictureManager
@ide     : PyCharm
@file    : ImageFileListModel
@author  : wuhoubo
@desc    : 
@create  : 2019/5/26 15:25:32
@update  :
"""
import os

from PyQt5.QtCore import QModelIndex, QVariant, Qt

from helper.file_helper import FileHelper
from model.my_list_model import MyBaseListModel


class ImageFileListModel(MyBaseListModel):

    def __init__(self):
        super().__init__()
        self._base_dir = ""
        self._image_extension_list = ['.jpg', 'jpeg', '.bmp', '.png', 'gif', 'dib', 'pcp', 'dif', 'wmf', 'tif', 'eps',
                                      'psd', 'cdr', 'iff', 'tga', 'pcd', 'mpi']

    def data(self, index: QModelIndex, role: int = ...):
        if index.isValid() or (0 <= index.row() < len(self._data_list)):
            if role == Qt.DisplayRole:
                return QVariant(self._data_list[index.row()]['name'])
            elif role == Qt.StatusTipRole:
                return QVariant(self._data_list[index.row()]['path'])
        return QVariant()

    def add_dir(self, dir_path):
        self._base_dir = os.path.basename(dir_path)
        print(self._base_dir)
        for filename in os.listdir(dir_path):
            file_path = "%s/%s" % (dir_path, filename)
            if os.path.isdir(file_path):
                self.add_children_dir(file_path)
                continue
            if not self.is_image(filename):
                continue
            item_data = {
                "name": "%s/%s" % (self._base_dir, filename),
                "path": file_path,
                'simpleName': filename
            }
            self._data_list.append(item_data)

    def add_children_dir(self, dir_path):
        for filename in os.listdir(dir_path):
            file_path = "%s/%s" % (dir_path, filename)
            dir_name = os.path.basename(dir_path)
            if os.path.isdir(file_path):
                self.add_children_dir(file_path)
                continue
            if not self.is_image(filename):
                continue
            item_data = {
                "name": "%s/%s/%s" % (self._base_dir, dir_name, filename),
                "path": file_path,
                'simpleName': filename
            }
            self._data_list.append(item_data)

    def is_image(self, filename):
        extension = FileHelper.get_file_extension(filename)
        b_image = extension in self._image_extension_list
        return extension in self._image_extension_list
