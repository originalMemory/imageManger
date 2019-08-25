#!/user/bin/env python
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : main
@author  : wuhoubo
@desc    : 
@create  : 2019/6/2 23:57:26
@update  :
"""
import os
from enum import unique, Enum

from PyQt5.QtCore import QModelIndex
from PyQt5.QtWidgets import QMainWindow
from qtpy import QtWidgets, QtGui

import db_helper
from model.ImageFileListModel import ImageFileListModel
from model.my_list_model import MyBaseListModel

from view.main import Ui_Main


@unique
class VIEW(Enum):
    LIST = 1
    GRAPHIC = 2


class MyMain(QMainWindow, Ui_Main):
    def __init__(self, parent=None):
        super(MyMain, self).__init__(parent)
        self.setupUi(self)

        self.actionOpen.triggered.connect(self.open_files)
        # self.listView.clicked.connect(self.show_image_by_index)

        # 下拉列表设置
        self._typeModel = MyBaseListModel()
        self.comboBox_type.setModel(self._typeModel)
        self._typeModel.add_items(db_helper.get_model_data_list('type'))
        self.comboBox_type.setCurrentIndex(0)

        self._level_model = MyBaseListModel()
        self.comboBox_level.setModel(self._level_model)
        self._level_model.add_items(db_helper.get_model_data_list('level'))
        self.comboBox_level.setCurrentIndex(0)

        # 图片信息
        self._image_model = ImageFileListModel()  # 图片信息
        self._default_dir = 'D:/图片/[wlop (Wang Ling)] Artwork 2017 集合'
        for f in os.listdir(self._default_dir):
            file_path = "%s/%s" % (self._default_dir, f)
            if not os.path.isdir(file_path):
                tp_list = file_path.split('/')
                item_data = {
                    "name": "%s/%s" % (tp_list[-2], tp_list[-1]),
                    "path": file_path,
                    'simpleName': tp_list[-1]
                }
                self._image_model.addItem(item_data)
        self.listView.setModel(self._image_model)

        self.listView.selectionModel().currentChanged.connect(self.on_change)
        self.graphicsView.setFocus()

    def open_files(self):
        """
        打开图片文件
        :return:
        """
        path_list = \
            QtWidgets.QFileDialog.getOpenFileNames(self, "选择文件", "D:\\图片\\[wlop (Wang Ling)] Artwork 2017 集合",
                                                   '图片(*.jpg *.png *.gif *.jpeg *.bmp)')[0]
        # 生成List使用的Model
        for path in path_list:
            tp_lists = path.split('/')
            item_data = {
                "name": "%s/%s" % (tp_lists[-2], tp_lists[-1]),
                "path": path
            }
            self._image_model.addItem(item_data)

    def show_image(self, index: int):
        """
        显示指定索引文件名对应的图片
        :param index: 文件索引
        :return:
        """
        path = self._image_model.getItem(index)['path']
        self.statusbar.showMessage(path)
        print(path)
        pixmap = QtGui.QPixmap(path)
        # 填充缩放
        x_scale = self.graphicsView.width() / float(pixmap.width())
        y_scale = self.graphicsView.height() / float(pixmap.height())
        if x_scale < y_scale:
            pixmap = pixmap.scaledToWidth(self.graphicsView.width())
        else:
            pixmap = pixmap.scaledToHeight(self.graphicsView.height())
        # 加载图片
        item = QtWidgets.QGraphicsPixmapItem(pixmap)
        scene = QtWidgets.QGraphicsScene()
        scene.addItem(item)
        self.graphicsView.setScene(scene)

    def on_change(self, current: QModelIndex, previous: QModelIndex):
        """
        图片列表焦点变化事件
        :param current:
        :param previous:
        :return:
        """
        self.show_image(current.row())

    def classify(self):
        """
        分类图片
        :return:
        """
        select_rows = self.listView.selectionModel().selectedRows()
        index = self.comboBox_type.currentIndex()
        type_id = self._typeModel.get_item(index)
        index = self.comboBox_level.currentIndex()
        level_id = self._level_model.get_item(index)
        # for index in select_rows:
            
        pass
