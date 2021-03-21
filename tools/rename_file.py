#!/user/bin/env python
# coding=utf-8
"""
@project : PythonEx
@ide     : PyCharm
@file    : rename_file
@author  : illusion
@desc    :
@create  : 2021-01-16 10:49:03
"""
import os, shutil


# def rename_file(dir_path, depth, is_fix_zero):
#     print(f"解析{dir_path}层文件夹 - {dir_path}")
#     names = os.listdir(dir_path)
#     count = len(names)
#     i = 0
#     for name in names:
#         i += 1
#         print(f"解析文件[{i}/{count}] {name}")
#         path = os.path.join(dir_path, name)
#         if os.path.isdir(path):
#             rename_file(path, depth + 1)
#             continue
#         else:
#             (shot_name, extension) = os.path.splitext(name)
#             if is_fix_zero:
#                 if count >= 1000:
#                     if i < 10:
#                         new_name = f"000{i}{extension}"
#                     elif i < 100:
#                         new_name = f"00{i}{extension}"
#                     elif i < 1000:
#                         new_name = f"0{i}{extension}"
#                     else:
#                         new_name = f"{i}{extension}"
#                 elif count >= 100:
#                     if i < 10:
#                         new_name = f"00{i}{extension}"
#                     elif i < 100:
#                         new_name = f"0{i}{extension}"
#                     else:
#                         new_name = f"{i}{extension}"
#                 else:
#                     if i < 10:
#                         new_name = f"0{i}{extension}"
#                     else:
#                         new_name = f"{i}{extension}"
#             else:
#                 new_name = f"{i}{extension}"
#         new_path = os.path.join(dir_path, new_name)
#         print(f"新文件名:{new_path}")
#         shutil.move(path, new_path)
#
#
# base_path = "E:\临时壁纸\\4"
# rename_file(base_path, 1, is_fix_zero=True)

from screeninfo import get_monitors

for m in get_monitors():
    print(str(m))
