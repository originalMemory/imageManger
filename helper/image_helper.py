#!/user/bin/env python
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : image_helper
@author  : illusion
@desc    : 图片处理帮助类，将对图片的处理抽离出来
@create  : 2020-08-01 10:10:06
"""
import os
import re

from PIL import Image
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImageReader, QImage

from helper.db_helper import DBHelper
from helper.file_helper import FileHelper
from model.data import MyImage


class ImageHelper:
    @staticmethod
    def get_image_from_file(path, expect_width, expect_height):
        """
        从路径读取图片文件
        :param path: 图片路径
        :param expect_width: 期望展示的宽
        :param expect_height: 期望展示的高
        :return: qtImage，宽，高
        """
        # 使用 QImageReader 加载图片以避免直播使用 QImage 导致因扩展名加载失败
        reader = QImageReader(path)
        reader.setDecideFormatFromContent(True)
        if not reader.canRead():
            print(f'加载图片失败： {reader.errorString()}')
            return None, 0, 0
        qim = QImage()
        if not reader.read(qim):
            print(f'加载图片失败： {reader.errorString()}')
            return None, 0, 0
        width = qim.width()
        height = qim.height()
        x_scale = expect_width / float(width)
        y_scale = expect_height / float(height)
        if x_scale < y_scale:
            qim = qim.scaledToWidth(expect_width, Qt.SmoothTransformation)
        else:
            qim = qim.scaledToHeight(expect_height, Qt.SmoothTransformation)
        pixmap = QtGui.QPixmap.fromImage(qim)
        return pixmap, width, height

    @staticmethod
    def get_image_width_and_height(image_path):
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

    @staticmethod
    def analyze_image_info(file_path):
        """
        根据文件路径分析图片信息
        :param file_path: 图片路径
        :return:
        """
        info = MyImage()
        info.filename = os.path.basename(file_path)
        info.size = FileHelper.get_file_size_in_mb(file_path)
        info.create_time = FileHelper.get_create_time(file_path)
        filename = os.path.basename(file_path)
        yande = 'yande'
        pixiv = 'pixiv'
        konachan = 'konachan'
        # cosplay = '/Cosplay/'
        filter_list = [yande, pixiv, konachan]
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
            return info

        if yande in filename:
            info.source = 'yande'
            info.tags, info.uploader = ImageHelper.analyze_yande(filename)
        elif pixiv in filename:
            info.source = 'pixiv'
            # [ % site_ % id_ % author] % desc_ % tag <! < _ % imgp[5]
            match = re.search(r"pixiv.*?_\d*?_(?P<author>.+?)](?P<desc>.+?)_(?P<tags>.+?)_00", filename)
            if match:
                author = match.group('author')
                info.author = author.replace("「", '').replace('」的插画', '').replace('」的漫画', '')
                info.desc = match.group('desc')
                tags = match.group('tags')
                tags.replace(';', ',')
                info.tags = tags
            else:
                match = re.search(r"pixiv.*?_\d*?_(?P<author>.+?)](?P<tags>.+?)_", filename)
                if match:
                    author = match.group('author')
                    author = author.replace("「", '').replace('」的插画', '').replace('」的漫画', '')
                    info.author = author
                    info.tags = match.group('tags')
        elif konachan in filename:
            info.source = konachan
            # [konachan_241354_RyuZU]blindfold breast_grab breasts demiroid elbow_gloves
            match = re.search(r"konachan_\d*?_(?P<uploader>.+?)](?P<tags>.+?)\.", filename)
            if match:
                info.uploader = match.group('uploader')
                info.tags = match.group('tags').replace("_00000", "")

        return info

    @staticmethod
    def analyze_yande(filename):
        # [yande_492889_Mr_GT]asian_clothes cleavage clouble tianxia_00
        match = re.search(r"yande.*?_\d*?_(?P<uploader>.+?)](?P<tags>.+?)_00", filename)
        if match:
            uploader = match.group('uploader')
            tags = match.group('tags')
            tags = tags.replace("_00", "")
            return tags, uploader
        else:
            # yande.re 505 hook neko seifuku shimazu_wakana _summer wallpaper.jpg
            match = re.search(r"yande(.re)? (?P<id>.+?) (?P<tags>.+?)\.(?:jpg|png|gif|jpeg|bmp)", filename)
            if match:
                tags = match.group('tags')
                return tags, None
            else:
                return None, None

    @staticmethod
    def refresh_recode_info(error_handler, message_handler):
        """
        刷新数据库里文件信息，包括宽高和md5
        :return:
        """
        page = 0
        pagesize = 500
        db_helper = DBHelper(error_handler)
        count = db_helper.get_table_count(f"select count(*) from myacg.image;")
        while True:
            image_list = db_helper.get_images(page, pagesize)

            if len(image_list) == 0:
                break
            for index, image in enumerate(image_list):
                print(f"[{page * pagesize + index}/{count}] 更新数据中")
                if "?" in image.path:
                    continue
                if not os.path.exists(image.path):
                    db_helper.delete(image.id)
                    continue
                # if not image.series:
                #     image.series = ""
                # if not image.uploader:
                #     image.uploader = ""
                # image.width, image.height = ImageHelper.get_image_width_and_height(image.path)
                # image.md5 = FileHelper.get_md5(image.path)
                # db_helper.update_image(image)
            page += 1

    @staticmethod
    def get_sized_image(image_path, *, size=None, width=None, height=None):
        """
        读取指定大小的图片，采用填充模式缩放
        :param image_path: 图片路径
        :param size: (宽，高)
        :param width: 宽
        :param height: 高
        :return: 图片
        """
        image = Image.open(image_path)
        if not image:
            return
        if size and len(size) == 2:
            width = size[0]
            height = size[1]
        if not width:
            width = image.size[0]
        if not height:
            height = image.size[1]
        image_width, image_height = image.size
        target_scale = width / height
        new_width = int(image_height * target_scale)
        if new_width < image_width:
            width_crop = (image_width - new_width) / 2
            image = image.crop((width_crop, 0, image_width - width_crop, image_height))
        else:
            new_height = image_width // target_scale
            height_crop = (image_height - new_height) / 2
            image = image.crop((0, height_crop, image_width, image_height - height_crop))
        return image.resize((width, height), Image.ANTIALIAS)

    @staticmethod
    def merge_horizontal_img(images, start_y_list, save_name):
        """
        横向合并图片
        :param images: 图片列表
        :param start_y_list: 竖直偏移列表
        :param save_name: 保存名称
        :return:
        """
        widths, heights = zip(*(i.size for i in images))

        total_width = sum(widths)
        max_height = max(heights)

        new_im = Image.new('RGB', (total_width, max_height))

        start_x = 0
        for i in range(len(images)):
            image = images[i]
            start_y = start_y_list[i]
            new_im.paste(image, (start_x, start_y))
            start_x += image.size[0]
        new_im.save(save_name, quality=100, subsampling=0)
