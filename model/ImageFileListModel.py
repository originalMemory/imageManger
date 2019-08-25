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

from PyQt5.QtCore import QAbstractListModel, QModelIndex, QVariant, Qt


class ImageFileListModel(QAbstractListModel):
    def __init__(self):
        super().__init__()
        self.ListItemData = []

    def data(self, index: QModelIndex, role: int = ...):
        if index.isValid() or (0 <= index.row() < len(self.ListItemData)):
            if role == Qt.DisplayRole:
                return QVariant(self.ListItemData[index.row()]['name'])
            elif role == Qt.StatusTipRole:
                return QVariant(self.ListItemData[index.row()]['path'])
            elif role == Qt.ToolTipRole:
                return QVariant(self.ListItemData[index.row()]['path'])
        else:
            return QVariant()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self.ListItemData)

    def addItem(self, itemData):
        if itemData:
            self.beginInsertRows(QModelIndex(), len(self.ListItemData), len(self.ListItemData) + 1)
            self.ListItemData.append(itemData)
            self.endInsertRows()

    def deleteItem(self, index):
        del self.ListItemData[index]

    def getItem(self, index):
        if -1 < index < len(self.ListItemData):
            return self.ListItemData[index]
