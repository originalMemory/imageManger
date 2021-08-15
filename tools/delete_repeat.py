#!/user/bin/env python
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : delete_repeat
@author  : illusion
@desc    :
@create  : 2021-01-16 22:08:18
"""

import os
import re
import shutil
import time

from helper.db_helper import DBHelper
from helper.file_helper import FileHelper

db_helper = DBHelper(None)


def check_repeat(dir_path, depth):
    print(f"解析{depth}层文件夹 - {dir_path}")
    names = os.listdir(dir_path)
    count = len(names)
    i = 0
    repeat_count = 0
    for name in names:
        i += 1
        print(f"解析文件[{i}/{count}] {dir_path}/{name}")
        path = os.path.join(dir_path, name)
        if os.path.isdir(path):
            repeat_count += check_repeat(path, depth + 1)
            continue
        if not path.endswith("png") and not path.endswith("jpg"):
            continue
        md5 = FileHelper.get_md5(path)
        image = db_helper.search_by_md5(md5)
        if image:
            print(f"文件重复，删除")
            os.remove(path)
            repeat_count += 1
        time.sleep(1)
    if repeat_count == count:
        print(f"文件夹重复")
        # os.rmdir(dir_path)
        return 1
    else:
        return 0


def delete_repeat_dir(base_dir, check_dir):
    base_names = os.listdir(base_dir)
    remove_size_and_count_info_in_names(base_names)
    check_names = os.listdir(check_dir)
    for check_name in check_names:
        print(f'检查文件夹: {check_name}')
        series_name = extract_series_name(check_name)
        if series_name in base_names:
            print('存在重复，删除')
            shutil.rmtree(os.path.join(check_dir, check_name))


def remove_size_and_count_info_in_names(dir_names):
    for i in range(len(dir_names)):
        name = dir_names[i]
        new_name = extract_series_name(name)
        if name != new_name:
            print(f'oldName: {name}, newName: {new_name}')
        dir_names[i] = new_name


def extract_series_name(name):
    return re.sub(r'\[.+\]', '', name).strip()


def remove_author_and_no_info(dir_path):
    dir_names = os.listdir(dir_path)
    for name in dir_names:
        # 去除'-'前面的呢称
        try:
            i1 = name.index('-')
        except ValueError as error:
            i1 = -1
        new_name = name[i1 + 1:]
        # 去除数字编号
        new_name = re.sub(r'NO\.\d+', '', new_name).strip()
        print(f'{name} -> {new_name}')
        new_path = os.path.join(dir_path, new_name)
        # 为"[]"左侧添加空格
        if '[' in name and ' [' not in name:
            name = name.replace('[', ' [')
        os.rename(os.path.join(dir_path, name), new_path)


if __name__ == '__main__':
    # remove_author_and_no_info(r'C:\下载\第四资源站\Azami')
    # delete_repeat_dir(r'G:/收藏/写真/有其他Cos作品/Azami', r'C:\下载\第四资源站\Azami')
# remove_size_and_count_info_in_names(['2021元旦限定魅魔私房[40P1V-272MB]  '])
# base_dir = r"C:\下载\第四资源站\235"
    check_repeat(r'C:\下载\22雨波解压密码：shenshisucai.com', 0)
