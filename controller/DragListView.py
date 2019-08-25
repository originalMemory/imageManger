#!/user/bin/env python
# coding=utf-8
"""
@project : PictureManager
@ide     : PyCharm
@file    : DragListView
@author  : wuhoubo
@desc    : 
@create  : 2019/5/26 16:36:11
@update  :
"""
from PyQt5.QtWidgets import QListView, QMenu, QAction
from qtpy import QtGui

from Model.ImageFileListModel import ImageFileListModel


class DragListView(QListView):
    map_listView = []

    def __int__(self):
        super().__init__()
        self.m_pModel = ImageFileListModel()
        self.setModel(self.m_pModel)

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent):
        hitIndex = self.indexAt(event.pos()).column()
        if hitIndex > -1:
            pmenu = QMenu(self)
            pDeleteAct = QAction("删除", pmenu)
            pmenu.addAction(pDeleteAct)
            pDeleteAct.triggered.connect(self.deleteItemSlot)

    def deleteItemSlot(self):
        index = self.currentIndex().row()
        if index > -1:
            self.m_pModel.deleteItem(index)

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:
        path = e.mimeData().text()
        print(path)