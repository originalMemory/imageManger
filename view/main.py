# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'main.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Main(object):
    def setupUi(self, Main):
        Main.setObjectName("Main")
        Main.resize(1674, 1110)
        Main.setAcceptDrops(True)
        self.centralwidget = QtWidgets.QWidget(Main)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.widget = QtWidgets.QWidget(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.widget.setMinimumSize(QtCore.QSize(0, 170))
        self.widget.setMaximumSize(QtCore.QSize(16777215, 170))
        self.widget.setObjectName("widget")
        self.pushButton_classify = QtWidgets.QPushButton(self.widget)
        self.pushButton_classify.setGeometry(QtCore.QRect(1180, 20, 112, 34))
        self.pushButton_classify.setObjectName("pushButton_classify")
        self.comboBox_type = QtWidgets.QComboBox(self.widget)
        self.comboBox_type.setGeometry(QtCore.QRect(383, 10, 111, 31))
        self.comboBox_type.setObjectName("comboBox_type")
        self.lineEdit_desc = QtWidgets.QLineEdit(self.widget)
        self.lineEdit_desc.setGeometry(QtCore.QRect(70, 15, 251, 25))
        self.lineEdit_desc.setObjectName("lineEdit_desc")
        self.label = QtWidgets.QLabel(self.widget)
        self.label.setGeometry(QtCore.QRect(4, 19, 61, 20))
        self.label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(self.widget)
        self.label_2.setGeometry(QtCore.QRect(4, 60, 61, 20))
        self.label_2.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_2.setObjectName("label_2")
        self.lineEdit_tag = QtWidgets.QLineEdit(self.widget)
        self.lineEdit_tag.setGeometry(QtCore.QRect(70, 56, 251, 25))
        self.lineEdit_tag.setObjectName("lineEdit_tag")
        self.comboBox_level = QtWidgets.QComboBox(self.widget)
        self.comboBox_level.setGeometry(QtCore.QRect(383, 53, 111, 31))
        self.comboBox_level.setObjectName("comboBox_level")
        self.label_3 = QtWidgets.QLabel(self.widget)
        self.label_3.setGeometry(QtCore.QRect(320, 17, 61, 20))
        self.label_3.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_3.setObjectName("label_3")
        self.label_4 = QtWidgets.QLabel(self.widget)
        self.label_4.setGeometry(QtCore.QRect(320, 58, 61, 20))
        self.label_4.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_4.setObjectName("label_4")
        self.label_5 = QtWidgets.QLabel(self.widget)
        self.label_5.setGeometry(QtCore.QRect(318, 134, 61, 20))
        self.label_5.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_5.setObjectName("label_5")
        self.label_6 = QtWidgets.QLabel(self.widget)
        self.label_6.setGeometry(QtCore.QRect(515, 54, 61, 20))
        self.label_6.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_6.setObjectName("label_6")
        self.lineEdit_source = QtWidgets.QLineEdit(self.widget)
        self.lineEdit_source.setGeometry(QtCore.QRect(581, 50, 100, 25))
        self.lineEdit_source.setObjectName("lineEdit_source")
        self.lineEdit_path = QtWidgets.QLineEdit(self.widget)
        self.lineEdit_path.setEnabled(True)
        self.lineEdit_path.setGeometry(QtCore.QRect(70, 96, 251, 25))
        self.lineEdit_path.setReadOnly(True)
        self.lineEdit_path.setObjectName("lineEdit_path")
        self.label_7 = QtWidgets.QLabel(self.widget)
        self.label_7.setGeometry(QtCore.QRect(4, 100, 61, 20))
        self.label_7.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_7.setObjectName("label_7")
        self.dateTimeEdit_create = QtWidgets.QDateTimeEdit(self.widget)
        self.dateTimeEdit_create.setGeometry(QtCore.QRect(983, 47, 150, 25))
        self.dateTimeEdit_create.setFrame(True)
        self.dateTimeEdit_create.setReadOnly(True)
        self.dateTimeEdit_create.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.dateTimeEdit_create.setAccelerated(False)
        self.dateTimeEdit_create.setKeyboardTracking(True)
        self.dateTimeEdit_create.setProperty("showGroupSeparator", False)
        self.dateTimeEdit_create.setDateTime(QtCore.QDateTime(QtCore.QDate(2000, 1, 1), QtCore.QTime(3, 4, 5)))
        self.dateTimeEdit_create.setCalendarPopup(True)
        self.dateTimeEdit_create.setObjectName("dateTimeEdit_create")
        self.label_9 = QtWidgets.QLabel(self.widget)
        self.label_9.setGeometry(QtCore.QRect(890, 50, 91, 20))
        self.label_9.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_9.setObjectName("label_9")
        self.dateTimeEdit_update = QtWidgets.QDateTimeEdit(self.widget)
        self.dateTimeEdit_update.setGeometry(QtCore.QRect(983, 87, 150, 25))
        self.dateTimeEdit_update.setFrame(True)
        self.dateTimeEdit_update.setReadOnly(True)
        self.dateTimeEdit_update.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.dateTimeEdit_update.setAccelerated(False)
        self.dateTimeEdit_update.setKeyboardTracking(True)
        self.dateTimeEdit_update.setProperty("showGroupSeparator", False)
        self.dateTimeEdit_update.setDateTime(QtCore.QDateTime(QtCore.QDate(2000, 1, 1), QtCore.QTime(3, 4, 5)))
        self.dateTimeEdit_update.setCalendarPopup(True)
        self.dateTimeEdit_update.setObjectName("dateTimeEdit_update")
        self.label_10 = QtWidgets.QLabel(self.widget)
        self.label_10.setGeometry(QtCore.QRect(890, 90, 91, 20))
        self.label_10.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_10.setObjectName("label_10")
        self.pushButton_move = QtWidgets.QPushButton(self.widget)
        self.pushButton_move.setGeometry(QtCore.QRect(1180, 70, 112, 34))
        self.pushButton_move.setObjectName("pushButton_move")
        self.lineEdit_role = QtWidgets.QLineEdit(self.widget)
        self.lineEdit_role.setGeometry(QtCore.QRect(383, 95, 111, 25))
        self.lineEdit_role.setObjectName("lineEdit_role")
        self.label_11 = QtWidgets.QLabel(self.widget)
        self.label_11.setGeometry(QtCore.QRect(322, 97, 61, 20))
        self.label_11.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_11.setObjectName("label_11")
        self.label_8 = QtWidgets.QLabel(self.widget)
        self.label_8.setGeometry(QtCore.QRect(495, 96, 81, 20))
        self.label_8.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_8.setObjectName("label_8")
        self.lineEdit_uploader = QtWidgets.QLineEdit(self.widget)
        self.lineEdit_uploader.setGeometry(QtCore.QRect(581, 92, 100, 25))
        self.lineEdit_uploader.setObjectName("lineEdit_uploader")
        self.lineEdit_width = QtWidgets.QLineEdit(self.widget)
        self.lineEdit_width.setGeometry(QtCore.QRect(760, 50, 100, 25))
        self.lineEdit_width.setReadOnly(True)
        self.lineEdit_width.setObjectName("lineEdit_width")
        self.label_12 = QtWidgets.QLabel(self.widget)
        self.label_12.setGeometry(QtCore.QRect(694, 54, 61, 20))
        self.label_12.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_12.setObjectName("label_12")
        self.lineEdit_height = QtWidgets.QLineEdit(self.widget)
        self.lineEdit_height.setGeometry(QtCore.QRect(760, 90, 100, 25))
        self.lineEdit_height.setReadOnly(True)
        self.lineEdit_height.setObjectName("lineEdit_height")
        self.label_13 = QtWidgets.QLabel(self.widget)
        self.label_13.setGeometry(QtCore.QRect(694, 94, 61, 20))
        self.label_13.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_13.setObjectName("label_13")
        self.label_14 = QtWidgets.QLabel(self.widget)
        self.label_14.setGeometry(QtCore.QRect(890, 13, 91, 20))
        self.label_14.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_14.setObjectName("label_14")
        self.dateTimeEdit_file_create = QtWidgets.QDateTimeEdit(self.widget)
        self.dateTimeEdit_file_create.setGeometry(QtCore.QRect(983, 10, 150, 25))
        self.dateTimeEdit_file_create.setFrame(True)
        self.dateTimeEdit_file_create.setReadOnly(True)
        self.dateTimeEdit_file_create.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.dateTimeEdit_file_create.setAccelerated(False)
        self.dateTimeEdit_file_create.setKeyboardTracking(True)
        self.dateTimeEdit_file_create.setProperty("showGroupSeparator", False)
        self.dateTimeEdit_file_create.setDateTime(QtCore.QDateTime(QtCore.QDate(2000, 1, 1), QtCore.QTime(3, 4, 5)))
        self.dateTimeEdit_file_create.setCalendarPopup(True)
        self.dateTimeEdit_file_create.setObjectName("dateTimeEdit_file_create")
        self.label_15 = QtWidgets.QLabel(self.widget)
        self.label_15.setGeometry(QtCore.QRect(694, 14, 61, 20))
        self.label_15.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_15.setObjectName("label_15")
        self.lineEdit_size = QtWidgets.QLineEdit(self.widget)
        self.lineEdit_size.setGeometry(QtCore.QRect(760, 10, 100, 25))
        self.lineEdit_size.setReadOnly(True)
        self.lineEdit_size.setObjectName("lineEdit_size")
        self.label_16 = QtWidgets.QLabel(self.widget)
        self.label_16.setGeometry(QtCore.QRect(515, 134, 61, 20))
        self.label_16.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_16.setObjectName("label_16")
        self.lineEdit_author = QtWidgets.QLineEdit(self.widget)
        self.lineEdit_author.setGeometry(QtCore.QRect(581, 130, 100, 25))
        self.lineEdit_author.setObjectName("lineEdit_author")
        self.lineEdit_series = QtWidgets.QLineEdit(self.widget)
        self.lineEdit_series.setGeometry(QtCore.QRect(581, 10, 100, 25))
        self.lineEdit_series.setObjectName("lineEdit_series")
        self.label_17 = QtWidgets.QLabel(self.widget)
        self.label_17.setGeometry(QtCore.QRect(515, 14, 61, 20))
        self.label_17.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_17.setObjectName("label_17")
        self.lineEdit_works = QtWidgets.QLineEdit(self.widget)
        self.lineEdit_works.setGeometry(QtCore.QRect(382, 132, 111, 25))
        self.lineEdit_works.setObjectName("lineEdit_works")
        self.verticalLayout.addWidget(self.widget)
        self.splitter = QtWidgets.QSplitter(self.centralwidget)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.listView = QtWidgets.QListView(self.splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.listView.sizePolicy().hasHeightForWidth())
        self.listView.setSizePolicy(sizePolicy)
        self.listView.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.listView.setObjectName("listView")
        self.graphicsView = QtWidgets.QGraphicsView(self.splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(3)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.graphicsView.sizePolicy().hasHeightForWidth())
        self.graphicsView.setSizePolicy(sizePolicy)
        self.graphicsView.setMinimumSize(QtCore.QSize(0, 0))
        self.graphicsView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.graphicsView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.graphicsView.setObjectName("graphicsView")
        self.verticalLayout.addWidget(self.splitter)
        Main.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(Main)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1674, 30))
        self.menubar.setObjectName("menubar")
        self.menu = QtWidgets.QMenu(self.menubar)
        self.menu.setObjectName("menu")
        Main.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(Main)
        self.statusbar.setObjectName("statusbar")
        Main.setStatusBar(self.statusbar)
        self.actionOpen = QtWidgets.QAction(Main)
        self.actionOpen.setObjectName("actionOpen")
        self.menu.addAction(self.actionOpen)
        self.menubar.addAction(self.menu.menuAction())

        self.retranslateUi(Main)
        QtCore.QMetaObject.connectSlotsByName(Main)

    def retranslateUi(self, Main):
        _translate = QtCore.QCoreApplication.translate
        Main.setWindowTitle(_translate("Main", "图片整理程序"))
        self.pushButton_classify.setText(_translate("Main", "分类"))
        self.label.setText(_translate("Main", "描述："))
        self.label_2.setText(_translate("Main", "标签："))
        self.label_3.setText(_translate("Main", "类型："))
        self.label_4.setText(_translate("Main", "等级："))
        self.label_5.setText(_translate("Main", "作品："))
        self.label_6.setText(_translate("Main", "来源："))
        self.label_7.setText(_translate("Main", "路径："))
        self.label_9.setText(_translate("Main", "创建时间："))
        self.label_10.setText(_translate("Main", "更新时间："))
        self.pushButton_move.setText(_translate("Main", "移动"))
        self.label_11.setText(_translate("Main", "角色："))
        self.label_8.setText(_translate("Main", "上传者："))
        self.label_12.setText(_translate("Main", "宽度："))
        self.label_13.setText(_translate("Main", "高度："))
        self.label_14.setText(_translate("Main", "文件创建时间："))
        self.label_15.setText(_translate("Main", "大小："))
        self.label_16.setText(_translate("Main", "作者："))
        self.label_17.setText(_translate("Main", "系列："))
        self.menu.setTitle(_translate("Main", "文件"))
        self.actionOpen.setText(_translate("Main", "打开"))
        self.actionOpen.setShortcut(_translate("Main", "Ctrl+O"))

