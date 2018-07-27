# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'SlideRunner_ui.ui'
#
# Created by: PyQt5 UI code generator 5.10
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets
from SlideRunner.gui.zoomSlider import *

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setWindowModality(QtCore.Qt.NonModal)
        MainWindow.resize(905, 821)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        MainWindow.setFocusPolicy(QtCore.Qt.StrongFocus)
        MainWindow.setAcceptDrops(True)
        MainWindow.setDockOptions(QtWidgets.QMainWindow.AllowNestedDocks|QtWidgets.QMainWindow.AllowTabbedDocks|QtWidgets.QMainWindow.AnimatedDocks)
        MainWindow.setUnifiedTitleAndToolBarOnMac(True)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.MainImage = QtWidgets.QLabel(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.MainImage.sizePolicy().hasHeightForWidth())
        self.MainImage.setSizePolicy(sizePolicy)
        self.MainImage.setMinimumSize(QtCore.QSize(400, 400))
        self.MainImage.setLineWidth(0)
        self.MainImage.setAlignment(QtCore.Qt.AlignCenter)
        self.MainImage.setObjectName("MainImage")
        self.verticalLayout.addWidget(self.MainImage)
        self.horizontalScrollBar = QtWidgets.QScrollBar(self.centralwidget)
        self.horizontalScrollBar.setMaximum(999)
        self.horizontalScrollBar.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalScrollBar.setObjectName("horizontalScrollBar")
        self.verticalLayout.addWidget(self.horizontalScrollBar)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.zoomSlider = zoomSlider()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.zoomSlider.sizePolicy().hasHeightForWidth())
        self.zoomSlider.setSizePolicy(sizePolicy)
        self.verticalLayout.addWidget(self.zoomSlider)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.horizontalLayout.addLayout(self.verticalLayout)
        self.verticalScrollBar = QtWidgets.QScrollBar(self.centralwidget)
        self.verticalScrollBar.setOrientation(QtCore.Qt.Vertical)
        self.verticalScrollBar.setObjectName("verticalScrollBar")
        self.horizontalLayout.addWidget(self.verticalScrollBar)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.horizontalLayout.addItem(spacerItem)
        self.sidebarLayout = QtWidgets.QVBoxLayout()
        self.sidebarLayout.setObjectName("sidebarLayout")
        self.OverviewLabel = QtWidgets.QLabel(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.OverviewLabel.sizePolicy().hasHeightForWidth())
        self.OverviewLabel.setSizePolicy(sizePolicy)
        self.OverviewLabel.setMinimumSize(QtCore.QSize(200, 200))
        self.OverviewLabel.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.OverviewLabel.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.OverviewLabel.setObjectName("OverviewLabel")
        self.sidebarLayout.addWidget(self.OverviewLabel)
        self.filenameLabel = QtWidgets.QLabel(self.centralwidget)
        self.filenameLabel.setObjectName("filenameLabel")
        self.sidebarLayout.addWidget(self.filenameLabel)
        self.databaseLabel = QtWidgets.QLabel(self.centralwidget)
        self.databaseLabel.setObjectName("databaseLabel")
        self.sidebarLayout.addWidget(self.databaseLabel)
        self.horizontalLayout.addLayout(self.sidebarLayout)
        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 905, 22))
        self.menubar.setObjectName("menubar")
        self.menuDatabase = QtWidgets.QMenu(self.menubar)
        self.menuDatabase.setObjectName("menuDatabase")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuAnnotation = QtWidgets.QMenu(self.menubar)
        self.menuAnnotation.setObjectName("menuAnnotation")
        self.menuHelp = QtWidgets.QMenu(self.menubar)
        self.menuHelp.setObjectName("menuHelp")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.action_Open = QtWidgets.QAction(MainWindow)
        self.action_Open.setObjectName("action_Open")
        self.actionOpen = QtWidgets.QAction(MainWindow)
        self.actionOpen.setObjectName("actionOpen")
        self.action_Close = QtWidgets.QAction(MainWindow)
        self.action_Close.setObjectName("action_Close")
        self.action_Quit = QtWidgets.QAction(MainWindow)
        self.action_Quit.setObjectName("action_Quit")
        self.actionOpen_custom = QtWidgets.QAction(MainWindow)
        self.actionOpen_custom.setObjectName("actionOpen_custom")
        self.actionMode = QtWidgets.QAction(MainWindow)
        self.actionMode.setObjectName("actionMode")
        self.actionAdd_annotator = QtWidgets.QAction(MainWindow)
        self.actionAdd_annotator.setEnabled(False)
        self.actionAdd_annotator.setObjectName("actionAdd_annotator")
        self.actionAdd_cell_class = QtWidgets.QAction(MainWindow)
        self.actionAdd_cell_class.setEnabled(False)
        self.actionAdd_cell_class.setObjectName("actionAdd_cell_class")
        self.actionCreate_new = QtWidgets.QAction(MainWindow)
        self.actionCreate_new.setObjectName("actionCreate_new")
        self.actionAbout = QtWidgets.QAction(MainWindow)
        self.actionAbout.setObjectName("actionAbout")
        self.menuDatabase.addAction(self.actionCreate_new)
        self.menuDatabase.addAction(self.action_Open)
        self.menuDatabase.addAction(self.actionOpen_custom)
        self.menuDatabase.addSeparator()
        self.menuDatabase.addAction(self.actionAdd_annotator)
        self.menuDatabase.addAction(self.actionAdd_cell_class)
        self.menuFile.addAction(self.actionOpen)
        self.menuFile.addAction(self.action_Close)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.action_Quit)
        self.menuHelp.addAction(self.actionAbout)
        self.menubar.addAction(self.menuDatabase.menuAction())
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuAnnotation.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "SlideRunner"))
        self.MainImage.setText(_translate("MainWindow", "No Slide Open"))
        self.OverviewLabel.setText(_translate("MainWindow", "TextLabel"))
        self.filenameLabel.setText(_translate("MainWindow", "TextLabel"))
        self.databaseLabel.setText(_translate("MainWindow", "No database opened."))
        self.menuDatabase.setTitle(_translate("MainWindow", "Database"))
        self.menuFile.setTitle(_translate("MainWindow", "Slide"))
        self.menuAnnotation.setTitle(_translate("MainWindow", "Annotation"))
        self.menuHelp.setTitle(_translate("MainWindow", "Help"))
        self.action_Open.setText(_translate("MainWindow", "&Open default"))
        self.actionOpen.setText(_translate("MainWindow", "Open"))
        self.action_Close.setText(_translate("MainWindow", "&Close"))
        self.action_Quit.setText(_translate("MainWindow", "&Quit"))
        self.actionOpen_custom.setText(_translate("MainWindow", "Open custom"))
        self.actionMode.setText(_translate("MainWindow", "Mode"))
        self.actionAdd_annotator.setText(_translate("MainWindow", "Add annotator"))
        self.actionAdd_cell_class.setText(_translate("MainWindow", "Add annotation class"))
        self.actionCreate_new.setText(_translate("MainWindow", "Create new"))
        self.actionAbout.setText(_translate("MainWindow", "About"))

