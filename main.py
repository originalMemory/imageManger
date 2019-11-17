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

from PyQt5.QtWidgets import QApplication

from controller.main import MyMain

if __name__ == '__main__':
    app = QApplication(sys.argv)
    try:
        myWin = MyMain()
        myWin.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(e)
