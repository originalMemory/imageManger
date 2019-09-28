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
import datetime
import os
import re
from enum import unique, Enum

from PIL import Image
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QModelIndex, Qt, QStringListModel
from PyQt5.QtWidgets import QMainWindow, QApplication, QCompleter
from configparser import ConfigParser

from helper import db_helper
from helper.file_helper import FileHelper
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

        # 下拉列表设置
        self._type_model = MyBaseListModel()
        self.comboBox_type.setModel(self._type_model)
        self._type_model.add_items(db_helper.get_model_data_list('type'))
        self.comboBox_type.setCurrentIndex(0)

        self._level_model = MyBaseListModel()
        self.comboBox_level.setModel(self._level_model)
        self._level_model.add_items(db_helper.get_model_data_list('level'))
        self.comboBox_level.setCurrentIndex(0)

        # 图片信息
        self._image_model = ImageFileListModel()
        self._config_filename = "config.ini"
        self._config = ConfigParser()
        if os.path.exists(self._config_filename):
            try:
                self._config.read(self._config_filename, encoding='utf-8')
                last_dir = self._config.get('history', 'lastDir')
                self._image_model.add_dir(last_dir)
            except Exception as e:
                print(e)

        self.listView.setModel(self._image_model)

        # 关联事件
        self.listView.selectionModel().currentChanged.connect(self.on_change)
        self.pushButton_classify.clicked.connect(self.classify)

        # 设置 tab 切换顺序
        self.setTabOrder(self.lineEdit_desc, self.lineEdit_tag)
        self.setTabOrder(self.lineEdit_tag, self.lineEdit_path)
        self.setTabOrder(self.lineEdit_path, self.comboBox_type)
        self.setTabOrder(self.comboBox_type, self.comboBox_level)
        self.setTabOrder(self.comboBox_level, self.lineEdit_role)
        self.setTabOrder(self.lineEdit_role, self.lineEdit_works)
        self.setTabOrder(self.lineEdit_works, self.lineEdit_series)
        self.setTabOrder(self.lineEdit_series, self.lineEdit_source)
        self.setTabOrder(self.lineEdit_source, self.lineEdit_uploader)
        self.setTabOrder(self.lineEdit_uploader, self.lineEdit_author)
        self.setTabOrder(self.lineEdit_author, self.pushButton_classify)
        self.setTabOrder(self.pushButton_classify, self.pushButton_move)

        # 自动补全
        self._completer_list = []
        self._completer_filename = 'works.txt'
        if not os.path.exists(self._completer_filename):
            f = open(self._completer_filename, 'w', encoding='utf-8')
            f.close()
        with open(self._completer_filename, 'r+', encoding='utf-8') as f:
            self._completer_list = list(map(lambda x: x.replace("\n", "").replace("\r", ""), f.readlines()))
        self.completer = QCompleter(self._completer_list)
        self.completer.setCompletionMode(QCompleter.InlineCompletion)
        self.completer.setFilterMode(Qt.MatchContains)
        self.lineEdit_works.setCompleter(self.completer)
        self.lineEdit_works.editingFinished.connect(self.add_complete)
        Image.MAX_IMAGE_PIXELS = 1882320000
        self.listView.setFocus()

    def add_complete(self):
        cur_completion = self.completer.currentCompletion()
        if cur_completion == "":
            self._completer_list.append(self.lineEdit_works.text())
            self.completer = QCompleter(self._completer_list)
            self.completer.setCompletionMode(QCompleter.InlineCompletion)
            self.completer.setFilterMode(Qt.MatchContains)
            self.lineEdit_works.setCompleter(self.completer)
            print(self._completer_list)

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

    def show_image(self, index):
        """
        显示指定索引文件名对应的图片
        :param index: 文件索引
        :return:
        """
        path = self._image_model.get_item(index)['full_path']
        self.statusbar.showMessage(f"[{index + 1}/{self._image_model.rowCount()}] {path}")
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

        path = self._image_model.get_item(current.row())['full_path']
        info = db_helper.search(path)
        if not info:
            # 分析图片信息
            size = FileHelper.get_file_size_in_mb(path)
            width, height = self.get_image_width_and_height(path)
            create_time = FileHelper.get_create_time(path)
            self.lineEdit_desc.setText("")
            self.lineEdit_tag.setText("")
            self.lineEdit_size.setText(f"{size} MB")
            self.lineEdit_width.setText(str(width))
            self.lineEdit_height.setText(str(height))
            self.lineEdit_path.setText(path)
            self.dateTimeEdit_file_create.setDateTime(create_time)
            self.analyze_image_info(path)
            return
        # 显示已有记录
        self.lineEdit_desc.setText(info.desc)
        self.lineEdit_tag.setText(info.tags)
        self.lineEdit_path.setText(info.path)
        self.lineEdit_works.setText(info.works)
        self.lineEdit_source.setText(info.source)
        self.lineEdit_role.setText(info.role)
        self.lineEdit_author.setText(info.author)
        self.lineEdit_series.setText(info.series)
        self.lineEdit_uploader.setText(info.uploader)
        self.lineEdit_size.setText(f"{info.size} MB")
        self.lineEdit_width.setText(str(info.width))
        self.lineEdit_height.setText(str(info.height))
        self.comboBox_type.setCurrentIndex(self._type_model.get_index(info.type_id))
        self.comboBox_level.setCurrentIndex(self._level_model.get_index(info.level_id))
        self.dateTimeEdit_file_create.setDateTime(info.file_create_time)
        self.dateTimeEdit_create.setDateTime(info.create_time)
        self.dateTimeEdit_update.setDateTime(info.update_time)

    def classify(self):
        """
        分类图片
        :return:
        """
        select_rows = self.listView.selectionModel().selectedRows()
        index = self.comboBox_type.currentIndex()
        type_id = self._type_model.get_item(index)['id']
        index = self.comboBox_level.currentIndex()
        level_id = self._level_model.get_item(index)['id']
        desc = self.lineEdit_desc.text()
        author = self.lineEdit_author.text()
        tags = self.lineEdit_tag.text()
        works = self.lineEdit_works.text()
        role = self.lineEdit_role.text()
        source = self.lineEdit_source.text()
        series = self.lineEdit_series.text()
        uploader = self.lineEdit_uploader.text()
        for i in range(len(select_rows)):
            item = self._image_model.get_item(select_rows[i].row())
            filename = item['name']
            path = item['full_path']
            create_time = FileHelper.get_create_time_str(path)
            size = FileHelper.get_file_size_in_mb(path)
            width, height = self.get_image_width_and_height(path)
            image_id = item['id']
            if image_id == 0:
                db_helper.insert_image(
                    desc,
                    author,
                    type_id,
                    level_id,
                    tags,
                    works,
                    role,
                    source,
                    filename,
                    path,
                    width,
                    height,
                    size,
                    create_time,
                    series,
                    uploader
                )
                image_id = db_helper.get_id_by_path(path)
                self._image_model.set_image_id(select_rows[i].row(), image_id)
                self.dateTimeEdit_create.setDateTime(datetime.datetime.now())
                self.dateTimeEdit_update.setDateTime(datetime.datetime.now())
                message = f"{item['relative_path']} 创建完成！"
            else:
                # 批量更新时，保持原来的描述、作者、等级、标签、作品
                old_image = self._image_model.get_database_item(image_id)
                if old_image and len(select_rows) > 1:
                    desc = old_image.desc
                    author = old_image.author
                    level_id = old_image.level_id
                    tags = old_image.tags
                    works = old_image.works
                db_helper.update_image(
                    image_id,
                    desc,
                    author,
                    type_id,
                    level_id,
                    tags,
                    works,
                    role,
                    source,
                    filename,
                    path,
                    width,
                    height,
                    size,
                    create_time,
                    series,
                    uploader
                )
                self.dateTimeEdit_update.setDateTime(datetime.datetime.now())
                message = f"{item['relative_path']} 更新完成！"
            self.statusbar.showMessage(f"[{i + 1}/{len(select_rows)}] {message}")

    @staticmethod
    def get_image_width_and_height(image_path):
        img = Image.open(image_path)
        return img.width, img.height

    def analyze_image_info(self, file_path):
        filename = os.path.basename(file_path)
        yande = 'yande'
        pixiv = 'pixiv'
        if yande not in filename and pixiv not in filename:
            return None
        if yande in filename:
            # [yande_492889_Mr_GT]asian_clothes cleavage clouble tianxia_00
            match = re.search(r"yande.*?_\d*?_(?P<author>.+?)](?P<desc>.+?)\.", filename)
            if match:
                self.lineEdit_author.setText(match.group('author'))
                desc = match.group('desc')
                desc = desc.replace("_00", "")
                self.lineEdit_desc.setText(desc)
                self.lineEdit_source.setText("yande")
            else:
                # yande.re 505 hook neko seifuku shimazu_wakana _summer wallpaper.jpg
                match = re.search(r"yande(.re)? (?P<author>.+?) (?P<desc>.+?)\.", filename)
                if match:
                    self.lineEdit_author.setText(match.group('author'))
                    self.lineEdit_desc.setText(match.group('desc'))
                    self.lineEdit_source.setText("yande")

        if pixiv in filename:
            # [ % site_ % id_ % author] % desc_ % tag <! < _ % imgp[5]
            match = re.search(r"pixiv.*?_\d*?_(?P<author>.+?)](?P<desc>.+?)_(?P<tags>.+?)_", filename)
            if match:
                author = match.group('author')
                author = author.replace("「", '').replace('」的插画', '').replace('」的漫画', '')
                self.lineEdit_author.setText(author)
                self.lineEdit_desc.setText(match.group('desc'))
                tags = match.group('tags')
                tags.replace(';', ',')
                self.lineEdit_tag.setText(tags)
                self.lineEdit_source.setText("pixiv")
            else:
                match = re.search(r"pixiv.*?_\d*?_(?P<author>.+?)](?P<desc>.+?)_", filename)
                if match:
                    author = match.group('author')
                    author = author.replace("「", '').replace('」的插画', '').replace('」的漫画', '')
                    self.lineEdit_author.setText(author)
                    self.lineEdit_desc.setText(match.group('desc'))
                    self.lineEdit_source.setText("pixiv")

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == Qt.Key_R and QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.classify()
            self.listView.setFocus()
        if event.key() == Qt.Key_E and QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.comboBox_level.setFocus()
        if event.key() == Qt.Key_W and QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.lineEdit_works.setText("")
        if event.key() == Qt.Key_Delete:
            self.del_select_rows()

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:
        e.accept()

    def dropEvent(self, e: QtGui.QDropEvent) -> None:
        urls = e.mimeData().urls()
        self._image_model.clear()
        for url in urls:
            self._image_model.add_dir(url.toLocalFile())
        if not self._config.has_section('history'):
            self._config.add_section('history')
        self._config['history']['lastDir'] = urls[0].toLocalFile()

    def del_select_rows(self):
        select_rows = self.listView.selectionModel().selectedRows()
        if len(select_rows) == 0:
            return
        first_index = select_rows[0]
        for i in range(len(select_rows)):
            index = select_rows[i]
            item = self._image_model.get_item(index.row())
            if item['id'] != 0:
                db_helper.delete(item['id'])
            os.remove(item['full_path'])
            self._image_model.delete_item(index.row())
            self.statusbar.showMessage(f"[{i + 1}/{len(select_rows)}] {item['relative_path']} 删除成功！")
        if first_index.row() == 0:
            return
        self.listView.setCurrentIndex(self.listView.model().index(first_index.row() - 1, first_index.column()))
        self.listView.setCurrentIndex(first_index)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        with open(self._completer_filename, 'w+', encoding='utf-8') as f:
            f.writelines(list(map(lambda x: x + "\n", self._completer_list)))

        with open(self._config_filename, 'w', encoding='utf-8') as f:
            self._config.write(f)
