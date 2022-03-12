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

from PyQt6.QtCore import QModelIndex, QVariant, Qt
from PyQt6.QtGui import QBrush, QColor

from helper.db_helper import DBHelper
from helper.file_helper import FileHelper
from helper.image_helper import ImageHelper
from model.data import ImageFile, MyImage
from model.my_list_model import MyBaseListModel


class ImageFileListModel(MyBaseListModel):

    delete_repeat = False

    def __init__(self, context):
        super().__init__()
        self._base_dir = ""
        self.__image_extension_list = ['.jpg', '.jpeg', '.bmp', '.png', 'gif', '.dib', '.pcp', '.dif', '.wmf', '.tif',
                                       '.eps', '.psd', '.cdr', '.iff', '.tga', '.pcd', '.mpi', '.icon', '.ico']
        self._data_list_in_database = []
        self.__db_helper = DBHelper(context)

    def data(self, index: QModelIndex, role: int = ...):
        if index.isValid() or (0 <= index.row() < len(self._data_list)):
            if role == Qt.ItemDataRole.DisplayRole:
                return QVariant(self._data_list[index.row()].name)
            elif role == Qt.ItemDataRole.StatusTipRole:
                return QVariant(self._data_list[index.row()].full_path)
            elif role == Qt.ItemDataRole.BackgroundRole:
                if self._data_list[index.row()].id != 0:
                    return QBrush(QColor(84, 255, 159))
                else:
                    return QBrush(QColor(255, 255, 255))
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
        self._base_dir = os.path.basename(dir_path)
        for filename in os.listdir(dir_path):
            file_path = "%s/%s" % (dir_path, filename)
            if os.path.isdir(file_path):
                self.__add_children_dir(file_path)
                continue
            relative_path = "%s/%s" % (self._base_dir, filename)
            self.__add_image_data(relative_path, file_path, filename)

    def __add_children_dir(self, dir_path):
        for filename in os.listdir(dir_path):
            file_path = "%s/%s" % (dir_path, filename)
            dir_name = os.path.basename(dir_path)
            if os.path.isdir(file_path):
                self.__add_children_dir(file_path)
                continue
            relative_path = "%s/%s/%s" % (self._base_dir, dir_name, filename)
            self.__add_image_data(relative_path, file_path, filename)

    def __add_image_data(self, show_path, full_path, filename):
        if not self.__is_image(filename):
            return
        image = self.__db_helper.search_by_file_path(full_path)
        if not image:
            # 根据md5再做1次判断
            md5 = FileHelper.get_md5(full_path)
            image = self.__db_helper.search_by_md5(md5)
            if image and image.path != full_path:
                # 当前是 pixiv ，数据库是 yande 时更新为 pixiv 的信息
                if image.source == 'yande' and ImageHelper.get_pixiv_no(full_path):
                    info = ImageHelper.analyze_image_info(full_path)
                    image.source = 'pixiv'
                    image.desc = info.desc
                    image.tags = info.tags
                    image.author = info.author
                    image.uploader = ''
                    image.sequence = info.sequence
                    image.file_create_time = FileHelper.get_create_time_str(full_path)
                    yande_path = image.path
                    sub_str = f'_{info.tags}'
                    source_pixiv_path = full_path
                    full_path = full_path.replace(sub_str, '')
                    show_path = show_path.replace(sub_str, '')
                    new_path = full_path.replace(FileHelper.get_path_prefix(), '')
                    image.relative_path = new_path
                    image.path = full_path
                    self.__db_helper.update_image(image)
                    os.rename(source_pixiv_path, full_path)
                    os.remove(yande_path)
                    print(f'pixiv 替换 yande\nyande: {yande_path}, pixiv: {full_path}')
                else:
                    # 已有图片存在且删除重复时删除当前图片
                    if os.path.exists(image.path) and self.delete_repeat:
                        print(f'删除重复图片: {full_path}, 原图地址：{image.path}')
                        os.remove(full_path)
                        return
                    image.path = full_path
                    new_path = full_path.replace(FileHelper.get_path_prefix(), '')
                    image.relative_path = new_path
                    self.__db_helper.update_path(image.id, new_path)

        if image:
            image_id = image.id
            self._data_list_in_database.append(image)
        else:
            image_id = 0
        item_data = ImageFile(image_id, show_path, full_path)
        self.add_item(item_data)

    def add_path(self, path):
        if os.path.isdir(path):
            self.__add_dir(path)
        elif os.path.isfile(path):
            self.__add_file(path)

    def __add_file(self, file_path):
        filename = os.path.basename(file_path)
        if not self.__is_image(filename):
            return
        relative_path = filename
        self.__add_image_data(relative_path, file_path, filename)

    def set_image_id(self, index, image_id):
        self._data_list[index.row()].id = image_id
        self.dataChanged(index, index, [Qt.ItemDataRole.BackgroundRole])

    def __is_image(self, filename):
        extension = FileHelper.get_file_extension(filename).lower()
        return extension in self.__image_extension_list

    def clear(self):
        super().clear()
        self._data_list_in_database.clear()

    def get_database_item(self, image_id) -> MyImage:
        for image in self._data_list_in_database:
            if image.id == image_id:
                return image
        return None

    def set_images(self, image_sql_list, image_file_list):
        self.beginResetModel()
        self._data_list_in_database = image_sql_list
        self._data_list = image_file_list
        self.endResetModel()
