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
        print(f"解析文件[{i}/{count}] {name}")
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
    if repeat_count == count:
        print(f"文件夹重复，删除")
        # os.rmdir(dir_path)
        return 1
    else:
        return 0


base_dir = ""
check_repeat(base_dir, 0)

