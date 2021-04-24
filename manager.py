#!/user/bin/env python
# coding=utf-8
"""
@project : ImageManager
@ide     : PyCharm
@file    : main
@author  : wuhoubo
@desc    : 
@create  : 2019/6/2 23:56:45
@update  :
"""
import sys
import PyQt5.sip

from PyQt5.QtWidgets import QApplication

from manager.controller.manager import ImageManager

if __name__ == '__main__':
    app = QApplication(sys.argv)
    try:
        myWin = ImageManager()
        myWin.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(e)
