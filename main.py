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

import db_helper
from controller.main import MyMain

if __name__ == '__main__':
    app = QApplication(sys.argv)
    try:
        db_helper.init()
    except Exception as e:
        print(f"Error [{e.args[0]}]: {e.args[1]}")
    myWin = MyMain()
    myWin.show()
    sys.exit(app.exec_())
