#!/user/bin/env python
# coding=utf-8
"""
@project : DeviceManager
@ide     : PyCharm
@file    : my_list_model
@author  : wuhoubo
@desc    : 自定义列表类，用于在列表展示数据
@create  : 2019/6/5 22:23:20
@update  :
"""

from PyQt5.QtCore import QAbstractListModel, QModelIndex, QVariant, Qt

from model.data import BaseData


class MyBaseListModel(QAbstractListModel):
    """
    Model类，用于listView展示
    """

    def __init__(self):
        super().__init__()
        self._data_list = []  # 数据list，保存所有数据

    def data(self, index: QModelIndex, role: int = ...):
        """
        继承父类，必须有。设置不同类型调用返回数据
        :param index: 索引
        :param role: 要获取的数据类型
        :return:
        """
        # 设置表格显示使用的数据
        if index.isValid() or (0 <= index.row() < len(self._data_list)):
            if role == Qt.DisplayRole:
                return QVariant(self._data_list[index.row()].name)
        else:
            return QVariant()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        """
        继承父类，必须有。返回数据总行数
        :param parent:
        :return:
        """
        return len(self._data_list)

    def add_item(self, item_data):
        """
        自定义。添加单个数据
        :param item_data: 数据
        :return:
        """
        if item_data:
            self.beginInsertRows(QModelIndex(), len(self._data_list), len(self._data_list) + 1)
            self._data_list.append(item_data)
            self.endInsertRows()

    def add_items(self, item_data_list):
        """
        自定义。添加多个数据
        :param item_data_list: 数据列表
        :return:
        """
        if item_data_list:
            self.beginInsertRows(QModelIndex(), len(self._data_list), len(self._data_list) + len(item_data_list))
            self._data_list.extend(item_data_list)
            self.endInsertRows()

    def delete_item(self, row):
        """
        自定义。删除数据
        :param row: 索引
        :return:
        """
        self.beginRemoveRows(QModelIndex(), row, row - 1)
        del self._data_list[row]
        self.endRemoveRows()

    def update_item(self, index, new_item):
        """
        自定义。更新数据
        :param index: 索引
        :param new_item:
        :return:
        """
        self._data_list[index.row()] = new_item
        self.dataChanged(index, index, Qt.BackgroundRole)

    def get_item(self, row) -> BaseData:
        """
        自定义。获取数据
        :param row: 索引
        :return:
        """
        if -1 < row < len(self._data_list):
            return self._data_list[row]

    def get_index(self, key):
        """
        自定义。获取数据的的字段值获取对应索引
        :param key: 数据的字段值，有id和name两种，分别为数字和字符串类型
        :return:
        """
        # 如果是数字类型，则以id进行对比
        if isinstance(key, int):
            for i in range(len(self._data_list)):
                if key == self._data_list[i].id:
                    return i
        elif isinstance(key, str):
            for i in range(len(self._data_list)):
                if key == self._data_list[i].name:
                    return i
        return 0

    def get_id(self, index):
        """
        自定义。根据索引获取对应数据的id
        :param index: 索引
        :return:
        """
        if -1 < index < len(self._data_list):
            return self._data_list[index].id
        return 0

    def clear(self):
        """
        清空数据
        :return:
        """
        self.beginResetModel()
        self._data_list.clear()
        self.endResetModel()
