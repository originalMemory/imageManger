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

from PyQt5.QtCore import QModelIndex, QVariant, Qt, QAbstractListModel
from PyQt5.QtGui import QBrush, QColor

from helper import db_helper
from helper.file_helper import FileHelper
from model.my_list_model import MyBaseListModel


class ImageFileListModel(MyBaseListModel):

    def __init__(self):
        super().__init__()
        self._base_dir = ""
        self._image_extension_list = ['.jpg', 'jpeg', '.bmp', '.png', 'gif', 'dib', 'pcp', 'dif', 'wmf', 'tif', 'eps',
                                      'psd', 'cdr', 'iff', 'tga', 'pcd', 'mpi', '.icon', '.ico']

    def data(self, index: QModelIndex, role: int = ...):
        if index.isValid() or (0 <= index.row() < len(self._data_list)):
            if role == Qt.DisplayRole:
                return QVariant(self._data_list[index.row()]['relative_path'])
            elif role == Qt.StatusTipRole:
                return QVariant(self._data_list[index.row()]['full_path'])
            elif role == Qt.BackgroundColorRole:
                if self._data_list[index.row()]["id"] != 0:
                    return QBrush(QColor(84, 255, 159))
                else:
                    return QBrush(QColor(255, 255, 255))
        else:
            return QVariant()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self._data_list)

    def add_dir(self, dir_path):
        self._base_dir = os.path.basename(dir_path)
        for filename in os.listdir(dir_path):
            file_path = "%s/%s" % (dir_path, filename)
            if os.path.isdir(file_path):
                self.add_children_dir(file_path)
                continue
            relative_path = "%s/%s" % (self._base_dir, filename)
            self.add_image_data(relative_path, file_path, filename)

    def add_children_dir(self, dir_path):
        for filename in os.listdir(dir_path):
            file_path = "%s/%s" % (dir_path, filename)
            dir_name = os.path.basename(dir_path)
            if os.path.isdir(file_path):
                self.add_children_dir(file_path)
                continue
            relative_path = "%s/%s/%s" % (self._base_dir, dir_name, filename)
            self.add_image_data(relative_path, file_path, filename)

    def add_image_data(self, relative_path, full_path, filename):
        if not self.is_image(filename):
            return
        image_id = db_helper.get_id_by_path(full_path)
        item_data = {
            "id": image_id,
            "relative_path": relative_path,
            "full_path": full_path,
            'name': filename
        }
        self.add_item(item_data)

    def set_image_id(self, index, image_id):
        self._data_list[index]['id'] = image_id

    def is_image(self, filename):
        extension = FileHelper.get_file_extension(filename).lower()
        return extension in self._image_extension_list
