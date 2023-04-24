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
import re

from PyQt6.QtCore import QModelIndex, QVariant, Qt
from PyQt6.QtGui import QBrush, QColor

from helper.db_helper import DBHelper
from helper.file_helper import FileHelper
from helper.image_helper import ImageHelper
from model.data import ImageFile, MyImage, TagSource
from model.my_list_model import MyBaseListModel


def _get_int_key(item):
    name = os.path.splitext(item)[0]
    match = re.search(r'(?P<no>\d+?)[)_]?$', name)
    if match:
        return int(match.group('no'))


class ImageFileListModel(MyBaseListModel):
    delete_repeat = False

    def __init__(self, context):
        super().__init__()
        self._data_list_in_database = []
        self.__db_helper = DBHelper(context)

    def data(self, index: QModelIndex, role: int = ...):
        if index.isValid() or (0 <= index.row() < len(self._data_list)):
            if role == Qt.ItemDataRole.DisplayRole:
                return QVariant(self._data_list[index.row()].name)
            elif role == Qt.ItemDataRole.StatusTipRole:
                return QVariant(self._data_list[index.row()].full_path)
            elif role == Qt.ItemDataRole.BackgroundRole:
                if self._data_list[index.row()].id:
                    return QBrush(QColor(84, 255, 159))
                else:
                    return QBrush(QColor(255, 255, 255, 0))
        else:
            return QVariant()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self._data_list)

    def get_item(self, row) -> ImageFile:
        """
                自定义。获取数据
                :param row: 索引
                :return:
                """
        if -1 < row < len(self._data_list):
            return self._data_list[row]

    def __add_dir(self, dir_path):
        paths = []
        for root, ds, fs in os.walk(dir_path):
            tp_paths = []
            all_int = True
            for name in fs:
                if not ImageHelper.is_image(name) or '$RECYCLE' in name:
                    continue
                if all_int and not _get_int_key(name):
                    all_int = False
                tp_paths.append(f'{root}/{name}'.replace('\\', '/'))
            if all_int:
                tp_paths.sort(key=_get_int_key)
            else:
                tp_paths.sort()
            paths += tp_paths
        if not len(paths):
            return
        for path in paths:
            filename = os.path.basename(path)
            self.__add_image_data(dir_path, path, filename)

    def __add_image_data(self, dir_path, full_path, filename):
        if not ImageHelper.is_image(filename):
            return
        image = self._check_exist_image(full_path)
        if image:
            image_id = image.id()
            self._data_list_in_database.append(image)
            full_path = image.full_path()
        else:
            image_id = None
        if not os.path.exists(full_path):
            return
        show_path = full_path.replace(dir_path, '')
        if show_path.startswith('/'):
            show_path = show_path[1:]
        item_data = ImageFile(image_id, show_path, full_path)
        self.add_item(item_data)

    def _check_exist_image(self, full_path):
        image = self.__db_helper.search_by_file_path(full_path)
        if image:
            return image
        if not image:
            # 根据md5再做1次判断
            md5 = FileHelper.get_md5(full_path)
            image = self.__db_helper.search_by_md5(md5)
        if not image:
            return
        exist_full_path = image.full_path().replace('\\', '/')
        if exist_full_path == full_path:
            return image
        old_path = exist_full_path
        info = ImageHelper.analyze_image_info(full_path)
        if image.type != 1 or not info.source or image.source == info.source or not os.path.exists(exist_full_path):
            # 已有图片存在且删除重复时删除当前图片
            if os.path.exists(exist_full_path) and self.delete_repeat:
                print(f'删除重复图片: {full_path}, 原图地址：{old_path}')
                FileHelper.del_file(full_path)
                return
            if os.path.exists(exist_full_path):
                FileHelper.del_file(exist_full_path)
                print(f'删除已存在图片：{exist_full_path}')
            new_path = FileHelper.get_relative_path(full_path)
            image.path = new_path
            print(f'新路径：{new_path}，原地址：{old_path}')
            self.__db_helper.update_path(image.id(), new_path)
            return image
        for tag_name in info.tags:
            tag = self.__db_helper.find_or_create_tag(tag_name, TagSource(info.source))
            if tag.children:
                image.tags += tag.children
            else:
                image.tags.append(tag.id())
        image.tags = list(set(image.tags))
        image.file_create_time = FileHelper.get_create_time(full_path)
        remove_tags_filepath = ImageHelper.remove_tags(full_path)
        print(f'合并文件。增加标签：{info.tags}。新地址：{remove_tags_filepath}, 原地址：{exist_full_path}')
        if info.source != 'pixiv':
            os.remove(full_path)
            self.__db_helper.update_image(image)
        else:
            # 当前是 pixiv ，更新为 pixiv 的信息
            image.source = 'pixiv'
            image.desc = info.desc
            image.authors = info.authors
            image.uploader = ''
            image.sequence = info.sequence
            os.rename(full_path, remove_tags_filepath)
            os.remove(exist_full_path)
            image.path = FileHelper.get_relative_path(remove_tags_filepath)
            self.__db_helper.update_image(image)
            return image

    def add_path(self, path):
        if os.path.isdir(path):
            self.__add_dir(path)
        elif os.path.isfile(path):
            self.__add_file(path)

    def __add_file(self, file_path):
        filename = os.path.basename(file_path)
        self.__add_image_data(os.path.dirname(file_path), file_path, filename)

    def set_image_id(self, index, image_id):
        self._data_list[index.row()].id = image_id
        self.dataChanged(index, index, [Qt.ItemDataRole.BackgroundRole])

    def clear(self):
        super().clear()
        self._data_list_in_database.clear()

    def get_database_item(self, image_id) -> MyImage:
        for image in self._data_list_in_database:
            if image.id() == image_id:
                return image
        return None

    def set_images(self, image_sql_list, image_file_list):
        self.beginResetModel()
        self._data_list_in_database = image_sql_list
        self._data_list = image_file_list
        self.endResetModel()
