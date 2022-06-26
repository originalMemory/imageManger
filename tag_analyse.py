#!/user/bin/env python
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : main
@author  : wuhoubo
@desc    : 
@create  : 2022-06-25 18:07:00 周六
@update  :
"""
import sys

from PyQt6.QtWidgets import QApplication

from manager.controller.tag_analyse import TagAnalyse

if __name__ == '__main__':
    app = QApplication(sys.argv)
    try:
        myWin = TagAnalyse()
        myWin.show()
        sys.exit(app.exec())
    except Exception as e:
        print(e)
