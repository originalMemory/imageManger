#!/user/bin/env python
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : tray_start
@author  : wuhoubo
@desc    : 
@create  : 2019/12/15 17:35:40
@update  :
"""
import sys

from PyQt6.QtWidgets import QApplication

from tray.controller.tray_setting import TraySetting

if __name__ == '__main__':
    app = QApplication(sys.argv)
    try:
        myWin = TraySetting()
        sys.exit(app.exec())
    except Exception as e:
        print(e)
