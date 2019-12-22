from SlideRunner.general.dependencies import *
from SlideRunner.dataAccess.database import Database
from functools import partial
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSlot
import sys
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QAction, QTableWidget,QTableWidgetItem,QVBoxLayout
from PyQt5.QtGui import QIcon

class DatabaseManager(QDialog):

    def __init__(self, DB:Database):
        super().__init__()
        self.title = 'Database overview (%s)' % DB.dbfilename
        self.left = 50
        self.top = 50
        self.width = 600
        self.height = 500
        self.DB = DB
        self.setModal(True)
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        
        self.createTable()

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.tableWidget) 
        self.setLayout(self.layout) 

        self.show()

    def updateTable(self):
        DB = self.DB
        fileToAnnos = {slide:count for slide,count in DB.execute('SELECT slide, COUNT(*) FROM Annotations group by slide').fetchall()}
        self.tableWidget.setRowCount(len(DB.listOfSlides()))
        self.los = DB.listOfSlides()
        for row,(idx,filename) in enumerate(self.los):
            self.tableWidget.setItem(row,0, QTableWidgetItem(str(idx)))
            self.tableWidget.setItem(row,1, QTableWidgetItem(str(filename)))
            self.tableWidget.setItem(row,2, QTableWidgetItem(str(fileToAnnos[int(idx)]) if (int(idx)) in fileToAnnos else '0'))

    def createTable(self):
       # Create table
        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(3)
        self.tableWidget.setHorizontalHeaderLabels(['ID','Filename','Annotations'])
        self.updateTable()
        self.tableWidget.move(0,0)
        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.viewport().installEventFilter(self)
        
    
    def removeFile(self, uid):
        reply = QtWidgets.QMessageBox.question(self, 'Question',
                                        'Do you really want to delete the file and all annotations from the database?', QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.No:
            return
        self.DB.removeFileFromDatabase(uid[0])
        self.updateTable()
        self.show()

    def eventFilter(self, source, event):
        if(event.type() == QtCore.QEvent.MouseButtonPress and
           event.buttons() == QtCore.Qt.RightButton and
           source is self.tableWidget.viewport()):
            item = self.tableWidget.itemAt(event.pos())
            if item is not None:
                menu = QMenu(self)
                menu.addAction('Remove '+item.text(), partial(self.removeFile, self.los[item.row()]))         #(QAction('test'))
                menu.exec_(event.globalPos())
        return super(DatabaseManager, self).eventFilter(source, event)

 

