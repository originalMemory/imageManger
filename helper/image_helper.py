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
import random
import re
import textwrap

from PIL import Image, ImageQt, ImageDraw, ImageFont, ImageFile
from PyQt6 import QtGui
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImageReader
from colorthief import ColorThief

from helper.db_helper import DBHelper
from helper.file_helper import FileHelper
from model.data import MyImage

ImageFile.MAX_IMAGE_PIXELS = None


def get_two_different_numbers():
    attempts = 0
    while attempts < 3:
        # 生成两个随机数
        num1 = random.randint(0, 2)
        num2 = random.randint(0, 2)

        # 如果两个数不相等，则直接返回
        if num1 != num2:
            return num1, num2

        # 如果两个数相等，重试
        attempts += 1

    # 重试 3 次后仍然相等，返回两个相等的数
    return num1, num2


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
        try:
            qim = ImageQt.ImageQt(path)
        except Exception as e:
            print(f'获取图片宽高失败 {e}')
            return None, 0, 0
        if not qim:
            return None, 0, 0
        width = qim.width()
        height = qim.height()

        if not width or not height:
            return None, 0, 0
        x_scale = expect_width / float(width)
        y_scale = expect_height / float(height)
        if x_scale < y_scale:
            qim = qim.scaledToWidth(expect_width, Qt.TransformationMode.SmoothTransformation)
        else:
            qim = qim.scaledToHeight(expect_height, Qt.TransformationMode.SmoothTransformation)
        pixmap = QtGui.QPixmap.fromImage(qim)
        return pixmap, width, height

    @staticmethod
    def _get_image_by_qimage_reader(path):
        reader = QImageReader(path)
        reader.setDecideFormatFromContent(True)
        qim = None
        can_read = reader.canRead()
        if not can_read:
            print(f'加载图片失败： {reader.errorString()}')
            qim = QtGui.QImage(path)
        elif not reader.read(qim):
            print(f'加载图片失败： {reader.errorString()}')
            qim = QtGui.QImage(path)
        return qim

    @staticmethod
    def get_image_width_and_height(image_path):
        """
        获取图片的宽高
        :param image_path: 图片路径
        :return:
        """
        try:
            width, height = Image.open(image_path).size
            return width, height
        except Exception as e:
            print(f'获取图片宽高失败 {e}')
            return 0, 0

    @staticmethod
    def analyze_image_info(file_path, check_size=True):
        """
        根据文件路径分析图片信息
        :param file_path: 图片路径
        :return:
        """
        info = MyImage()
        filename = os.path.basename(file_path)
        info.filename = filename
        if os.path.exists(file_path) and check_size:
            info.size = FileHelper.get_file_size_in_mb(file_path)
            info.create_time = FileHelper.get_create_time(file_path)

        # MetArt.com_22.12.04.Florens.Presenting.Florens/metart_presenting-florens_florens_high_0001.jpg
        match = re.search(r'/MetArt.com_\d+\.\d+\.\d+\.(?P<name>.+?)/', file_path)
        if match and 'cover' not in filename:
            all_name = match.group('name')
            works = filename.replace('metart_', '').replace('-', '.').split('_')[0]
            lower = all_name.lower()
            works_index = lower.find(works)
            info.source = 'MertArt'
            info.works = [all_name[works_index:]]
            info.authors = [all_name[0:works_index - 1]]
            return info

        re_strs = [
            # r'/(?P<authors>.+?)/(?P<source>\w+?) .+ - (?P<works>.+?) \(',
            # FemJoy 2019-09-15 Carolina K - Naked in the trees
            r'/(?P<source>[\w-]+?) \d+-\d+-\d+ (?P<authors>.+?) - (?P<works>.+?)/',
            # Carisha\Femjoy 2011-05-15 - Hello (x38) 2667x4000
            # r'/(?P<authors>.+?) - (?P<works>.+?)\[',
            # r'/\d+-\d+-\d+ - (?P<source>.+?) - (?P<authors>.+?) - (?P<works>.+?)/',
            # r'/\d+-\d+-\d+ - (?P<authors>.+?) - (?P<works>.+?)/'
        ]
        for s in re_strs:
            match = re.search(s, file_path)
            if match:
                groupdict = match.groupdict()
                if 'source' in groupdict:
                    info.source = groupdict['source']
                info.works = [groupdict['works'].strip()]
                authors = groupdict['authors'].split('/')[-1]
                if ',' in authors:
                    authors = authors.split(',')
                if '&' in authors:
                    authors = authors.split(',')
                if isinstance(authors, str):
                    authors = [authors]
                info.authors = [x.strip() for x in authors]
                return info

        match = re.search(r"\[(?P<source>(konachan|yande|donmai))_(?P<no>\d+?)_(?P<uploader>.+?)](?P<tags>.+?)\.",
                          filename)
        if match:
            info.source = match.group('source')
            info.uploader = match.group('uploader')
            info.tags = match.group('tags').replace("_00000", "").split(' ')
            info.sequence = int(match.group('no'))
            return info
        # [ % site_ % id_ % author] % desc_ % tag <! < _ % imgp[5]
        match = re.search(r"pixiv_(?P<no>\d+?)_(?P<author>.+?)](?P<desc>.+?)_(?P<tags>.+?)\.(jpg|png|jpeg|bmp)",
                          filename)
        if match:
            info.source = 'pixiv'
            author = match.group('author').replace("「", '').replace('」的插画', '').replace('」的漫画', '')
            info.authors = [author]
            info.desc = match.group('desc')
            tags_str = match.group('tags').strip()
            tags_str = re.sub(r'(_00\d+| {2}p[\d-]+)$', '', tags_str)
            info.tags = tags_str.split(';' if ';' in tags_str else ' ')
            info.sequence = int(match.group('no'))
        return info

    @staticmethod
    def remove_tags(filename):
        patterns = [
            r'(yande|konachan|donmai)_\d+_.+](?P<tags>.+?)\.(jpg|png|jpeg|bmp)',
            r'pixiv_\d+_.+](?P<desc>.+?)_(?P<tags>.+?)(_00| p[\d-]+)?\.(jpg|png|jpeg|bmp)'
        ]
        for pattern in patterns:
            match = re.search(pattern, filename)
            if not match:
                continue
            tags_str = match.group('tags')
            if '[pixiv_' in filename and not tags_str.isdigit():
                tags_str = '_' + re.sub(r'_00\d+$', '', tags_str)
            return filename.replace(tags_str, '')
        return filename

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
            width_crop = (image_width - new_width) // 2
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

    @staticmethod
    def random_merge_image(get_image_path, size):
        if size[0] > size[1]:
            im = ImageHelper._random_merge_horizontal_image(get_image_path, size)
        else:
            im = ImageHelper._random_merge_vertical_image(get_image_path, size)
        return im

    @staticmethod
    def _random_merge_vertical_image(get_image_path, size):
        left_hor_i, right_hor_i = get_two_different_numbers()
        sub_width = size[0] // 2
        new_im = Image.new('RGB', size)
        top_y = 0
        bottom_y = 0

        hor_images = get_image_path(2, True)
        ver_images = get_image_path(4, False)

        def get_sub_image(vertical):
            height = size[1] // 5
            if vertical:
                path = ver_images.pop()
                height *= 2
            else:
                path = hor_images.pop()
            return ImageHelper.get_sized_image(path, width=sub_width, height=height)

        for i in range(3):
            left_image = get_sub_image(i != left_hor_i)
            new_im.paste(left_image, (0, top_y))
            top_y += left_image.height
            right_image = get_sub_image(i != right_hor_i)
            new_im.paste(right_image, (sub_width, bottom_y))
            bottom_y += right_image.height
        return new_im

    @staticmethod
    def _random_merge_horizontal_image(get_image_path, size):
        top_ver_i, bottom_ver_i = get_two_different_numbers()
        sub_height = size[1] // 2
        new_im = Image.new('RGBA', size)
        top_x = 0
        bottom_x = 0

        hor_images = get_image_path(4, True)
        ver_images = get_image_path(2, False)

        def get_sub_image(horizontal):
            width = size[0] // 5
            if horizontal:
                path = hor_images.pop()
                width *= 2
            else:
                path = ver_images.pop()
            img = ImageHelper.get_sized_image(path, width=width, height=sub_height)
            img = img.convert('RGBA')
            ImageHelper._draw_text_in_img(img, FileHelper.get_relative_path(path))
            return img

        for i in range(3):
            top_image = get_sub_image(i != top_ver_i)
            new_im.paste(top_image, (top_x, 0))
            top_x += top_image.width
            bottom_image = get_sub_image(i != bottom_ver_i)
            new_im.paste(bottom_image, (bottom_x, sub_height))
            bottom_x += bottom_image.width
        return new_im

    @staticmethod
    def _draw_text_in_img(image, text):
        # 创建一个 ImageDraw 对象
        draw = ImageDraw.Draw(image)
        # 设置字体和字体大小
        font = ImageFont.truetype('msyh.ttc', size=20)
        x, y = 10, 10
        max_width = image.width - 40
        text_wrap = textwrap.wrap(text, width=max_width // font.getsize(' ')[0])
        # lines = len(text_wrap)
        # line_height = font.getsize(' ')[1]
        # 绘制阴影和文本
        # 设置文字颜色和透明度
        text_color = (255, 255, 255, 10)
        # 设置阴影颜色
        shadow_color = (0, 0, 0, 20)
        for i, line in enumerate(text_wrap):
            line_width, line_height = font.getsize(line)
            draw.text((x + 2, y + i * line_height + 2), line, font=font, fill=shadow_color)
            draw.text((x, y + i * line_height), line, font=font, fill=text_color)

    @staticmethod
    def is_image(filename):
        image_extension_list = ['.jpg', '.jpeg', '.bmp', '.png', 'gif', '.dib', '.pcp', '.dif', '.wmf', '.tif', '.tiff',
                                '.eps', '.psd', '.cdr', '.iff', '.tga', '.pcd', '.mpi', '.icon', '.ico', '.gif']
        extension = FileHelper.get_file_extension(filename).lower()
        return extension in image_extension_list

    @staticmethod
    def save_thumb(source_path, dest_path, size=500):
        img = Image.open(source_path)
        img.thumbnail((size, size))
        img.save(dest_path)
        return img.size

    @staticmethod
    def get_hex_color(path):
        rgb = ColorThief(path).get_color()
        color = '#'
        for i in rgb:
            num = int(i)
            # 将R、G、B分别转化为16进制拼接转换并大写  hex() 函数用于将10进制整数转换成16进制，以字符串形式表示
            color += str(hex(num))[-2:].replace('x', '0').upper()
        return color
