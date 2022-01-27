#!/user/bin/env python
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : main
@author  : wuhoubo
@desc    :
@create  : 2021/11/13 15:57:59
@update  :
"""
import os

from PIL import Image, ImageFile

from helper.db_helper import DBHelper
from helper.file_helper import FileHelper
from helper.image_helper import ImageHelper
from model.data import MyImage

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None


def analysis_and_rename_file(dir_path, prefix):
    for root, dirs, files in os.walk(dir_path):
        length = len(files)
        for i in range(length):
            file = files[i]
            file_path = os.path.join(root, file)
            print(f'[{i}/{length}] {file_path}')
            update_image(file_path, prefix)


db_helper = DBHelper(None)


def update_image(file_path, prefix):
    info = ImageHelper.analyze_image_info(file_path)
    source = info.source
    if source == 'pixiv':
        sub_str = f'_{info.tags}'
    elif source in ['yande', 'konachan']:
        if '00000' in info.relative_path:
            sub_str = f'{info.tags}_00000'
        elif '_00' in info.relative_path:
            sub_str = f'{info.tags}_00'
        else:
            sub_str = f'{info.tags}'
    else:
        sub_str = ''
    new_path = file_path.replace(sub_str, '')
    if file_path == new_path:
        print('未匹配或已经优化过文件名，直接跳过')
        return
    try:
        if not os.path.exists(new_path):
            os.rename(file_path, new_path)
    except Exception as e:
        print(f"重命名失败：{e}")
        return
    md5 = FileHelper.get_md5(new_path)
    old = db_helper.search_by_md5(md5)
    if not old:
        print('没有历史数据，跳过')
        return
    new_path = new_path.replace('\\', '/')
    image = MyImage(id=old.id, desc=info.desc, author=info.author, type=old.type, level=old.type,
                    tags=info.tags, works=old.works, role=old.role, source=info.source, width=old.width,
                    height=old.height, size=old.size, relative_path=new_path.replace(prefix, ''), md5=md5,
                    file_create_time=FileHelper.get_create_time_str(new_path), series=old.series,
                    uploader=info.uploader, sequence=old.sequence)
    db_helper.update_image(image)


def rename_png2jpg(dir_path):
    for root, dirs, files in os.walk(dir_path):
        length = len(files)
        for i in range(length):
            file = files[i]
            file_path = os.path.join(root, file)
            print(f'[{i}/{length}] {file_path}')
            extension = FileHelper.get_file_extension(file_path)
            if extension != '.png':
                continue
            new_path = file_path.replace('.png', '.jpg')
            os.rename(file_path, new_path)


def get_file_paths(dir_path):
    paths = []
    img_extension = ['jpg', 'jpeg', 'bmp', 'png']
    # img_extension = ['png']
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if file.lower().split('.')[-1] in img_extension:
                paths.append([root, os.path.join(root, file)])
    return paths


def compress(source_dir, target_dir):
    paths = get_file_paths(source_dir)
    n = len(paths)
    total_percent = 0
    for i in range(n):
        path = os.path.join(paths[i][1])
        img = Image.open(path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        filename = path.split('/')[-1].split('.')[0]
        target_sub_dir = os.path.join(target_dir, paths[i][0].replace(source_dir, ''))
        new_path = os.path.join(target_sub_dir, filename + '.jpg')
        # if os.path.exists(new_path):
        #     continue
        no = 1
        while os.path.exists(new_path):
            new_path = os.path.join(target_sub_dir, f'{filename}_{no:0>2d}.jpg')
            print(f'有重复，重命名为：{new_path}')
            no += 1
        if not os.path.exists(target_sub_dir):
            print(f'创建文件夹{target_sub_dir}')
            os.makedirs(target_sub_dir)
        img.save(new_path, quality=90)
        old_size = FileHelper.get_file_size_in_mb(path)
        new_size = FileHelper.get_file_size_in_mb(new_path)
        sub = old_size - new_size
        percent = round(new_size * 100 / old_size, 2)
        total_percent += percent
        print(f'[{i}/{n}]压缩比例 {percent:.2f}%, 减小大小 {round(sub / old_size, 2):.2f} MB, {path.replace(source_dir, "")}')
    print(f'总压缩比：{round(total_percent / n, 2):.2f}%')


if __name__ == '__main__':
    analysis_and_rename_file(r'Z:\图片\yande\64', 'Z:/')
    # compress('/Volumes/ex/待测试/壁纸/横/', '/Volumes/ex/压缩壁纸/横2/')
    # rename_png2jpg(r'E:\下载\第四资源站\楚楚子 png待功能完善')
