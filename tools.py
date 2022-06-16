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
import re
import shutil

import pymongo
from PIL import Image

from helper.db_helper import DBHelper, DBExecuteType
from helper.image_helper import ImageHelper
from helper.tag_helper import TagHelper
from model.data import *

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None


def analysis_and_rename_file(dir_path, path_prefix, handler, num_prefix=None):
    filenames = os.listdir(dir_path)
    length = len(filenames)
    if not filenames and num_prefix:
        print(f'[{num_prefix}]无文件')
    for i, filename in enumerate(filenames):
        if '$RECYCLE' in filename:
            continue
        filepath = os.path.join(dir_path, filename)
        if os.path.isdir(filepath):
            prefix = f'{i}/{length}'
            if num_prefix:
                prefix = f'{num_prefix}-{prefix}'
            analysis_and_rename_file(filepath, path_prefix, handler, prefix)
            continue
        index_str = f'{i}/{length}'
        if num_prefix:
            index_str = f'{num_prefix}-{index_str}'
        print(f'[{index_str}] {filepath}')
        handler(filepath, path_prefix)


db_helper = DBHelper(None)


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
        infos = [MyImage.from_dict(x) for x in queries]
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
        md5 = FileHelper.get_md5(file_path)
        info = db_helper.search_by_md5(md5)
        if info:
            db_helper.update_path(info.id, relative_path)
    if not info:
        with open('notRecord.log', 'a+', encoding='utf-8') as f:
            f.write(f'{file_path}\n')
        print('文件不存在')


def check_exist(file_path, prefix):
    if not ImageHelper.is_image(file_path):
        return
    md5 = FileHelper.get_md5(file_path)
    info = db_helper.search_by_md5(md5)
    if info:
        print('已存在，删除该文件')
        os.remove(file_path)


def update_path(filepath, prefix):
    if '$RECYCLE' in filepath:
        return
    if not ImageHelper.is_image(filepath):
        return
    relative_path = filepath.replace('\\', '/').replace(prefix, '')
    info = db_helper.search_by_file_path(relative_path)
    if info:
        return
    md5 = FileHelper.get_md5(filepath)
    info = db_helper.search_by_md5(md5)
    if info:
        db_helper.update_path(info.id, relative_path)


def split_by_works(filepath, prefix):
    if not ImageHelper.is_image(filepath):
        return
    relative_path = filepath.replace('\\', '/').replace(prefix, '')
    # relative_path = filepath.replace('\\', '/')
    info = db_helper.search_by_file_path(relative_path)
    if not info:
        print('无信息，跳过')
        return
    if not info.works:
        print('无作品，跳过')
        return
    base = 'Z:/图片/'
    max_work = ''
    for work in info.works:
        if len(max_work) < len(work):
            max_work = work
    work_dir = re.sub(r'[<>/\\|:"?]', '_', max_work)
    dir_path = os.path.join(base, work_dir)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    filename = os.path.basename(filepath)
    new_filepath = os.path.join(dir_path, filename)
    shutil.move(filepath, new_filepath)
    db_helper.update_path(info.id, new_filepath.replace('\\', '/').replace('Z:/', ''))
    print(f'归档到作品 {max_work} 内，文件名 {filename}')


def check_no_split_works(filepath, prefix):
    if not ImageHelper.is_image(filepath):
        return
    relative_path = filepath.replace('\\', '/').replace(prefix, '')
    info = db_helper.search_by_file_path(relative_path)
    if not info:
        with open('notRecord.log', 'a+', encoding='utf-8') as f:
            f.write(f'{filepath}\n')
        print('无信息，跳过')
        return
    if not info.works:
        dir_name = filepath.split('\\')[-2].replace('_', '/')
        query = db_helper.execute(f"select id from myacg.tran_dest where name='{dir_name}'", DBExecuteType.FetchOne)
        if query:
            print("拆分但丢失作品信息")
            with open('notWorks.log', 'a+', encoding='utf-8') as f:
                f.write(f'{info.id}, {filepath}\n')
        return
    if info.works in filepath:
        return
    with open('notSplitWorks.log', 'a+', encoding='utf-8') as f:
        print("未按作品拆分")
        f.write(f'{info.id}, {info.works}, {filepath}\n')


if __name__ == '__main__':
    # analysis_and_rename_file(r'F:/图片/yandegg', 'Z:/', split_by_works)
    TagHelper().get_not_tran_yande_tag()
