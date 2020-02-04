from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMenu
from PyQt5.QtWidgets import QTableWidget
from SlideRunner.gui.types import *
from SlideRunner.gui import annotation as GUIannotation
from functools import partial

class ClassSelectTableWidget(QTableWidget):
    def __init__(self, parent = None, parentObject = None):
        QTableWidget.__init__(self, parent)
        self.parentObject = parentObject
    
    def contextMenuEvent(self, event):
        columnId = self.columnAt(event.pos().x())
        rowId = self.rowAt(event.pos().y())
        menu = QMenu(self)
        if (columnId == 0):
                addAction = menu.addAction('Toggle all', self.parentObject.toggleAllClasses)

        elif (self.parentObject.db.isOpen()):
                addAction = menu.addAction('Add new class')
                addAction.triggered.connect(self.parentObject.addCellClass)
                if (rowId > 0):
                        if (self.parentObject.classList[rowId].itemID == ClassRowItemId.ITEM_DATABASE):
                                changeColorAction = menu.addAction('Change color', partial(GUIannotation.changeClassColor, self.parentObject, self.parentObject.classList[rowId].color, self.parentObject.classList[rowId].uid))                
                                renameAction = menu.addAction('Rename class',partial(GUIannotation.renameClass,self.parentObject, self.parentObject.classList[rowId].uid))                
                                removeAction = menu.addAction('Remove class', partial(GUIannotation.deleteClass, self.parentObject, self.parentObject.classList[rowId].uid))                

                                removeAllOfClassAction = menu.addAction('Remove all of this class from slide', partial(GUIannotation.deleteAllFromClassOnSlide,self.parentObject, self.parentObject.classList[rowId].uid))


                if (self.parentObject.activePlugin is not None) and (rowId > 0):
                        if (self.parentObject.classList[rowId].itemID == ClassRowItemId.ITEM_PLUGIN):
                                addmenu = menu.addMenu('Copy all items to database as:')
                                menuitems = list()
                                for clsname in self.parentObject.db.getAllClasses():
                                        act=addmenu.addAction(clsname[0],partial(GUIannotation.copyAllAnnotations,self.parentObject,self.parentObject.classList[rowId].classID, clsname[1], event))
                                        menuitems.append(act)

        action = menu.exec_(self.mapToGlobal(event.pos()))


def addSidebar(self, parentObject):

        self.tabView = QtWidgets.QTabWidget()


        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
#        sizePolicy.setHeightForWidth(self.tabView.sizePolicy().hasHeightForWidth())
        self.tabView.setSizePolicy(sizePolicy)
        self.tabView.setMaximumSize(QtCore.QSize(16777215, 300))

        self.tab1widget = QtWidgets.QWidget()
        self.tab1Layout = QtWidgets.QVBoxLayout()
        self.tab1widget.setLayout(self.tab1Layout)
        self.tab1Layout.setObjectName("tab1Layout")

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(10)
        sizePolicy.setHeightForWidth(self.tab1widget.sizePolicy().hasHeightForWidth())
        self.tab1widget.setSizePolicy(sizePolicy)
        self.tab1widget.setMinimumSize(QtCore.QSize(200, 100))

        self.tab2widget = QtWidgets.QWidget()
        self.tab2Layout = QtWidgets.QVBoxLayout()
        self.tab2widget.setLayout(self.tab2Layout)
        self.tab2Layout.setObjectName("tab2Layout")

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.tab2widget.sizePolicy().hasHeightForWidth())
        self.tab2widget.setSizePolicy(sizePolicy)
        self.tab2widget.setMinimumSize(QtCore.QSize(200, 100))



        self.categoryView = ClassSelectTableWidget(self.centralwidget, parentObject)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.categoryView.sizePolicy().hasHeightForWidth())
        self.categoryView.setSizePolicy(sizePolicy)
        self.categoryView.setMinimumSize(QtCore.QSize(200, 100))
#        self.categoryView.setMaximumSize(QtCore.QSize(16777215, 120))
        self.categoryView.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.categoryView.setObjectName("categoryView")
        self.categoryView.setColumnCount(0)
        self.categoryView.setRowCount(0)
        self.categoryView.setVisible(False)
        self.tab1Layout.addWidget(self.categoryView)
        self.annotatorComboBox = QtWidgets.QComboBox(self.tab1widget)
       # self.annotatorComboBox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.annotatorComboBox.setObjectName("comboBox")
        self.annotatorComboBox.setVisible(False)
        self.tab1Layout.addWidget(self.annotatorComboBox)
        self.statisticView = QtWidgets.QTableView(self.tab2widget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.statisticView.sizePolicy().hasHeightForWidth())
        self.statisticView.setMinimumSize(QtCore.QSize(200, 10))
        self.statisticView.setSizePolicy(sizePolicy)
#        self.statisticView.setMaximumSize(QtCore.QSize(16777215, 120))
        self.statisticView.setObjectName("statisticView")
        self.statisticView.setVisible(True)
        self.tab2Layout.addWidget(self.statisticView)
        self.inspectorTableView = QtWidgets.QTableView(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.inspectorTableView.sizePolicy().hasHeightForWidth())
        self.inspectorTableView.setSizePolicy(sizePolicy)
        self.inspectorTableView.setMinimumSize(QtCore.QSize(200, 10))
        self.inspectorTableView.setObjectName("tableView")
        self.inspectorTableView.setVisible(False)
        self.tab1Layout.addWidget(self.inspectorTableView)
        self.statusLabel = QtWidgets.QLabel(self.centralwidget)
        self.statusLabel.setObjectName("statusLabel")
        self.progressBar = QtWidgets.QProgressBar(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.progressBar.sizePolicy().hasHeightForWidth())
        self.progressBar.setSizePolicy(sizePolicy)
        self.progressBar.setProperty("value", 24)
        self.progressBar.setObjectName("progressBar")

        self.opacitySlider = QtWidgets.QSlider(self.centralwidget)
        self.opacitySlider.setEnabled(False)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.opacitySlider.sizePolicy().hasHeightForWidth())
        self.opacitySlider.setSizePolicy(sizePolicy)
        self.opacitySlider.setProperty("value", 50)
        self.opacitySlider.setOrientation(QtCore.Qt.Horizontal)
        self.opacitySlider.setObjectName("opacitySlider")


        self.stretchlabel = QtWidgets.QLabel(self.centralwidget)
        self.stretchlabel.setObjectName("stretchlabel")
        self.stretchlabel.setText("")
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        self.stretchlabel.setSizePolicy(sizePolicy)        
        self.stretchlabel.setMinimumSize(QtCore.QSize(200, 0))

        self.tab1Layout.addWidget(self.statusLabel)

 
#        self.tab3scrollarea.setWidget(self.tab3scrolllayout.widget())
        self.tab3widget = QtWidgets.QWidget()
        self.tab3Layout = QtWidgets.QVBoxLayout()
        self.tab3widget.setLayout(self.tab3Layout)
        self.tab3Layout.setObjectName("tab3Layout")

        self.opacityLabel = QtWidgets.QLabel(self.centralwidget)
        self.opacityLabel.setObjectName("opacityLabel")
        self.tab3Layout.addWidget(self.opacityLabel)
        self.tab3Layout.addWidget(self.opacitySlider)

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.tab3widget.setSizePolicy(sizePolicy)        


        self.tabView.addTab(self.tab1widget, "Annotation")
        self.tabView.addTab(self.tab2widget, "Statistics")
        self.tabView.addTab(self.tab3widget, "Plugin")
        self.sidebarLayout.addWidget(self.tabView)
        self.sidebarLayout.addWidget(self.stretchlabel)
        self.sidebarLayout.addWidget(self.progressBar)

        self.opacityLabel.setText( "Overlay opacity")
        self.opacityLabel.setStyleSheet("font-size:8px")
        self.opacitySlider.setToolTip( "Opacity")

        self.statusLabel.setText( "TextLabel")


        return self