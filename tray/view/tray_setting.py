# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'tray_setting.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_TraySetting(object):
    def setupUi(self, TraySetting):
        TraySetting.setObjectName("TraySetting")
        TraySetting.resize(684, 383)
        self.label = QtWidgets.QLabel(TraySetting)
        self.label.setGeometry(QtCore.QRect(30, 40, 91, 20))
        self.label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label.setObjectName("label")
        self.textEdit_sqlWhere = QtWidgets.QTextEdit(TraySetting)
        self.textEdit_sqlWhere.setGeometry(QtCore.QRect(120, 40, 501, 181))
        self.textEdit_sqlWhere.setObjectName("textEdit_sqlWhere")
        self.label_2 = QtWidgets.QLabel(TraySetting)
        self.label_2.setGeometry(QtCore.QRect(20, 258, 91, 20))
        self.label_2.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_2.setObjectName("label_2")
        self.lineEdit_min = QtWidgets.QLineEdit(TraySetting)
        self.lineEdit_min.setGeometry(QtCore.QRect(120, 258, 81, 20))
        self.lineEdit_min.setObjectName("lineEdit_min")
        self.label_3 = QtWidgets.QLabel(TraySetting)
        self.label_3.setGeometry(QtCore.QRect(210, 258, 91, 20))
        self.label_3.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_3.setObjectName("label_3")
        self.pushButton_save = QtWidgets.QPushButton(TraySetting)
        self.pushButton_save.setGeometry(QtCore.QRect(220, 310, 75, 23))
        self.pushButton_save.setObjectName("pushButton_save")
        self.pushButton_cancel = QtWidgets.QPushButton(TraySetting)
        self.pushButton_cancel.setGeometry(QtCore.QRect(390, 310, 75, 23))
        self.pushButton_cancel.setObjectName("pushButton_cancel")

        self.retranslateUi(TraySetting)
        QtCore.QMetaObject.connectSlotsByName(TraySetting)

    def retranslateUi(self, TraySetting):
        _translate = QtCore.QCoreApplication.translate
        TraySetting.setWindowTitle(_translate("TraySetting", "壁纸切换设置"))
        self.label.setText(_translate("TraySetting", "筛选语句："))
        self.label_2.setText(_translate("TraySetting", "间隔时间："))
        self.label_3.setText(_translate("TraySetting", "分钟"))
        self.pushButton_save.setText(_translate("TraySetting", "保存"))
        self.pushButton_cancel.setText(_translate("TraySetting", "取消"))
