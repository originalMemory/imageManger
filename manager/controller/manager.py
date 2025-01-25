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
import json
import os
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from enum import unique, Enum

from PIL import Image
from PyQt6 import QtWidgets, QtGui
from PyQt6.QtCore import QModelIndex, Qt, pyqtSignal
from PyQt6.QtWidgets import QMainWindow, QApplication, QCompleter, QMessageBox
from bson import ObjectId

from helper.config_helper import ConfigHelper
from helper.db_helper import DBHelper, Col
from helper.file_helper import FileHelper
from helper.image_helper import ImageHelper
from manager.view.manager import Ui_Manager
from model.ImageFileListModel import ImageFileListModel
from model.data import ImageFile, PreloadImage, MyImage, TagType, Tag, TagSource
from model.my_list_model import MyBaseListModel


@unique
class VIEW(Enum):
    LIST = 1
    GRAPHIC = 2


class ImageManager(QMainWindow, Ui_Manager):
    _signal_update_image_id = pyqtSignal(QModelIndex, ImageFile)
    _signal_update_status = pyqtSignal(str)
    _signal_update_tags = pyqtSignal(str)
    _signal_update_authors = pyqtSignal(str)
    _signal_update_roles = pyqtSignal(str)
    _signal_update_works = pyqtSignal(str)
    _signal_handle_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super(ImageManager, self).__init__(parent)
        self.setupUi(self)
        self.__config = ConfigHelper(self)
        rect_info = self.__config.get_config_key('history', 'rect')
        rect = rect_info.split(',')
        if len(rect) == 4:
            left, top, width, height = int(rect[0]), int(rect[1]) - 32, int(rect[2]), int(rect[3])
            self.move(left, top)
            self.resize(width, height)
        else:
            self.__config.add_config_key('history', 'rect', '')

        self.__db_helper = DBHelper(self.db_error_handler)  # 数据库操作

        # 下拉列表设置
        self.__type_model = MyBaseListModel()
        self.comboBox_type.setModel(self.__type_model)
        self.__type_model.add_items(self.__db_helper.get_model_data_list('type'))
        self.comboBox_type.setCurrentIndex(0)

        self.__level_model = MyBaseListModel()
        self.comboBox_level.setModel(self.__level_model)
        levels = self.__db_helper.get_model_data_list('level')
        levels = sorted(levels, key=lambda x: x.id)
        self.__level_model.add_items(levels)
        self.comboBox_level.setCurrentIndex(0)

        # 图片信息
        self.__image_model = ImageFileListModel(self)
        self.__image_model.delete_repeat = self.checkBox_delete_repeat.isChecked()

        threading.Thread(target=self._load_default_images, daemon=True).start()
        self.lineEdit_sql_where.setText(self.__config.get_config_key('history', 'sqlWhere'))
        self.lineEdit_export_dir.setText(self.__config.get_config_key('history', 'lastExportDir'))

        self.listView.setModel(self.__image_model)

        # 关联事件
        self.listView.selectionModel().currentChanged.connect(self.__on_list_view_current_row_change)
        self.listView.set_key_press_delegate(self.key_press_delegate)
        self.listView.set_action_show_file_directory_delegate(self.open_file_directory)
        self.pushButton_classify.clicked.connect(self.__classify)
        self.pushButton_search.clicked.connect(self.__search)
        self.checkBox_delete_repeat.clicked.connect(self._on_check_box_delete_repeat_click)
        self.actionOpen.triggered.connect(self.__open_files)
        self.lineEdit_sql_where.returnPressed.connect(self.__search)
        self.pushButton_export_dir.clicked.connect(self.__choose_export_dir)
        self.pushButton_export.clicked.connect(self.__choose_export)
        self.lineEdit_desc.returnPressed.connect(self.__classify)
        self.lineEdit_role.returnPressed.connect(self.__classify)
        self.lineEdit_works.returnPressed.connect(self.__classify)
        self.lineEdit_series.returnPressed.connect(self.__classify)
        self.lineEdit_source.returnPressed.connect(self.__classify)
        self.lineEdit_uploader.returnPressed.connect(self.__classify)
        self.lineEdit_author.returnPressed.connect(self.__classify)
        self.lineEdit_sequence.returnPressed.connect(self.__classify)
        self._signal_update_image_id.connect(self._update_image_id)
        self._signal_update_status.connect(self._update_status)
        self._signal_update_tags.connect(self._update_tags)
        self._signal_update_roles.connect(self._update_roles)
        self._signal_update_works.connect(self._update_works)
        self._signal_update_authors.connect(self._update_authors)
        self._signal_handle_error.connect(self._handle_error)

        # 设置 tab 切换顺序
        self.setTabOrder(self.lineEdit_desc, self.textEdit_tag)
        self.setTabOrder(self.textEdit_tag, self.lineEdit_path)
        self.setTabOrder(self.lineEdit_path, self.comboBox_type)
        self.setTabOrder(self.comboBox_type, self.comboBox_level)
        self.setTabOrder(self.comboBox_level, self.lineEdit_role)
        self.setTabOrder(self.lineEdit_role, self.lineEdit_works)
        self.setTabOrder(self.lineEdit_works, self.lineEdit_series)
        self.setTabOrder(self.lineEdit_series, self.lineEdit_source)
        self.setTabOrder(self.lineEdit_source, self.lineEdit_sequence)
        self.setTabOrder(self.lineEdit_sequence, self.lineEdit_uploader)
        self.setTabOrder(self.lineEdit_uploader, self.lineEdit_author)
        self.setTabOrder(self.lineEdit_author, self.pushButton_classify)
        self.setTabOrder(self.pushButton_classify, self.pushButton_search)

        # 自动补全
        self.lineEdit_works.setCompleter(self._create_completer(TagType.Work))
        self.lineEdit_role.setCompleter(self._create_completer(TagType.Role))
        self.checkBox_delete_repeat.setChecked(True)
        self.__image_model.delete_repeat = True

        Image.MAX_IMAGE_PIXELS = 1882320000
        self.listView.setFocus()

        # 预加载图片
        threading.Thread(target=self.__preload, daemon=True).start()
        # threading.Thread(target=self._insert_or_update, daemon=True).start()

    def _create_completer(self, tag_type: TagType):
        names = self.__db_helper.search_all(Col.Tag, {'type': tag_type.value}, {'tran': 1})
        names = [x['tran'] for x in names]
        completer = QCompleter(names)
        # completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        return completer

    def _load_default_images(self):
        last_dir = self.__config.get_config_key('history', 'lastDir')
        if os.path.isdir(last_dir) and os.path.exists(last_dir):
            self.__image_model.add_path(last_dir)
            if self.__image_model.rowCount() > 0:
                self.listView.setCurrentIndex(self.__image_model.index(0, 0))

    def __open_files(self):
        """
        打开图片文件
        :return:
        """
        path_list = \
            QtWidgets.QFileDialog.getOpenFileNames(self, "选择文件", filter='图片(*.jpg *.png *.gif *.jpeg *.bmp)')[0]
        # 生成List使用的Model
        for path in path_list:
            tp_lists = path.split('/')
            item_data = ImageFile(
                name="%s/%s" % (tp_lists[-2], tp_lists[-1]),
                full_path=path
            )
            self.__image_model.add_item(item_data)

    def __choose_export_dir(self):
        """
        选择保存文件夹
        :return:
        """
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, "选择保存的文件夹", "E:/图片")
        self.lineEdit_export_dir.setText(dir_path)

    # @timeit
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
        except Exception as e:
            print(e)
            QMessageBox.information(self, "提示", str(e), QMessageBox.StandardButton.Ok)
        self.__analysis_file_info(path)
        self.statusbar.showMessage(status)

    def __on_list_view_current_row_change(self, current: QModelIndex, _: QModelIndex):
        """
        图片列表当前行变化事件
        :param current: 当前行索引
        :param _:
        :return:
        """
        self.__show_image(current.row())

    def __analysis_file_info(self, path):
        info = self.__db_helper.search_by_file_path(path)
        if not info:
            # 清空二次元图上一次自动识别的结果
            is_anim = self.__type_model.get_item(self.comboBox_type.currentIndex()).id == 1
            if is_anim:
                self.lineEdit_role.clear()
                self.lineEdit_works.clear()
                self.lineEdit_author.clear()
                # self.lineEdit_series.clear()

            # 分析图片信息
            self.lineEdit_path.setText(path)
            info = ImageHelper.analyze_image_info(path, check_size=False)
            if info.desc:
                self.lineEdit_desc.setText(info.desc)
            if info.tags:
                self.textEdit_tag.setText(','.join(info.tags))
            if info.source:
                self.lineEdit_source.setText(info.source)
            if info.uploader:
                self.lineEdit_uploader.setText(info.uploader)
            if info.authors:
                self.lineEdit_author.setText(info.author_str())
            if info.works:
                self.lineEdit_works.setText(','.join(info.works))
            if not self.lineEdit_sequence.text():
                self.lineEdit_sequence.setText('0')
            if info.sequence:
                self.lineEdit_sequence.setText(str(info.sequence))
            threading.Thread(target=self._refresh_tran_tags, args=(info.tags, False,), daemon=True).start()
            return
        # 显示已有记录
        self.lineEdit_desc.setText(info.desc)
        self.lineEdit_path.setText(info.full_path())
        self.lineEdit_source.setText(info.source)
        self.lineEdit_author.setText(info.author_str())
        self.lineEdit_series.setText(info.series)
        self.lineEdit_sequence.setText(str(info.sequence))
        self.lineEdit_uploader.setText(info.uploader)
        self.lineEdit_size.setText(f"{info.size} MB")
        self.lineEdit_role.setText(','.join(info.roles))
        self.lineEdit_works.setText(','.join(info.works))
        self.comboBox_type.setCurrentIndex(self.__type_model.get_index(info.type))
        self.comboBox_level.setCurrentIndex(self.__level_model.get_index(info.level))
        self.dateTimeEdit_file_create.setDateTime(info.file_create_time)
        self.dateTimeEdit_create.setDateTime(info.create_time)
        self.dateTimeEdit_update.setDateTime(info.update_time)
        tags = info.tags
        if not tags:
            tags = ImageHelper.analyze_image_info(info.path).tags
        threading.Thread(target=self._refresh_tran_tags, args=(tags, False,), daemon=True).start()

    def _refresh_tran_tags(self, source_tags, keep_role):
        if not source_tags:
            self._signal_update_tags.emit('')
            # self.textEdit_tag.setText('')
            return
        tran_tags = self._get_tran_tags(source_tags)
        roles = set()
        works = set()
        authors = set()
        tags = []
        for tag in tran_tags:
            show = tag.tran if tag.tran else tag.name
            tags.append(f'{show}##{tag.type}')
            if tag.get_type() == TagType.Role:
                roles.add(tag.tran.split('(')[0])
            elif tag.get_type() == TagType.Work:
                works.add(tag.tran)
            elif tag.get_type() == TagType.Author:
                authors.add(tag.tran)
        if keep_role and self.lineEdit_role.text():
            roles += set(self.lineEdit_role.text().split(','))
        self._signal_update_tags.emit(','.join(tags))
        if roles and not self.lineEdit_role.text():
            self._signal_update_roles.emit(','.join(roles))
        if works and not self.lineEdit_works.text():
            self._signal_update_works.emit(','.join(works))
        if authors and not self.lineEdit_author.text():
            self._signal_update_authors.emit(','.join(authors))

    def _get_tran_tags(self, tags):
        dest_ids = []
        for tag_name in tags:
            if isinstance(tag_name, ObjectId):
                dest_ids.append(tag_name)
                continue
            source = TagSource.Yande
            source_name = self.lineEdit_source.text()
            if source_name:
                source = TagSource(source_name)
            tag = self.__db_helper.find_or_create_tag(tag_name, source)
            if tag.children:
                dest_ids += tag.children
            else:
                dest_ids.append(tag.id())
        tags = self.__db_helper.find_decode(Tag, {'_id': {'$in': dest_ids}})
        return tags

    def __classify(self):
        """
        分类图片
        :return:
        """
        select_rows = self.listView.selectionModel().selectedRows()
        select_rows = [x for x in select_rows]
        if len(select_rows) > 1:
            threading.Thread(target=self._prepare_classify, args=(select_rows,), daemon=True).start()
        else:
            self._prepare_classify(select_rows)
        end_index = select_rows[-1]
        next_index = self.__image_model.index(end_index.row() + 1, end_index.column())
        if 0 < next_index.row() < self.__image_model.rowCount():
            self.listView.setCurrentIndex(next_index)
        # else:
        #     self.listView.clearFocus()
        # self.listView.setFocus()

    def _prepare_classify(self, select_rows):
        index = self.comboBox_type.currentIndex()
        type_value = self.__type_model.get_item(index).id
        index = self.comboBox_level.currentIndex()
        level = self.__level_model.get_item(index).id
        desc = self.lineEdit_desc.text()
        authors = self.lineEdit_author.text().split(',')
        if '' in authors:
            authors.remove('')
        tags = self.textEdit_tag.toPlainText().split(',')
        if '' in tags:
            tags.remove('')
        works = self.lineEdit_works.text().split(',')
        if '' in works:
            works.remove('')
        roles = self.lineEdit_role.text().split(',')
        if '' in roles:
            roles.remove('')
        source = self.lineEdit_source.text()
        sequence = int(self.lineEdit_sequence.text())
        series = self.lineEdit_series.text()
        uploader = self.lineEdit_uploader.text()
        for row in select_rows:
            item = self.__image_model.get_item(row.row())
            path = item.full_path
            relative_path = FileHelper.get_relative_path(path)
            # width 和 height 放到编程里更新
            image = MyImage(_id=item.id, desc=desc, authors=authors, type=type_value, level=level, tags=tags,
                            works=works, roles=roles, source=source, width=0, height=0, size=0, path=relative_path,
                            md5='', file_create_time=datetime.datetime.now(), series=series, uploader=uploader,
                            sequence=sequence)
            if image.id():
                # 批量更新时，保持原来的描述、作者、等级、标签、作品
                old_image = self.__image_model.get_database_item(image.id())
                if old_image and len(select_rows) > 1:
                    image.desc = old_image.desc
                    image.authors = old_image.authors
                    image.level = old_image.level
                    image.tags = old_image.tags
                    image.works = old_image.works
            threading.Thread(target=self._insert_or_update, args=(row, image), daemon=True).start()
            # self._change_tasks.put((row, image))
            if not self.listView.hasFocus():
                self.listView.setFocus()

    _change_tasks = queue.Queue()

    def _insert_or_update(self, row, image):
        try:
            # row, image = self._change_tasks.get()
            item = self.__image_model.get_item(row.row())
            path = image.full_path()
            if not os.path.exists(path):
                print(f'文件不存在：{path}')
                return
            need_refresh_item = False
            width, height = ImageHelper.get_image_width_and_height(path)
            image.width = width
            image.height = height
            image.size = FileHelper.get_file_size_in_mb(path)
            image.md5 = FileHelper.get_md5(path)
            image.file_create_time = FileHelper.get_create_time(path)
            new_item = item
            remove_tag_path = ImageHelper.remove_tags(path)
            src_path = path
            if remove_tag_path and remove_tag_path != path:
                try:
                    if os.path.exists(remove_tag_path):
                        os.remove(path)
                    new_name = remove_tag_path.replace(path.replace(item.name, ''), '')
                    path = remove_tag_path
                    image.path = FileHelper.get_relative_path(path)
                    need_refresh_item = True
                    new_item = ImageFile(id=image.id(), name=new_name, full_path=path)
                except Exception as e:
                    print(f"重命名失败：{e}")
            for i, title_and_type in enumerate(image.tags):
                title, tag_type = title_and_type.split('##')
                tag_fl = {'tran': title, 'type': tag_type}
                if not tag_type:
                    del tag_fl['type']
                    tag_fl['$or'] = [{'type': {'$exists': False}}, {'type': tag_type}]
                tag = self.__db_helper.find_one_decode(Tag, tag_fl)
                if not tag:
                    del tag_fl['tran']
                    tag_fl['name'] = title
                    tag = self.__db_helper.find_one_decode(Tag, tag_fl)
                image.tags[i] = tag.id()
            if not image.id():
                self.__db_helper.insert_image(image)
                image_id = self.__db_helper.get_id_by_path(image.path)
                need_refresh_item = True
                new_item.id = image_id
            else:
                self.__db_helper.update_image(image)
                message = f"{item.name} 更新完成！"
                self.statusbar.showMessage(f"[{row.row() + 1}/{self.__image_model.rowCount()}] {message}")
            if remove_tag_path and remove_tag_path != src_path:
                os.rename(src_path, remove_tag_path)
            if need_refresh_item:
                self._signal_update_image_id.emit(row, new_item)
            # ImageHelper.del_tag_file(path)
        except Exception as e:
            print(f"分类失败：{e}")
            self._signal_handle_error.emit(f"分类失败：{e}")

    def _handle_error(self, msg):
        QMessageBox.information(self, "提示", msg, QMessageBox.StandardButton.Ok)

    def _update_image_id(self, index: QModelIndex, image_file: ImageFile):
        self.__image_model.update_item(index, image_file)

    def _update_status(self, msg):
        self.statusbar.showMessage(msg)

    def _update_tags(self, msg):
        self.textEdit_tag.setText(msg)

    def _update_roles(self, msg):
        self.lineEdit_role.setText(msg)

    def _update_works(self, msg):
        self.lineEdit_works.setText(msg)

    def _update_authors(self, msg):
        self.lineEdit_author.setText(msg)

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
            if item.id:
                self.__db_helper.delete(item.id)
            FileHelper.del_file(item.full_path)
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
        image_sql_list, image_file_list = self.__db_helper.search_by_filter(json.loads(sql_where))
        if len(image_sql_list) > 0:
            self._cache.clear()
            self.__image_model.set_images(image_sql_list, image_file_list)
            self.listView.setFocus()
            self.listView.scrollToTop()
        self.__config.add_config_key('history', 'sqlWhere', self.lineEdit_sql_where.text())

    def __choose_export(self):
        th = threading.Thread(target=self.__export_images, daemon=True)
        th.start()

    def __export_images(self):
        dir_path = self.lineEdit_export_dir.text()
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        if not os.path.isdir(dir_path):
            return

        for i in range(self.__image_model.rowCount()):
            image = self.__image_model.get_item(i)
            if not image.id:
                continue
            image_sql = self.__image_model.get_database_item(image.id)
            if not os.path.exists(image_sql.full_path()):
                continue

            try:
                new_filename = None
                if image_sql.type == 2:
                    new_filename = f"{image_sql.works}_{image_sql.roles}_{image_sql.series}_{image_sql.author_str()}"
                if image_sql.type == 3:
                    new_filename = f"{image_sql.works}_{image_sql.series}_{image_sql.author_str()}"
                FileHelper.copyfile_without_override(image_sql.full_path(), dir_path, new_filename)
            except Exception as e:
                print(e)

            msg = f"[{i + 1}/{self.__image_model.rowCount()}] {image.name} 复制成功！"
            self._signal_update_status.emit(msg)

    def _on_check_box_delete_repeat_click(self):
        print(f'是否删除重复：{self.checkBox_delete_repeat.isChecked()}')
        self.__image_model.delete_repeat = self.checkBox_delete_repeat.isChecked()

    # region 重写 Qt 控件方法
    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        # 键盘快捷键事件
        if event.key() == Qt.Key.Key_R and QApplication.keyboardModifiers() == Qt.KeyboardModifier.ControlModifier:
            self.__classify()
            self.listView.setFocus()
        if event.key() == Qt.Key.Key_E and QApplication.keyboardModifiers() == Qt.KeyboardModifier.ControlModifier:
            self.comboBox_level.setFocus()
        if event.key() == Qt.Key.Key_W and QApplication.keyboardModifiers() == Qt.KeyboardModifier.ControlModifier:
            self.lineEdit_works.setText("")
        # if event.key() == Qt.Key.Key_Delete:
        #     self.__del_select_rows()

    def key_press_delegate(self, event: QtGui.QKeyEvent):
        level_index = None
        if event.key() == Qt.Key.Key_1:
            level_index = 1
        if event.key() == Qt.Key.Key_2:
            level_index = 2
        if event.key() == Qt.Key.Key_3:
            level_index = 3
        if event.key() == Qt.Key.Key_4:
            level_index = 4
        if event.key() == Qt.Key.Key_5:
            level_index = 5
        if event.key() == Qt.Key.Key_6:
            level_index = 6
        if event.key() == Qt.Key.Key_7:
            level_index = 7
        if event.key() == Qt.Key.Key_8:
            level_index = 8
        if event.key() == Qt.Key.Key_9:
            level_index = 9
        if event.key() == Qt.Key.Key_0:
            level_index = 10

        if level_index and self.__level_model.rowCount() >= level_index:
            self.comboBox_level.setCurrentIndex(level_index - 1)
            return True

        if event.key() == Qt.Key.Key_R:
            self.__classify()
            return True
        if event.key() == Qt.Key.Key_E:
            self.lineEdit_role.setFocus()
            return True
        if event.key() == Qt.Key.Key_C:
            self.lineEdit_works.setText("")
            self.lineEdit_role.setText("")
            self.lineEdit_series.setText("")
            if self.lineEdit_source.text() == 'yande':
                self.lineEdit_author.setText("")
            return True
        if event.key() == Qt.Key.Key_D:
            self.__del_select_rows()
            return True
        if event.key() == Qt.Key.Key_W:
            current_index = self.listView.currentIndex()
            if current_index.row() > 0:
                self.listView.setCurrentIndex(self.__image_model.index(current_index.row() - 1, current_index.column()))
            return True
        if event.key() == Qt.Key.Key_S:
            current_index = self.listView.currentIndex()
            if current_index.row() < self.__image_model.rowCount() - 1:
                self.listView.setCurrentIndex(self.__image_model.index(current_index.row() + 1, current_index.column()))
            return True
        if event.key() == Qt.Key.Key_J:
            cur_index = self.comboBox_level.currentIndex()
            if cur_index > 0:
                self.comboBox_level.setCurrentIndex(cur_index - 1)
            return True
        if event.key() == Qt.Key.Key_K:
            cur_index = self.comboBox_level.currentIndex()
            if cur_index < self.__level_model.rowCount() - 1:
                self.comboBox_level.setCurrentIndex(cur_index + 1)
            return True
        return False

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:
        # 设置允许接收
        e.accept()

    def dropEvent(self, e: QtGui.QDropEvent) -> None:
        # 接收文件夹和文件以刷新图片列表
        self._cache.clear()
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
        # 关闭时保存自动填充作品列表的配置文件
        rect = self.geometry()
        rect_info = f'{rect.left()},{rect.top()},{rect.width()},{rect.height()}'
        self.__config.add_config_key('history', 'rect', rect_info)
        self._pool.shutdown()

    # endregion

    # region 预加载图片

    _cache = {}
    _pool = ThreadPoolExecutor(max_workers=5)
    _caching_paths = []

    def _preload_img(self, path, index):
        pixmap, width, height = ImageHelper.get_image_from_file(path, self.graphicsView.width(),
                                                                self.graphicsView.height())
        size = FileHelper.get_file_size_in_mb(path)
        create_time = FileHelper.get_create_time(path)
        img = PreloadImage(index, pixmap, width, height, size, create_time)
        self._cache[path] = img
        self._caching_paths.remove(path)
        print(f"预加载成功：{index}, {path}")

    def __preload(self):
        count = 10
        while True:
            try:
                index = self.listView.currentIndex().row()
                remove_key = []
                for key, img in self._cache.items():
                    if abs(img.index - index) > count * 2:
                        remove_key.append(key)
                for key in remove_key:
                    print(f'删除过期预缓存：{self._cache[key].index}, {key}')
                    del self._cache[key]
                last_info = self.__image_model.get_item(index + count)
                if not last_info or last_info.full_path in self._cache:
                    time.sleep(1)
                    continue
                print(f'开始预加载')
                time.sleep(1)
                offset = 1
                while True:
                    if offset > count:
                        break
                    pre_index = index + offset
                    info = self.__image_model.get_item(pre_index)
                    if not info:
                        print("找不到信息")
                        offset += 1
                        continue
                    full_path = info.full_path
                    # if not info.id:
                    #     exist_img = self.__db_helper.search_by_md5(FileHelper.get_md5(info.full_path))
                    # else:
                    #     exist_img = None
                    # if exist_img:
                    #     info = ImageHelper.analyze_image_info(full_path, check_size=False)
                    #     for tag_name in info.tags:
                    #         tag = self.__db_helper.find_or_create_tag(tag_name, TagSource(info.source))
                    #         if tag.children:
                    #             exist_img.tags += tag.children
                    #         else:
                    #             exist_img.tags.append(tag.id())
                    #     self.__db_helper.update_image(exist_img)
                    #     self.__image_model.delete_item(pre_index)
                    #     FileHelper.del_file(full_path)
                    #     print(f'{pre_index} 已经存在, 删除, {info.full_path}')
                    #     continue
                    if full_path in self._cache or full_path in self._caching_paths:
                        offset += 1
                        print(f'{pre_index} 已经有缓存了, {full_path}')
                        continue
                    self._pool.submit(self._preload_img, full_path, pre_index)
                    self._caching_paths.append(full_path)
                    offset += 1
                    # print(f'开始预加载: {pre_index}, {full_path}')
                time.sleep(1)
            except Exception as e:
                print(f"预加载失败：{e}")
                time.sleep(1)

    # @timeit
    def __get_image(self, index, path):
        # 优先从队列中获取
        if path in self._cache:
            pre = self._cache[path]
            print(f"从预载中读取 {path}")
            self.lineEdit_width.setText(str(pre.width))
            self.lineEdit_height.setText(str(pre.height))
            self.lineEdit_size.setText(f"{pre.size} MB")
            self.dateTimeEdit_file_create.setDateTime(pre.create_time)
            # del self._cache[path]
            return pre.pixmap, True
        print(f"从文件中读取 {index}")
        image, width, height = ImageHelper.get_image_from_file(path, self.graphicsView.width(),
                                                               self.graphicsView.height())
        self.lineEdit_width.setText(str(width))
        self.lineEdit_height.setText(str(height))
        self.lineEdit_size.setText(f"{FileHelper.get_file_size_in_mb(path)} MB")
        self.dateTimeEdit_file_create.setDateTime(FileHelper.get_create_time(path))
        return image, False

    # endregion

    def show_status_message(self, message):
        self.statusbar.showMessage(message)

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
        self._signal_handle_error.emit(error_str)
