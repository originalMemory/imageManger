#!/user/bin/env python
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : main
@author  : wuhoubo
@desc    : 图片管理
@create  : 2019/6/2 23:57:26
@update  :
"""
import datetime
import os
import queue
import re
import threading
import time
from enum import unique, Enum
from shutil import copyfile

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QModelIndex, Qt, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QApplication, QCompleter, QMessageBox

from helper.config_helper import ConfigHelper
from helper.db_helper import DBHelper
from helper.file_helper import FileHelper
from manager.view.manager import Ui_Manager
from model.ImageFileListModel import ImageFileListModel
from model.data import ImageFile, PreloadImage, MyImage
from model.my_list_model import MyBaseListModel


@unique
class VIEW(Enum):
    LIST = 1
    GRAPHIC = 2


class ImageManager(QMainWindow, Ui_Manager):
    """
    更新 list 信号
    """
    __refresh_list_signal = pyqtSignal()

    def __init__(self, parent=None):
        super(ImageManager, self).__init__(parent)
        self.setupUi(self)

        self.__db_helper = DBHelper(self.db_error_handler)  # 数据库操作

        self.__refresh_list_signal.connect(self.__refresh_list)
        # 下拉列表设置
        self.__type_model = MyBaseListModel()
        self.comboBox_type.setModel(self.__type_model)
        self.__type_model.add_items(self.__db_helper.get_model_data_list('type'))
        self.comboBox_type.setCurrentIndex(0)

        self.__level_model = MyBaseListModel()
        self.comboBox_level.setModel(self.__level_model)
        levels = self.__db_helper.get_model_data_list('level')
        for i in range(len(levels)):
            level = levels[i]
            if level.name == "码":
                levels.remove(level)
                levels.insert(5, level)
        self.__level_model.add_items(levels)
        self.comboBox_level.setCurrentIndex(0)

        # 图片信息
        self.__image_model = ImageFileListModel(self)
        self.__config = ConfigHelper(self)

        last_dir = self.__config.get_config_key('history', 'lastDir')
        if os.path.isdir(last_dir) and os.path.exists(last_dir):
            self.__image_model.add_path(last_dir)
        self.lineEdit_sql_where.setText(self.__config.get_config_key('history', 'sqlWhere'))
        self.lineEdit_export_dir.setText(self.__config.get_config_key('history', 'lastExportDir'))

        self.listView.setModel(self.__image_model)

        # 关联事件
        self.listView.selectionModel().currentChanged.connect(self.__on_list_view_current_row_change)
        self.listView.set_key_press_delegate(self.key_press_delegate)
        self.listView.set_action_show_file_directory_delegate(self.open_file_directory)
        self.pushButton_classify.clicked.connect(self.__classify)
        self.pushButton_search.clicked.connect(self.__search)
        self.pushButton_clean.clicked.connect(self.__clean_not_exist_images)
        self.actionOpen.triggered.connect(self.__open_files)
        self.lineEdit_sql_where.returnPressed.connect(self.__search)
        self.pushButton_export_dir.clicked.connect(self.__choose_export_dir)
        self.pushButton_export.clicked.connect(self.__choose_export)
        self.lineEdit_desc.returnPressed.connect(self.__classify)
        self.lineEdit_tag.returnPressed.connect(self.__classify)
        self.lineEdit_role.returnPressed.connect(self.__classify)
        self.lineEdit_works.returnPressed.connect(self.__classify)
        self.lineEdit_series.returnPressed.connect(self.__classify)
        self.lineEdit_source.returnPressed.connect(self.__classify)
        self.lineEdit_uploader.returnPressed.connect(self.__classify)
        self.lineEdit_author.returnPressed.connect(self.__classify)

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
        self.setTabOrder(self.pushButton_classify, self.pushButton_search)

        # 自动补全
        self.__completer_list = []
        self.__completer_filename = 'works.txt'
        if not os.path.exists(self.__completer_filename):
            f = open(self.__completer_filename, 'w', encoding='utf-8')
            f.close()
        with open(self.__completer_filename, 'r+', encoding='utf-8') as f:
            self.__completer_list = list(map(lambda x: x.replace("\n", "").replace("\r", ""), f.readlines()))
        self.completer = QCompleter(self.__completer_list)
        self.completer.setCompletionMode(QCompleter.InlineCompletion)
        self.completer.setFilterMode(Qt.MatchContains)
        self.lineEdit_works.setCompleter(self.completer)
        self.lineEdit_works.editingFinished.connect(self.__add_complete)

        # Image.MAX_IMAGE_PIXELS = 1882320000
        self.listView.setFocus()

        # 预加载图片
        threading.Thread(target=self.__preload, daemon=True).start()

    def __add_complete(self):
        """
        添加自动补全作品
        :return:
        """
        cur_completion = self.completer.currentCompletion()
        if cur_completion == "":
            self.__completer_list.append(self.lineEdit_works.text())
            self.completer = QCompleter(self.__completer_list)
            self.completer.setCompletionMode(QCompleter.InlineCompletion)
            self.completer.setFilterMode(Qt.MatchContains)
            self.lineEdit_works.setCompleter(self.completer)
            print(self.__completer_list)

    def __open_files(self):
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
            item_data = ImageFile(
                name="%s/%s" % (tp_lists[-2], tp_lists[-1]),
                full_path=path
            )
            self.__image_model.addItem(item_data)

    def __choose_export_dir(self):
        """
        选择保存文件夹
        :return:
        """
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, "选择保存的文件夹", "E:/图片")
        self.lineEdit_export_dir.setText(dir_path)

    def __show_image(self, index):
        """
        显示指定索引文件名对应的图片
        :param index: 文件索引
        :return:
        """
        path = self.__image_model.get_item(index).full_path
        start_time = time.time()
        status = f"[{index + 1}/{self.__image_model.rowCount()}] {path}"
        try:
            # 填充缩放
            pixmap, is_preload = self.__get_image(path)
            cur_time = time.time()
            status += f"\t是否预加载：{is_preload}\t图片读取：${round((cur_time - start_time) * 1000, 2)}ms"
            start_time = time.time()
            # 加载图片
            item = QtWidgets.QGraphicsPixmapItem(pixmap)
            scene = QtWidgets.QGraphicsScene()
            scene.addItem(item)
            self.graphicsView.setScene(scene)
            cur_time = time.time()
            status += f"\t图片加载：${round((cur_time - start_time) * 1000, 2)}ms"
        except Exception as e:
            print(e)
            QMessageBox.information(self, "提示", str(e), QMessageBox.Ok)
        self.__analysis_file_info(path)
        self.statusbar.showMessage(status)

    def __on_list_view_current_row_change(self, current: QModelIndex, previous: QModelIndex):
        """
        图片列表当前行变化事件
        :param current: 当前行索引
        :param previous:
        :return:
        """
        self.__show_image(current.row())

    def __analysis_file_info(self, path):
        info = self.__db_helper.search_by_file_path(path)
        if not info:
            # 分析图片信息
            size = FileHelper.get_file_size_in_mb(path)
            create_time = FileHelper.get_create_time(path)
            self.lineEdit_desc.setText("")
            self.lineEdit_tag.setText("")
            self.lineEdit_size.setText(f"{size} MB")
            self.lineEdit_path.setText(path)
            self.dateTimeEdit_file_create.setDateTime(create_time)
            self.__analyze_image_info(path)
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
        self.comboBox_type.setCurrentIndex(self.__type_model.get_index(info.type_id))
        self.comboBox_level.setCurrentIndex(self.__level_model.get_index(info.level_id))
        self.dateTimeEdit_file_create.setDateTime(info.file_create_time)
        self.dateTimeEdit_create.setDateTime(info.create_time)
        self.dateTimeEdit_update.setDateTime(info.update_time)

    def __classify(self):
        """
        分类图片
        :return:
        """
        select_rows = self.listView.selectionModel().selectedRows()
        select_rows = [x for x in select_rows]
        th = threading.Thread(target=self.__insert_or_update_db, args=(select_rows,), daemon=True)
        th.start()
        end_index = select_rows[-1]
        self.__select_index(self.__image_model.index(end_index.row() + 1, end_index.column()))

    def __insert_or_update_db(self, select_rows):
        index = self.comboBox_type.currentIndex()
        type_id = self.__type_model.get_item(index).id
        index = self.comboBox_level.currentIndex()
        level_id = self.__level_model.get_item(index).id
        desc = self.lineEdit_desc.text()
        author = self.lineEdit_author.text()
        tags = self.lineEdit_tag.text()
        works = self.lineEdit_works.text()
        role = self.lineEdit_role.text()
        source = self.lineEdit_source.text()
        series = self.lineEdit_series.text()
        uploader = self.lineEdit_uploader.text()
        for i in range(len(select_rows)):
            item = self.__image_model.get_item(select_rows[i].row())
            filename = item.name
            path = item.full_path
            file_create_time = FileHelper.get_create_time_str(path)
            size = FileHelper.get_file_size_in_mb(path)
            width = self.lineEdit_width.text()
            height = self.lineEdit_height.text()
            image_id = item.id
            image = MyImage(image_id, desc, author, type_id, level_id, tags, works, role, source, width, height, size,
                            filename, path, file_create_time, "", "", series, uploader)
            if image_id == 0:
                self.__db_helper.insert_image(image)
                image_id = self.__db_helper.get_id_by_path(path)
                self.__image_model.set_image_id(select_rows[i].row(), image_id)
                self.dateTimeEdit_create.setDateTime(datetime.datetime.now())
                self.dateTimeEdit_update.setDateTime(datetime.datetime.now())
                # message = f"{item.name} 创建完成！"
                self.__refresh_list_signal.emit()
            else:
                # 批量更新时，保持原来的描述、作者、等级、标签、作品
                old_image = self.__image_model.get_database_item(image_id)
                if old_image and len(select_rows) > 1:
                    image.desc = old_image.desc
                    image.author = old_image.author
                    image.level_id = old_image.level_id
                    image.tags = old_image.tags
                    image.works = old_image.works
                self.__db_helper.update_image(image)
                self.dateTimeEdit_update.setDateTime(datetime.datetime.now())
                message = f"{item.name} 更新完成！"
                self.statusbar.showMessage(f"[{i + 1}/{len(select_rows)}] {message}")
        # end_index = select_rows[-1]
        # self.__refresh_list_signal.emit(self.__image_model.index(end_index.row() + 1, end_index.column()))

    def __refresh_list(self):
        self.listView.clearFocus()
        self.listView.setFocus()

    def __select_index(self, index: QModelIndex):
        if 0 < index.row() < self.__image_model.rowCount():
            self.listView.setCurrentIndex(index)
            self.listView.setFocus()
        else:
            self.listView.clearFocus()
            self.listView.setFocus()

    @staticmethod
    def __get_image_width_and_height(image_path):
        """
        获取图片的宽高
        :param image_path: 图片路径
        :return:
        """
        try:
            img = QtGui.QPixmap(image_path)
            return img.width(), img.height()
        except Exception as e:
            print(e)
            return 0, 0

    def __analyze_image_info(self, file_path):
        """
        根据文件路径分析图片信息
        :param file_path: 图片路径
        :return:
        """
        filename = os.path.basename(file_path)
        yande = 'yande'
        pixiv = 'pixiv'
        # cosplay = '/Cosplay/'
        filter_list = [yande, pixiv]
        exclude_list = ['Cosplay/购买', 'Cosplay/Flameworks']
        is_in = False
        for f in filter_list:
            if f in file_path:
                is_in = True
                break
        for e in exclude_list:
            if e in file_path:
                is_in = False
        if not is_in:
            return None

        if yande in filename:
            desc, uploader = FileHelper.analysisYande(filename)
            if desc:
                self.lineEdit_desc.setText(desc)
                self.lineEdit_source.setText("yande")
            if uploader:
                self.lineEdit_uploader.setText(uploader)

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
        # if cosplay in file_path:
        #     match = re.search(r"Cosplay/(?P<works>.+?)/(?P<info>.+?)/", file_path)
        #     if match:
        #         self.lineEdit_works.setText(match.group('works'))
        #         info_list = match.group('info').split(' - ')
        #         info_list = [x.strip() for x in info_list]
        #         if len(info_list) > 2:
        #             author = ' - '.join(info_list[0:-1])
        #         else:
        #             author = info_list[0]
        #         self.lineEdit_series.setText(author)
        #         self.lineEdit_author.setText(info_list[-1])
        #         self.comboBox_type.setCurrentIndex(1)

    def __del_select_rows(self):
        """
        删除选中行
        :return:
        """
        select_rows = self.listView.selectionModel().selectedRows()
        if len(select_rows) == 0:
            return
        first_index = select_rows[0]
        for i in range(len(select_rows)):
            index = select_rows[i]
            item = self.__image_model.get_item(index.row() - i)
            if item.id != 0:
                self.__db_helper.delete(item.id)
            os.remove(item.full_path)
            self.__image_model.delete_item(index.row() - i)
            self.statusbar.showMessage(f"[{i + 1}/{len(select_rows)}] {item.name} 删除成功！")

        if len(select_rows) > 1:
            self.listView.clearSelection()
        # 如果删除到了最后一行，则刷新上一个
        if first_index.row() >= self.__image_model.rowCount():
            if first_index.row() == 0:
                return
            else:
                self.listView.setCurrentIndex(self.listView.model().index(first_index.row() - 1, first_index.column()))
        else:
            if len(select_rows) > 1:
                self.listView.setCurrentIndex(first_index)
            else:
                self.__show_image(first_index.row())

    def __search(self):
        sql_where = self.lineEdit_sql_where.text()
        if not sql_where:
            sql_where = ""
            if len(self.lineEdit_desc.text()):
                sql_where += f" `desc` like '%{self.lineEdit_desc.text()}%'"
            if len(self.lineEdit_role.text()):
                sql_where += f" `role` like '%{self.lineEdit_role.text()}%'"
            if len(self.lineEdit_works.text()):
                sql_where += f" `works` like '%{self.lineEdit_works.text()}%'"
            if len(self.lineEdit_series.text()):
                sql_where += f" `series` like '%{self.lineEdit_series.text()}%'"
            if len(self.lineEdit_source.text()):
                sql_where += f" `source` like '%{self.lineEdit_source.text()}%'"
            if len(self.lineEdit_uploader.text()):
                sql_where += f" `uploader` like '%{self.lineEdit_uploader.text()}%'"
            if len(self.lineEdit_author.text()):
                sql_where += f" `author` like '%{self.lineEdit_author.text()}%'"
        image_sql_list, image_file_list = self.__db_helper.search_by_where(sql_where)
        if len(image_sql_list) > 0:
            self.__image_model.set_images(image_sql_list, image_file_list)
            self.listView.setFocus()
            self.listView.scrollToTop()

    def __choose_export(self):
        dir_path = self.lineEdit_export_dir.text()
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        if not os.path.isdir(dir_path):
            return

        for i in range(self.__image_model.rowCount()):
            image = self.__image_model.get_item(i)
            if image.id:
                image_sql = self.__image_model.get_database_item(image.id)
                if not os.path.exists(image_sql.path):
                    continue

                try:
                    self.copyfile_without_override(image_sql.path, dir_path)
                except Exception as e:
                    print(e)
            else:
                self.copyfile_without_override(image.full_path, dir_path)

            self.statusbar.showMessage(f"[{i + 1}/{self.__image_model.rowCount()}] {image.name} 复制成功！")

    def copyfile_without_override(self, origin_file_path, dir_path):
        filename = os.path.basename(origin_file_path)
        target_file_path = os.path.join(dir_path, filename)
        (shot_name, extension) = os.path.splitext(filename)
        no = 1
        while True:
            if not os.path.exists(target_file_path):
                break
            filename = f"{shot_name}{no}{extension}"
            target_file_path = os.path.join(dir_path, filename)
            no += 1

        copyfile(origin_file_path, os.path.join(dir_path, filename))

    # region 重写 Qt 控件方法
    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        # 键盘快捷键事件
        if event.key() == Qt.Key_R and QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.__classify()
            self.listView.setFocus()
        if event.key() == Qt.Key_E and QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.comboBox_level.setFocus()
        if event.key() == Qt.Key_W and QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.lineEdit_works.setText("")
        # if event.key() == Qt.Key_Delete:
        #     self.__del_select_rows()

    def key_press_delegate(self, event: QtGui.QKeyEvent):
        level_index = None
        if event.key() == Qt.Key_1:
            level_index = 1
        if event.key() == Qt.Key_2:
            level_index = 2
        if event.key() == Qt.Key_3:
            level_index = 3
        if event.key() == Qt.Key_4:
            level_index = 4
        if event.key() == Qt.Key_5:
            level_index = 5
        if event.key() == Qt.Key_6:
            level_index = 6
        if event.key() == Qt.Key_7:
            level_index = 7
        if event.key() == Qt.Key_8:
            level_index = 8
        if event.key() == Qt.Key_9:
            level_index = 9

        if level_index and self.__level_model.rowCount() >= level_index:
            self.comboBox_level.setCurrentIndex(level_index - 1)
            return True

        if event.key() == Qt.Key_R:
            self.__classify()
            return True
        if event.key() == Qt.Key_E:
            self.lineEdit_role.setFocus()
            return True
        if event.key() == Qt.Key_C:
            self.lineEdit_works.setText("")
            return True
        if event.key() == Qt.Key_D:
            self.__del_select_rows()
            return True
        if event.key() == Qt.Key_W:
            current_index = self.listView.currentIndex()
            if current_index.row() > 0:
                self.listView.setCurrentIndex(self.__image_model.index(current_index.row() - 1, current_index.column()))
            return True
        if event.key() == Qt.Key_S:
            current_index = self.listView.currentIndex()
            if current_index.row() < self.__image_model.rowCount() - 1:
                self.listView.setCurrentIndex(self.__image_model.index(current_index.row() + 1, current_index.column()))
            return True
        return False

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:
        # 设置允许接收
        e.accept()

    def dropEvent(self, e: QtGui.QDropEvent) -> None:
        # 接收文件夹和文件以刷新图片列表
        urls = e.mimeData().urls()
        th = threading.Thread(target=self.__load_list_data, args=(urls,), daemon=True)
        th.start()

    def __load_list_data(self, urls):
        self.__image_model.clear()
        for url in urls:
            self.__image_model.add_path(url.toLocalFile())
        if self.__image_model.rowCount() > 0:
            self.listView.setCurrentIndex(self.__image_model.index(0, 0))
        if not os.path.isdir(urls[0].toLocalFile()):
            return
        self.__config.add_config_key('history', 'lastDir', urls[0].toLocalFile())

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.__config.add_config_key('history', 'lastExportDir', self.lineEdit_export_dir.text())
        self.__config.add_config_key('history', 'sqlWhere', self.lineEdit_sql_where.text())
        # 关闭时保存自动填充作品列表的配置文件
        with open(self.__completer_filename, 'w+', encoding='utf-8') as f:
            f.writelines(list(map(lambda x: x + "\n", self.__completer_list)))

    # endregion

    # region 预加载图片
    __preload_count = 5
    __preload_image_queue = queue.Queue(__preload_count)
    __preload_image_size = queue.Queue(__preload_count)
    __preload_lock = threading.Lock()

    def __preload(self):
        while True:
            if self.__preload_image_queue.qsize() == 5:
                time.sleep(1)
                continue

            index = self.listView.currentIndex().row()
            preload_index = index + self.__preload_image_queue.qsize() + 1
            image_file = self.__image_model.get_item(preload_index)
            if not image_file:
                time.sleep(1)
                continue

            full_path = image_file.full_path
            try:
                pixmap, width, height = self.__get_image_from_file(full_path)
                self.__preload_image_queue.put(PreloadImage(full_path, pixmap))
                self.__preload_image_size.put((width, height))
                print(f"预加载成功：{full_path}")
            except Exception as e:
                print(e)
                print(f"预加载失败：{full_path}")
                time.sleep(1)

    def __get_image_from_file(self, path):
        """
        从路径读取图片文件
        :param path: 图片路径
        :return:
        """
        qim = QtGui.QImage(path)
        width = qim.width()
        height = qim.height()
        x_scale = self.graphicsView.width() / float(qim.width())
        y_scale = self.graphicsView.height() / float(qim.height())
        if x_scale < y_scale:
            qim = qim.scaledToWidth(self.graphicsView.width(), Qt.SmoothTransformation)
        else:
            qim = qim.scaledToHeight(self.graphicsView.height(), Qt.SmoothTransformation)
        pixmap = QtGui.QPixmap.fromImage(qim)
        return pixmap, width, height

    def __get_image(self, path):
        # 优先从队列中获取
        while self.__preload_image_queue.qsize() > 0:
            image = self.__preload_image_queue.get()
            size = self.__preload_image_size.get()
            if isinstance(image, PreloadImage) and image.full_path == path:
                print("从预载中读取")
                self.lineEdit_width.setText(str(size[0]))
                self.lineEdit_height.setText(str(size[1]))
                return image.pixmap, True
        print("从文件中读取")
        image, width, height = self.__get_image_from_file(path)
        self.lineEdit_width.setText(str(width))
        self.lineEdit_height.setText(str(height))
        return image, False

    def __clean_not_exist_images(self):
        """
        清理不存在的图片
        :return:
        """
        page = 0
        pagesize = 500
        count = self.__db_helper.get_table_count(f"select count(*) from myacg.image;")
        while True:
            image_list = self.__db_helper.get_images(page, pagesize)

            if len(image_list) == 0:
                break
            self.statusbar.showMessage(f"[{(page + 1) * pagesize}/{count}] 无效验证")
            for image in image_list:
                if "?" in image.path:
                    continue
                if not os.path.exists(image.path):
                    self.__db_helper.delete(image.id)
            page += 1

    def open_file_directory(self):
        """
        打开文件所在目录并选中文件
        :return:
        """
        select_rows = self.listView.selectionModel().selectedRows()
        if not len(select_rows):
            return
        file_path = self.__image_model.get_item(select_rows[0].row()).full_path
        FileHelper.open_file_directory(file_path)

    def db_error_handler(self, error_str):
        QMessageBox.information(self, "提示", error_str, QMessageBox.Ok)
