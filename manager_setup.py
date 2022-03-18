#!/user/bin/env python
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : setup
@author  : wuhoubo
@desc    : 
@create  : 2019/12/29 14:48:19
@update  :
"""
import sys
from cx_Freeze import setup, Executable

base = None
if sys.platform == "win32":
    base = "Win32GUI"

product_name = "图片管理程序"
target_name = "ImageManager.exe"
product_desc = "自用图片管理程序"

build_exe_options = {
    # 包含外围的ini、jpg文件，以及data目录下所有文件，以上所有的文件路径都是相对于cxsetup.py的路径。
    "include_files": ["record.ini", "works.txt", "role.txt"],
    # "packages": ["os"],  # 包含用到的包
    # "includes": ["PIL"],
    # "excludes": ["tkinter"],  # 提出wx里tkinter包
    "path": sys.path  # 指定上述的寻找路径
}

executables = [
    Executable('manager.py', base=base)
]

setup(name="imageManager",
      version="1.0",
      description=product_desc,
      options={"build_exe": build_exe_options},
      executables=executables)
