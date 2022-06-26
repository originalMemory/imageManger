#!/user/bin/env python3
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : tag_analyse.py
@author  : illusion
@desc    :
@create  : 2022-06-25 15:45:42
"""
import json
import threading
import time
import webbrowser

from PyQt6 import QtWidgets, QtGui
from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QHeaderView
from win32comext.shell import shell, shellcon

from helper.config_helper import ConfigHelper
from helper.db_helper import DBHelper
from helper.file_helper import FileHelper
from helper.image_helper import ImageHelper
from helper.tag_helper import TagHelper
from manager.view.tag_analyse import Ui_Manager
from model.ImageFileListModel import ImageFileListModel
from model.data import PreloadImage


class TagAnalyse(QMainWindow, Ui_Manager):
    def __init__(self, parent=None):
        super(TagAnalyse, self).__init__(parent)
        self.setupUi(self)

        self._config = ConfigHelper(self)
        self._db_helper = DBHelper(self._error_toast)  # 数据库操作
        self._tag_helper = TagHelper()
        self._tag_headers = ['确认', '数量', '原名', '翻译名', '类型', '额外信息']
        self._tag_model = QStandardItemModel()
        self._image_model = ImageFileListModel(self)

        self.listView.setModel(self._image_model)
        self.tableView.setModel(self._tag_model)

        self.lineEdit_minCount.setText(self._config.get_config_key('history', 'tagMinCount', '3'))
        self.textEdit_search.setText(self._config.get_config_key('history', 'tagSearch'))

        # 关联事件
        self.tableView.selectionModel().currentRowChanged.connect(self._on_table_view_current_row_change)
        self.listView.selectionModel().currentChanged.connect(self.__on_list_view_current_row_change)
        self.listView.set_action_show_file_directory_delegate(self.open_file_directory)
        self.listView.set_key_press_delegate(self.key_press_delegate)
        self.pushButton_seach.clicked.connect(self._search_tags)
        self.pushButton_save.clicked.connect(self._save)
        self.pushButton_jump.clicked.connect(self._jum_pixiv)

        rect_info = self._config.get_config_key('history', 'tagRect')
        rect = rect_info.split(',')
        if len(rect) == 4:
            left, top, width, height = int(rect[0]), int(rect[1]) - 32, int(rect[2]), int(rect[3])
            self.move(left, top)
            self.resize(width, height)
        else:
            self._config.add_config_key('history', 'tagRect', '')

        threading.Thread(target=self.__preload, daemon=True).start()

    def _search_tags(self):
        text = self.textEdit_search.toPlainText()
        if not text:
            self._error_toast('搜索条件不能为空')
            return
        min_count = self.lineEdit_minCount.text()
        if not min_count.isdigit():
            self._error_toast('标签数下限必须为数字')
        min_count = int(min_count)
        try:
            fl = json.loads(text)
        except Exception as e:
            self._error_toast(e)
            return
        self._config.add_config_key('history', 'tagSearch', text)
        self._config.add_config_key('history', 'tagMinCount', min_count)
        self._tag_model.clear()
        self._tag_model.setHorizontalHeaderLabels(self._tag_headers)
        self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tableView.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tableView.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tableView.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.tableView.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.tableView.setColumnWidth(4, 120)
        self.tableView.setColumnWidth(5, 70)
        self.tableView.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        lines = self._tag_helper.get_not_tran_tags(fl, min_count)
        for line in lines:
            check = QStandardItem()
            check.setCheckable(True)
            row = [check] + list(map(lambda x: QStandardItem(str(x)), line))
            self._tag_model.appendRow(row)
        threading.Thread(target=self._load_authors, daemon=True).start()

    def _load_authors(self):
        count = 0
        for i in range(self._tag_model.rowCount()):
            trans = self._tag_model.item(i, 3).text()
            if trans:
                continue
            count += 1
            if count >= 50:
                break
            print(f'[{i}/{self._tag_model.rowCount()}] - 开始获取用户信息')
            no, name = self._tag_helper.get_yande_author_info(self._tag_model.item(i, 2).text())
            if not no:
                continue
            print(f'[{i}/{self._tag_model.rowCount()}] - 获取用户名成功：{name}, {no}')
            self._tag_model.setItem(i, 3, QStandardItem(name))
            self._tag_model.setItem(i, 4, QStandardItem('author'))
            self._tag_model.setItem(i, 5, QStandardItem(no))
        print('获取用户结束')

    def _save(self):
        rows = []
        for i in range(self._tag_model.rowCount()):
            if self._tag_model.item(i, 0).checkState() != Qt.CheckState.Checked:
                continue
            source = self._tag_model.item(i, 2).text()
            dests = self._tag_model.item(i, 3).text().split(';')
            types = self._tag_model.item(i, 4).text().split(';')
            extra = self._tag_model.item(i, 5).text()
            self._tag_helper.record_tran_tag(source, dests, types, extra)
            self._tag_helper.analysis_tags({'tags': source})
            rows.append(i)
        rows.sort(reverse=True)
        for row in rows:
            self._tag_model.removeRow(row)
        self._cache.clear()
        if self._tag_model.rowCount():
            self.tableView.setCurrentIndex(self._tag_model.index(0, 2))
            threading.Thread(target=self._load_authors, daemon=True).start()

    def _jum_pixiv(self):
        index = self.tableView.selectionModel().currentIndex()
        if index.row() < 0:
            return
        no = self._tag_model.item(index.row(), 5).text()
        if not no:
            return
        url = f'https://www.pixiv.net/users/{no}/artworks'
        webbrowser.open(url, new=0, autoraise=True)

    def _on_table_view_current_row_change(self, current: QModelIndex, previous: QModelIndex):
        if current.row() == previous.row():
            return
        if previous.row() >= 0:
            checked = self._tag_model.item(previous.row(), 0)
            checked.setCheckState(Qt.CheckState.Checked)
        threading.Thread(target=self._load_img, daemon=True).start()

    def _load_img(self):
        tag = self._tag_model.item(self.tableView.selectionModel().currentIndex().row(), 2).text()
        image_sql_list, image_file_list = self._db_helper.search_by_filter({'tags': tag})
        if len(image_sql_list) > 0:
            self._image_model.set_images(image_sql_list, image_file_list)
            self._cache.clear()
            self.listView.setCurrentIndex(self._image_model.index(0, 0))

    def open_file_directory(self):
        """
        打开文件所在目录并选中文件
        :return:
        """
        select_rows = self.listView.selectionModel().selectedRows()
        if not len(select_rows):
            return
        file_path = self._image_model.get_item(select_rows[0].row()).full_path
        FileHelper.open_file_directory(file_path)

    def key_press_delegate(self, event: QtGui.QKeyEvent):
        if event.key() == Qt.Key.Key_D:
            self._del_select_list_rows()
            return True
        if event.key() == Qt.Key.Key_W:
            current_index = self.listView.currentIndex()
            if current_index.row() > 0:
                self.listView.setCurrentIndex(self._image_model.index(current_index.row() - 1, current_index.column()))
            return True
        if event.key() == Qt.Key.Key_S:
            current_index = self.listView.currentIndex()
            if current_index.row() < self._image_model.rowCount() - 1:
                self.listView.setCurrentIndex(self._image_model.index(current_index.row() + 1, current_index.column()))
            return True
        return False

    def _del_select_list_rows(self):
        """
        删除选中行
        :return:
        """
        select_rows = self.listView.selectionModel().selectedRows()
        if len(select_rows) == 0:
            return
        first_index = select_rows[0]
        item = self._image_model.get_item(first_index)
        if item.id:
            self._db_helper.delete(item.id)
        shell.SHFileOperation((0, shellcon.FO_DELETE, item.full_path, None,
                               shellcon.FOF_SILENT | shellcon.FOF_ALLOWUNDO | shellcon.FOF_NOCONFIRMATION, None,
                               None))  # 删除文件到回收站
        self._image_model.delete_item(first_index)
        self.statusbar.showMessage(f"{item.name} 删除成功！")

        self._cache.clear()
        row = first_index.row()
        # 如果删除到了最后一行，则刷新上一个
        if first_index.row() >= self._image_model.rowCount():
            row = self._image_model.rowCount() - 1
            self.listView.setCurrentIndex(self.listView.model().index(row, first_index.column()))
        self._show_image(row)

    def __on_list_view_current_row_change(self, current: QModelIndex, previous: QModelIndex):
        """
        图片列表当前行变化事件
        :param current: 当前行索引
        :param previous:
        :return:
        """
        index = current.row()
        if index < 0:
            return
        self._show_image(index)

    def _show_image(self, index):
        path = self._image_model.get_item(index).full_path
        start_time = time.time()
        status = f"[{index + 1}/{self._image_model.rowCount()}] {path}"
        try:
            # 填充缩放
            pixmap, is_preload = self.__get_image(index, path)
            cur_time = time.time()
            status += f"\t是否预加载：{is_preload}\t图片读取：{round((cur_time - start_time) * 1000, 2)}ms"
            start_time = time.time()
            # 加载图片
            item = QtWidgets.QGraphicsPixmapItem(pixmap)
            scene = QtWidgets.QGraphicsScene()
            scene.addItem(item)
            self.graphicsView.setScene(scene)
            cur_time = time.time()
            status += f"\t图片加载：{round((cur_time - start_time) * 1000, 2)}ms"
            self._show_info(path)
        except Exception as e:
            print(e)
            QMessageBox.information(self, "提示", str(e), QMessageBox.StandardButton.Ok)
        self.statusbar.showMessage(status)

    def __get_image(self, index, path):
        # 优先从队列中获取
        if index in self._cache:
            pre = self._cache[index]
            if pre.full_path == path:
                print(f"从预载中读取 {index}")
                return pre.pixmap, True
            else:
                del self._cache[index]
        print(f"从文件中读取 {index}")
        image, width, height = ImageHelper.get_image_from_file(path, self.graphicsView.width(),
                                                               self.graphicsView.height())
        return image, False

    _cache = {}

    def __preload(self):
        count = 10
        while True:
            try:
                index = self.listView.currentIndex().row()
                remove_key = []
                for key in self._cache:
                    if key < index or key > index + count * 2:
                        remove_key.append(key)
                for key in remove_key:
                    print(f'删除过期预缓存：{key}')
                    del self._cache[key]
                cache_count = len(self._cache)
                row_count = self._image_model.rowCount()
                if cache_count >= count or row_count == 0 or cache_count + index >= row_count - 1:
                    time.sleep(1)
                    continue
                print('开始预加载')
                for offset in range(1, count + 1):
                    pre_index = index + offset
                    if pre_index in self._cache:
                        continue
                    info = self._image_model.get_item(pre_index)
                    if not info:
                        continue
                    full_path = info.full_path
                    pixmap, width, height = ImageHelper.get_image_from_file(full_path, self.graphicsView.width(),
                                                                            self.graphicsView.height())
                    img = PreloadImage(full_path, pixmap, width, height)
                    self._cache[pre_index] = img
                    print(f"预加载成功：{pre_index}, {full_path}")
                time.sleep(1)
            except Exception as e:
                print(f"预加载失败：{e}")
                time.sleep(1)

    def _show_info(self, path):
        info = self._db_helper.search_by_file_path(path.replace(FileHelper.get_path_prefix(), ''))
        if not info:
            return
        # 显示已有记录
        self.lineEdit_author.setText(info.author_str())
        self.lineEdit_size.setText(f"{info.size} MB")
        self.lineEdit_role.setText(','.join(info.roles))
        self.lineEdit_works.setText(','.join(info.works))
        tags = info.tags
        if not tags:
            return
        tran_tags, source_tags = self._tag_helper.get_tran_tags(tags)
        tags = list(map(lambda x: x.name, tran_tags)) + source_tags
        self.textEdit_tag.setText(','.join(tags))

    def _error_toast(self, error_str):
        QMessageBox.information(self, "提示", error_str, QMessageBox.StandardButton.Ok)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        rect = self.geometry()
        rect_info = f'{rect.left()},{rect.top()},{rect.width()},{rect.height()}'
        self._config.add_config_key('history', 'tagRect', rect_info)
