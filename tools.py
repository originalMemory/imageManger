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

from PIL import Image

from helper.db_helper import DBHelper, DBExecuteType
from helper.image_helper import ImageHelper
from model.data import *

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None


def analysis_and_rename_file(dir_path, prefix, handler):
    for root, dirs, files in os.walk(dir_path):
        length = len(files)
        for i in range(length):
            file = files[i]
            file_path = os.path.join(root, file)
            print(f'[{i}/{length}] {file_path}')
            handler(file_path, prefix)


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


def recheck_size(start_page):
    page_size = 500
    error_f = open('error.log', 'a+', encoding='utf-8')
    not_exist_f = open('notExist.log', 'a+', encoding='utf-8')
    count = db_helper.get_table_count("select count(*) from myacg.image;")
    while True:
        offset = (start_page - 1) * page_size
        sql = f"select * from myacg.image limit {page_size} offset {offset};"
        queries = db_helper.execute(sql, DBExecuteType.FetchAll)
        if not queries:
            print('没有数据，结束检查')
            break
        infos = [MyImage.from_mysql_dict(x) for x in queries]
        n = len(infos)
        for i in range(n):
            info = infos[i]
            print(f'[{offset + i}/{count}] {info.id}, {info.relative_path}')
            if not os.path.exists(info.path):
                not_exist_f.write(f'{info.id},{info.path}\n')
                print('图片不存在')
                db_helper.delete(info.id)
                continue
            try:
                width, height = Image.open(info.path).size
            except Exception as e:
                error_f.write(f'{info.id},{info.relative_path},{info.width},{info.height},{e}\n')
                print('尺寸读取失败')
                continue
            if not width or not height:
                error_f.write(f'{info.id},{info.relative_path},{info.width},{info.height}\n')
                print('尺寸读取失败')
                continue
            if width == info.width and height == info.height:
                continue
            print(f'宽度：{info.width} -> {width}，高度：{info.height} -> {height}')
            info.width = width
            info.height = height
            db_helper.update_image(info)
        start_page += 1
    error_f.close()
    not_exist_f.close()


def check_no_record_image(file_path, prefix):
    if not ImageHelper.is_image(file_path):
        return
    relative_path = file_path.replace('\\', '/').replace(prefix, '')
    info = db_helper.search_by_file_path(relative_path)
    if not info:
        with open('notRecord.log', 'a+', encoding='utf-8') as f:
            f.write(f'{file_path}\n')
        print('文件不存在')


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


def check_exist(file_path, prefix):
    if not ImageHelper.is_image(file_path):
        return
    md5 = FileHelper.get_md5(file_path)
    info = db_helper.search_by_md5(md5)
    if info:
        print('已存在，删除该文件')
        os.remove(file_path)


if __name__ == '__main__':
    # analysis_and_rename_file(r'Z:\写真', 'Z:/', check_no_record_image)
    rename_png2jpg(r'E:\下载\第四资源站\楚楚子 png待功能完善')
