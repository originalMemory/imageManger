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
import json
import os
import queue
import threading
import time
from enum import unique, Enum

from PyQt6 import QtWidgets, QtGui
from PyQt6.QtCore import QModelIndex, Qt, pyqtSignal
from PyQt6.QtWidgets import QMainWindow, QApplication, QCompleter, QMessageBox
from bson import ObjectId
from win32comext.shell import shell, shellcon

from helper.config_helper import ConfigHelper
from helper.db_helper import DBHelper
from helper.extension import timeit
from helper.file_helper import FileHelper
from helper.image_helper import ImageHelper
from helper.tag_helper import TagHelper
from manager.view.manager import Ui_Manager
from model.ImageFileListModel import ImageFileListModel
from model.data import ImageFile, PreloadImage, MyImage, TranDest, TagType
from model.my_list_model import MyBaseListModel


@unique
class VIEW(Enum):
    LIST = 1
    GRAPHIC = 2


class ImageManager(QMainWindow, Ui_Manager):
    _signal_update_image_id = pyqtSignal(QModelIndex, ImageFile)
    _signal_update_status = pyqtSignal(str)
    _signal_update_tags = pyqtSignal(str)
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
        self.pushButton_clean.clicked.connect(self.__clean_not_exist_images)
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
        self.__works_completer_filename = 'works.txt'
        self.__works_completer_set = self._read_completer_file(self.__works_completer_filename)
        works_completer = self._create_completer(self.__works_completer_set)
        self.lineEdit_works.setCompleter(works_completer)
        self.lineEdit_works.editingFinished.connect(self.__add_works_complete)
        self.__role_completer_filename = 'role.txt'
        self.__role_completer_set = self._read_completer_file(self.__role_completer_filename)
        role_completer = self._create_completer(self.__role_completer_set)
        self.lineEdit_role.setCompleter(role_completer)
        self.lineEdit_role.editingFinished.connect(self.__add_role_complete)
        self.checkBox_delete_repeat.setChecked(True)
        self.__image_model.delete_repeat = True

        # Image.MAX_IMAGE_PIXELS = 1882320000
        self.listView.setFocus()

        # 预加载图片
        threading.Thread(target=self.__preload, daemon=True).start()
        threading.Thread(target=self._insert_or_update, daemon=True).start()

    @staticmethod
    def _read_completer_file(filename):
        if not os.path.exists(filename):
            f = open(filename, 'w', encoding='utf-8')
            f.close()
        with open(filename, 'r+', encoding='utf-8') as f:
            return set(list(map(lambda x: x.replace("\n", "").replace("\r", ""), f.readlines())))

    @staticmethod
    def _create_completer(completer_list):
        completer = QCompleter(completer_list)
        completer.setCompletionMode(QCompleter.CompletionMode.InlineCompletion)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        return completer

    def _is_anime(self):
        type = self.__type_model.get_item(self.comboBox_type.currentIndex()).id
        return type == 1

    def __add_works_complete(self):
        """
        添加自动补全作品
        :return:
        """
        if not self._is_anime():
            return
        cur_completion = self.lineEdit_works.completer().currentCompletion()
        if cur_completion == "":
            self.__works_completer_set.add(self.lineEdit_works.text())
            completer = QCompleter(self.__works_completer_set)
            completer.setCompletionMode(QCompleter.CompletionMode.InlineCompletion)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            self.lineEdit_works.setCompleter(completer)
            print(self.__works_completer_set)

    def __add_role_complete(self):
        """
        添加自动补全角色
        :return:
        """
        if not self._is_anime():
            return
        cur_completion = self.lineEdit_role.completer().currentCompletion()
        if cur_completion == "":
            self.__role_completer_set.add(self.lineEdit_role.text())
            completer = QCompleter(self.__role_completer_set)
            completer.setCompletionMode(QCompleter.CompletionMode.InlineCompletion)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            self.lineEdit_role.setCompleter(completer)
            print(self.__role_completer_set)

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

    @timeit
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
            QMessageBox.information(self, "提示", str(e), QMessageBox.StandardButton.Ok)
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
        info = self.__db_helper.search_by_file_path(path.replace(FileHelper.get_path_prefix(), ''))
        if not info:
            # 清空二次元图上一次自动识别的结果
            type = self.__type_model.get_item(self.comboBox_type.currentIndex())
            if type.id == 1 and self.lineEdit_source.text() in ['pixiv', 'yande']:
                self.lineEdit_role.clear()
                self.lineEdit_works.clear()
                self.lineEdit_series.clear()
                if self.lineEdit_source.text() == 'yande':
                    self.lineEdit_author.clear()

            # 分析图片信息
            self.lineEdit_path.setText(path)
            info = ImageHelper.analyze_image_info(path)
            self.lineEdit_size.setText(f"{info.size} MB")
            self.dateTimeEdit_file_create.setDateTime(info.create_time)
            if info.desc:
                self.lineEdit_desc.setText(info.desc)
            if info.tags:
                self.textEdit_tag.setText(','.join(info.tags))
            if info.source:
                self.lineEdit_source.setText(info.source)
            if info.uploader:
                self.lineEdit_uploader.setText(info.uploader)
            if info.author:
                self.lineEdit_author.setText(info.author)
            if not self.lineEdit_sequence.text():
                self.lineEdit_sequence.setText('0')
            if info.sequence:
                self.lineEdit_sequence.setText(str(info.sequence))
            threading.Thread(target=self._refresh_tran_tags, args=(info.tags, False,), daemon=True).start()
            return
        # 显示已有记录
        self.lineEdit_desc.setText(info.desc)
        self.lineEdit_path.setText(info.path)
        self.lineEdit_source.setText(info.source)
        self.lineEdit_author.setText(info.author)
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

    def _refresh_tran_tags(self, tags, keep_role):
        if not tags:
            return
        tran_tags = set()
        if keep_role and self.lineEdit_role.text():
            roles = set(self.lineEdit_role.text().split(','))
        else:
            roles = set()
        works = set()
        for tag in tags:
            if isinstance(tag, ObjectId):
                query = self.__db_helper.search_one('tran_dest', {'_id': tag})
                if query:
                    dest = TranDest.from_dict(query)
                    tran_tags.add(dest.name)
                    if dest.type == TagType.Role:
                        roles.add(dest.name)
                    elif dest.type == TagType.Works:
                        works.add(dest.name)
                    elif dest.type == TagType.Author and not self.lineEdit_author.text():
                        self.lineEdit_author.setText(dest.name)
                    continue
            query = self.__db_helper.search_one('tran_source', {'name': tag})
            if query:
                query = self.__db_helper.search_all('tran_dest', {'_id': {'$in': query['dest_ids']}})
            if query:
                for x in query:
                    dest = TranDest.from_dict(x)
                    # 暂时没有翻译的保留原文
                    if not dest.name:
                        tran_tags.add(tag)
                        continue
                    tran_tags.add(dest.name)
                    if dest.type == TagType.Role:
                        roles.add(dest.name)
                    elif dest.type == TagType.Works:
                        works.add(dest.name)
                    elif dest.type == TagType.Author and not self.lineEdit_author.text():
                        self.lineEdit_author.setText(dest.name)
            else:
                tran_tags.add(tag)
        if tran_tags:
            text = ','.join(tran_tags)
            # self.textEdit_tag.setText(text)
            self._signal_update_tags.emit(text)
            # self.textEdit_tag.setText(text)
            pass
        if roles and not self.lineEdit_role.text():
            self.lineEdit_role.setText(','.join(roles))
        if works and not self.lineEdit_works.text():
            self.lineEdit_works.setText(','.join(works))

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
        else:
            self.listView.clearFocus()
        self.listView.setFocus()

    def _prepare_classify(self, select_rows):
        index = self.comboBox_type.currentIndex()
        type = self.__type_model.get_item(index).id
        index = self.comboBox_level.currentIndex()
        level = self.__level_model.get_item(index).id
        desc = self.lineEdit_desc.text()
        author = self.lineEdit_author.text()
        tags = self.textEdit_tag.toPlainText()
        works = self.lineEdit_works.text()
        role = self.lineEdit_role.text()
        source = self.lineEdit_source.text()
        sequence = int(self.lineEdit_sequence.text())
        series = self.lineEdit_series.text()
        uploader = self.lineEdit_uploader.text()
        for row in select_rows:
            item = self.__image_model.get_item(row.row())
            path = item.full_path
            relative_path = path.replace(FileHelper.get_path_prefix(), '')
            # width 和 height 放到编程里更新
            image = MyImage(id=item.id, desc=desc, author=author, type=type, level=level, tags=tags.split(','), works=works.split(','),
                            roles=role.split(','), source=source, width=0, height=0, size=FileHelper.get_file_size_in_mb(path),
                            path=path, relative_path=relative_path, md5=FileHelper.get_md5(path),
                            file_create_time=FileHelper.get_create_time(path), series=series, uploader=uploader,
                            sequence=sequence)
            if image.id:
                # 批量更新时，保持原来的描述、作者、等级、标签、作品
                old_image = self.__image_model.get_database_item(image.id)
                if old_image and len(select_rows) > 1:
                    image.desc = old_image.desc
                    image.author = old_image.author
                    image.level = old_image.level
                    image.tags = old_image.tags
                    image.works = old_image.works
            self._change_tasks.put((row, image))

    _change_tasks = queue.Queue()

    def _insert_or_update(self):
        while True:
            row, image = self._change_tasks.get()
            item = self.__image_model.get_item(row.row())
            path = image.path
            need_refresh_item = False
            width, height = ImageHelper.get_image_width_and_height(path)
            image.width = width
            image.height = height
            source = image.source
            new_item = item
            source_tags = ImageHelper.get_source_tags(image.path)
            if source in ['pixiv', 'yande', 'kona'] and source_tags and source_tags in path:
                if source == 'pixiv':
                    sub_str = f'_{source_tags}'
                else:
                    sub_str = f'{source_tags}_00000'
                new_path = path.replace(sub_str, '')
                if new_path != path:
                    try:
                        if os.path.exists(new_path):
                            os.remove(path)
                        else:
                            os.rename(path, new_path)
                        path = new_path
                        need_refresh_item = True
                    except Exception as e:
                        print(f"重命名失败：{e}")
                        continue
                new_item = ImageFile(id=image.id, name=item.name.replace(sub_str, ''), full_path=path)
            if not os.path.exists(path):
                print(f'文件不存在：{path}')
                continue
            for i in range(len(image.tags)):
                tag = image.tags[i]
                query = self.__db_helper.search_one('tran_dest', {'name': tag})
                if not query:
                    continue
                image.tags[i] = query['_id']
            if '' in image.tags:
                image.tags.remove('')
            if '' in image.roles:
                image.roles.remove('')
            if '' in image.works:
                image.works.remove('')
            relative_path = path.replace(FileHelper.get_path_prefix(), '')
            image.relative_path = relative_path
            image.path = path
            if not image.id:
                self.__db_helper.insert_image(image)
                image_id = self.__db_helper.get_id_by_path(relative_path)
                need_refresh_item = True
                new_item.id = image_id
            else:
                self.__db_helper.update_image(image)
                message = f"{item.name} 更新完成！"
                self.statusbar.showMessage(f"[{row.row() + 1}/{self.__image_model.rowCount()}] {message}")
            if need_refresh_item:
                self._signal_update_image_id.emit(row, new_item)

    def _handle_error(self, msg):
        QMessageBox.information(self, "提示", msg, QMessageBox.StandardButton.Ok)

    def _update_image_id(self, index: QModelIndex, image_file: ImageFile):
        self.__image_model.update_item(index, image_file)

    def _update_status(self, msg):
        self.statusbar.showMessage(msg)

    def _update_tags(self, msg):
        self.textEdit_tag.setText(msg)

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
            # os.remove(item.full_path)
            shell.SHFileOperation((0, shellcon.FO_DELETE, item.full_path, None,
                                   shellcon.FOF_SILENT | shellcon.FOF_ALLOWUNDO | shellcon.FOF_NOCONFIRMATION, None,
                                   None))  # 删除文件到回收站
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
            if image.id:
                image_sql = self.__image_model.get_database_item(image.id)
                if not os.path.exists(image_sql.path):
                    continue

                try:
                    new_filename = None
                    if image_sql.type == 2:
                        new_filename = f"{image_sql.works}_{image_sql.roles}_{image_sql.series}_{image_sql.author}"
                    if image_sql.type == 3:
                        new_filename = f"{image_sql.works}_{image_sql.series}_{image_sql.author}"
                    FileHelper.copyfile_without_override(image_sql.path, dir_path, new_filename)
                except Exception as e:
                    print(e)
            else:
                FileHelper.copyfile_without_override(image.full_path, dir_path)

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
        self._save_str_list_to_file(self.__works_completer_set, self.__works_completer_filename)
        self._save_str_list_to_file(self.__role_completer_set, self.__role_completer_filename)
        rect = self.geometry()
        rect_info = f'{rect.left()},{rect.top()},{rect.width()},{rect.height()}'
        self.__config.add_config_key('history', 'rect', rect_info)

    @staticmethod
    def _save_str_list_to_file(str_list, filename):
        with open(filename, 'w+', encoding='utf-8') as f:
            f.writelines(list(map(lambda x: x + "\n", str_list)))

    # endregion

    # region 预加载图片
    __preload_count = 5
    __preload_image_queue = queue.Queue(__preload_count)

    def __preload(self):
        while True:
            try:
                index = self.listView.currentIndex().row()
                preload_index = index + self.__preload_image_queue.qsize() + 1
                image_file = self.__image_model.get_item(preload_index)
                if not image_file:
                    time.sleep(1)
                    continue

                full_path = image_file.full_path
                pixmap, width, height = ImageHelper.get_image_from_file(full_path, self.graphicsView.width(),
                                                                        self.graphicsView.height())
                self.__preload_image_queue.put((PreloadImage(full_path, pixmap), width, height))
                print(f"预加载成功：{full_path}")
            except Exception as e:
                print(e)
                print(f"预加载失败：{full_path}")
                time.sleep(1)

    @timeit
    def __get_image(self, path):
        # 优先从队列中获取
        while self.__preload_image_queue.qsize() > 0:
            print(f"准备从预载中读取，{self.__preload_image_queue.qsize()}")
            image, width, height = self.__preload_image_queue.get(timeout=0.1)
            if isinstance(image, PreloadImage) and image.full_path == path:
                print("从预载中读取")
                self.lineEdit_width.setText(str(width))
                self.lineEdit_height.setText(str(height))
                return image.pixmap, True
        print("从文件中读取")
        self.__preload_image_queue.queue.clear()
        image, width, height = ImageHelper.get_image_from_file(path, self.graphicsView.width(),
                                                               self.graphicsView.height())
        self.lineEdit_width.setText(str(width))
        self.lineEdit_height.setText(str(height))
        return image, False

    # endregion

    def __clean_not_exist_images(self):
        """
        清理不存在的图片
        :return:
        """
        th = threading.Thread(
            target=ImageHelper.refresh_recode_info,
            args=(self.db_error_handler, self.show_status_message,),
            daemon=True
        )
        th.start()

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
