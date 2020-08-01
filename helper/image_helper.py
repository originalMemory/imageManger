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

from PyQt5 import QtGui
from PyQt5.QtCore import Qt

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
        qim = QtGui.QImage(path)
        width = qim.width()
        height = qim.height()
        x_scale = expect_width / float(qim.width())
        y_scale = expect_height / float(qim.height())
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
            return info

        if yande in filename:
            info.source = 'yande'
            info.desc, info.uploader = ImageHelper.analyze_yande(filename)

        if pixiv in filename:
            info.source = 'pixiv'
            # [ % site_ % id_ % author] % desc_ % tag <! < _ % imgp[5]
            match = re.search(r"pixiv.*?_\d*?_(?P<author>.+?)](?P<desc>.+?)_(?P<tags>.+?)_", filename)
            if match:
                author = match.group('author')
                info.author = author.replace("「", '').replace('」的插画', '').replace('」的漫画', '')
                info.desc = match.group('desc')
                tags = match.group('tags')
                tags.replace(';', ',')
                info.tags = tags
            else:
                match = re.search(r"pixiv.*?_\d*?_(?P<author>.+?)](?P<desc>.+?)_", filename)
                if match:
                    author = match.group('author')
                    author = author.replace("「", '').replace('」的插画', '').replace('」的漫画', '')
                    info.author = author
                    info.desc = match.group('desc')
        return info

    @staticmethod
    def analyze_yande(filename):
        # [yande_492889_Mr_GT]asian_clothes cleavage clouble tianxia_00
        match = re.search(r"yande.*?_\d*?_(?P<uploader>.+?)](?P<desc>.+?)\.", filename)
        if match:
            uploader = match.group('uploader')
            desc = match.group('desc')
            desc = desc.replace("_00", "")
            return desc, uploader
        else:
            # yande.re 505 hook neko seifuku shimazu_wakana _summer wallpaper.jpg
            match = re.search(r"yande(.re)? (?P<id>.+?) (?P<desc>.+?)\.", filename)
            if match:
                desc = match.group('desc')
                return desc, None
            else:
                return None, None


