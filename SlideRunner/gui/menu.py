"""

        This is SlideRunner - An Open Source Annotation Tool 
        for Digital Histology Slides.

         Marc Aubreville, Pattern Recognition Lab, 
         Friedrich-Alexander University Erlangen-Nuremberg 
         marc.aubreville@fau.de

        If you use this software in research, please citer our paper:
        M. Aubreville, C. Bertram, R. Klopfleisch and A. Maier:
        SlideRunner - A Tool for Massive Cell Annotations in Whole Slide Images. 
        In: Bildverarbeitung für die Medizin 2018. 
        Springer Vieweg, Berlin, Heidelberg, 2018. pp. 309-314.
"""


from functools import partial
from SlideRunner.gui.types import *
from PyQt5 import QtWidgets, QtCore
import cv2
import os

import SlideRunner.general.pluginFinder
def defineMenu(self, MainWindow, pluginList, initial=True):
        if (initial):
                self.menubar = QtWidgets.QMenuBar(MainWindow)
                self.menubar.setGeometry(QtCore.QRect(0, 0, 905, 22))
                self.menubar.setObjectName("menubar")
                self.menuDatabase = QtWidgets.QMenu(self.menubar)
                self.menuDatabase.setObjectName("menuDatabase")
                self.menuFile = QtWidgets.QMenu(self.menubar)
                self.menuFile.setObjectName("menuFile")
                self.menuAnnotation = QtWidgets.QMenu(self.menubar)
                self.menuAnnotation.setObjectName("menuAnnotation")


                self.zoomMenu = QtWidgets.QMenu(self.menubar)
                self.zoomMenu.setObjectName('zoomMenu')
                self.zoomMenu.setTitle('View')
                self.menuHelp = QtWidgets.QMenu(self.menubar)
                self.menuHelp.setObjectName("menuHelp")

                self.statusbar = QtWidgets.QStatusBar(MainWindow)
                self.statusbar.setObjectName("statusbar")
                MainWindow.setStatusBar(self.statusbar)
                self.menubar.addAction(self.menuDatabase.menuAction())
                self.menubar.addAction(self.menuFile.menuAction())
                self.menubar.addAction(self.menuAnnotation.menuAction())
                self.menubar.addAction(self.zoomMenu.menuAction())
                definePluginMenu(MainWindow,pluginList)
                self.menubar.addAction(self.menuHelp.menuAction())

        else:
                for action in self.menuFile.actions():
                        self.menuFile.removeAction(action)
                for action in self.menuDatabase.actions():
                        self.menuDatabase.removeAction(action)
                for action in self.menuAnnotation.actions():
                        self.menuAnnotation.removeAction(action)
                for action in self.menuHelp.actions():
                        self.menuHelp.removeAction(action)
        self.zoomInAction = self.zoomMenu.addAction('Zoom in')
        self.zoomInAction.setShortcut("+")
        self.zoomInAction.triggered.connect(MainWindow.zoomIn)

        self.zoomInAction = self.zoomMenu.addAction('Zoom out')
        self.zoomInAction.setShortcut("-")
        self.zoomInAction.triggered.connect(MainWindow.zoomOut)

        self.zoomInAction = self.zoomMenu.addAction('Max optical zoom')
        self.zoomInAction.setShortcut("Ctrl+M")
        self.zoomInAction.triggered.connect(MainWindow.zoomMaxoptical)
        MainWindow.setMenuBar(self.menubar)
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
        self.actionSettings = QtWidgets.QAction(MainWindow)
        self.action_setMPP = QtWidgets.QAction(MainWindow)
        self.actionSettings.setObjectName("actionSettings")
        self.actionManageDatabase = QtWidgets.QAction(MainWindow)
        self.actionManageDatabase.setText('Over&view')
        self.action_CloseDB = QtWidgets.QAction('Close')
        self.action_CloseDB.setEnabled(False)
        self.menuDatabase.addAction(self.actionCreate_new)
        self.menuDatabase.addAction(self.action_Open)
        self.menuDatabase.addAction(self.actionOpen_custom)
        self.menuDatabase.addAction(self.action_CloseDB)
        self.action_CloseDB.triggered.connect(MainWindow.closeDatabase)

        self.menuDatabase.addAction(self.actionManageDatabase)
        defineOpenRecentDatabase(MainWindow)
        self.menuDatabase.addSeparator()
        self.menuDatabase.addAction(self.actionAdd_annotator)
        self.menuDatabase.addAction(self.actionAdd_cell_class)
        if (MainWindow.settings.value('exactSupportEnabled', 0)):
                self.databaseExactMenuExport = self.menuDatabase.addAction('Export all slides to EXACT')
                self.databaseExactMenuSync = self.menuDatabase.addAction('Sync all slides with EXACT')
        self.menuFile.addAction(self.actionOpen)
        defineOpenRecent(MainWindow)
        self.menuFile.addAction(self.action_Close)
        self.menuFile.addAction(self.action_setMPP)
        self.menuFile.addSeparator()
        if (MainWindow.settings.value('exactSupportEnabled', 0)):
                self.exactMenuLinkImage = self.menuFile.addAction('Link slide to EXACT image')
                self.exactMenuSyncImage = self.menuFile.addAction('Sync slide')
                self.exactMenuImport = self.menuFile.addAction('Import slide from EXACT')
                self.exactMenuExportImage = self.menuFile.addAction('Export slide to EXACT')
                self.exactMenuSyncExpert = self.menuDatabase.addAction('Set expert used for EXACT sync')
        
        self.menuFile.addSeparator()

        self.menuFile.addAction(self.action_Quit)
        self.menuHelp.addAction(self.actionAbout)
        self.menuHelp.addAction(self.actionSettings)
        self.menuDatabase.setTitle(("Database"))
        self.menuFile.setTitle(("Slide"))
        self.action_setMPP.setText(("Set microns/pixel"))
        self.menuAnnotation.setTitle(("Annotation"))
        self.menuHelp.setTitle(("Help"))
        self.action_Open.setText(("&Open default"))
        self.actionOpen.setText(("Open"))
        self.action_Close.setText(("&Close"))
        self.action_Quit.setText(("&Quit"))
        self.actionOpen_custom.setText(("Open custom"))
        self.actionMode.setText(("Mode"))
        self.actionAdd_annotator.setText(("Add annotator"))
        self.actionAdd_cell_class.setText(("Add annotation class"))
        self.actionCreate_new.setText(("Create new"))
        self.actionAbout.setText(("About"))
        self.actionSettings.setText(("Settings"))

        self.menuItemView = self.menuAnnotation.addAction('Find by ID', MainWindow.findAnnoByID)
        self.rotate = self.menuFile.addAction('Rotate image', MainWindow.setRotate)
        self.rotate.setCheckable(True)
        rotval = MainWindow.settings.value('rotateImage', False)
        self.rotate.setChecked(rotval if not isinstance(rotval,str) else rotval.upper()=='TRUE')

        self.menuItemView = self.zoomMenu.addAction('Go to coordinate', MainWindow.goToCoordinate)
        self.saveSnapshot = self.zoomMenu.addAction('Create snapshot of current view', MainWindow.savescreenshot)

        self.saveto = self.menuDatabase.addAction('Copy To ...')
        self.saveto.setEnabled(False)
        self.saveto.triggered.connect(MainWindow.saveDBto)
        self.action_setMPP.triggered.connect(MainWindow.setMPP)
        self.actionManageDatabase.triggered.connect(MainWindow.manageDB)
        self.actionSettings.triggered.connect(MainWindow.settingsDialog)
        if (MainWindow.settings.value('exactSupportEnabled', 0)):
                self.exactMenuLinkImage.triggered.connect(MainWindow.linkSlideToExact)
                self.exactMenuImport.triggered.connect(MainWindow.downloadSlideFromExact)
                self.exactMenuSyncImage.triggered.connect(partial(MainWindow.syncWithExact, allSlides=False))
                self.exactMenuExportImage.triggered.connect(partial(MainWindow.exportToExact, allSlides=False))
                self.exactMenuSyncExpert.triggered.connect(MainWindow.setExactUser)
                self.databaseExactMenuExport.triggered.connect(partial(MainWindow.exportToExact,  allSlides=True))
                self.databaseExactMenuSync.triggered.connect(partial(MainWindow.syncWithExact, allSlides=True))

def definePluginMenu(self,pluginList):
        pluginMenu = QtWidgets.QMenu(self.ui.menubar)
        pluginMenu.setObjectName('PluginMenu')
        pluginMenu.setTitle('Plugins')
        self.ui.menubar.addAction(pluginMenu.menuAction())

        self.ui.pluginItems = list()
        for plugin in pluginList:
                plugin.instance = plugin.plugin(self.progressBarQueue)
                menuItem = pluginMenu.addAction(plugin.commonName, partial(self.togglePlugin, plugin))
                menuItem.setCheckable(True)
                menuItem.setEnabled(True)
                self.ui.pluginItems.append(menuItem)
        self.pluginList = pluginList

def updateOpenRecentSlide(self):
        lastOpenList = self.settings.value('LastSlides', type=list)
        lastOpenList.reverse()
        for action in self.openrecentactions:
                self.openrecent.removeAction(action)
        self.openrecentactions=list()
        if len(lastOpenList) > 0:
                for idx,item in enumerate(lastOpenList):
                        self.openrecentactions += [self.openrecent.addAction('%d: %s' % (idx+1, os.path.basename(item)), partial(self.openSlide,item))]


def updateOpenRecentDatabase(self):
        lastOpenList = self.settings.value('lastDatabases', type=list)
        for action in self.openrecentdbactions:
                self.openrecentdb.removeAction(action)

        lastOpenList.reverse()
        self.openrecentdbactions = list()
        if len(lastOpenList) > 0:
                for idx,item in enumerate(lastOpenList):
                        self.openrecentdbactions += [self.openrecentdb.addAction('%d: %s' % (idx+1, os.path.basename(item)), partial(self.openDatabase, False, item))]

def defineOpenRecent(self):
        openrecent = self.ui.menuFile.addMenu('Open recent')
        openrecent.setEnabled(True)
        self.openrecentactions = list()
        self.openrecent = openrecent
        updateOpenRecentSlide(self)



def defineOpenRecentDatabase(self):
        openrecent = self.ui.menuDatabase.addMenu('Open recent')
        openrecent.setEnabled(True)
        self.openrecentdbactions = list()

        self.openrecentdb = openrecent
        updateOpenRecentDatabase(self)

        
def defineAnnotationMenu(self):
        annomode = self.ui.menuAnnotation.addMenu('Mode')
        annomode.setEnabled(True)
        self.menuItemView = annomode.addAction('View', partial(self.setUIMode, UIMainMode.MODE_VIEW))
        self.menuItemView.setCheckable(True)
        self.menuItemView.setChecked(True)
        self.menuItemView.setEnabled(True)


        self.menuItemAnnotateCenter = annomode.addAction('Annotate object center', partial(self.setUIMode, UIMainMode.MODE_ANNOTATE_SPOT) )
        self.menuItemAnnotateCenter.setCheckable(True)
        self.menuItemAnnotateCenter.setEnabled(True)
        self.menuItemAnnotateArea = annomode.addAction('Annotate outline (area)', partial(self.setUIMode, UIMainMode.MODE_ANNOTATE_AREA))
        self.menuItemAnnotateArea.setCheckable(True)
        self.menuItemAnnotateArea.setChecked(False)
        self.menuItemAnnotateArea.setEnabled(True)

        self.menuItemAnnotateOutline = annomode.addAction('Annotate outline (polygon)', partial(self.setUIMode, UIMainMode.MODE_ANNOTATE_POLYGON))
        self.menuItemAnnotateOutline.setCheckable(True)
        self.menuItemAnnotateOutline.setChecked(False)
        self.menuItemAnnotateOutline.setEnabled(True)

        self.menuItemAnnotateWand = annomode.addAction('Annotate outline (magic wand)', partial(self.setUIMode, UIMainMode.MODE_ANNOTATE_WAND))
        self.menuItemAnnotateWand.setCheckable(True)
        self.menuItemAnnotateWand.setChecked(False)
        self.menuItemAnnotateWand.setEnabled(True)


        self.menuItemAnnotateFlag= annomode.addAction('Annotate important position', partial(self.setUIMode, UIMainMode.MODE_ANNOTATE_FLAG))
        self.menuItemAnnotateFlag.setCheckable(True)
        self.menuItemAnnotateFlag.setChecked(False)
        self.menuItemAnnotateFlag.setEnabled(True)

        self.menuItemAnnotateCircle = annomode.addAction('Annotate outline (circle)', partial(self.setUIMode, UIMainMode.MODE_ANNOTATE_CIRCLE))
        self.menuItemAnnotateCircle.setCheckable(True)
        self.menuItemAnnotateCircle.setChecked(False)
        self.menuItemAnnotateCircle.setEnabled(True)
