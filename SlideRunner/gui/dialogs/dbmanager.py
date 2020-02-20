from SlideRunner.general.dependencies import *
from SlideRunner.dataAccess.database import Database
from functools import partial
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSlot
import sys
import os
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
        self.loadSlide = ''
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
        self.tableWidget.setRowCount(len(DB.listOfSlidesWithExact()))
        self.los = DB.listOfSlidesWithExact()
        for row,(idx,filename,exactid,directory) in enumerate(self.los):
            self.tableWidget.setItem(row,0, QTableWidgetItem(str(idx)))
            self.tableWidget.setItem(row,1, QTableWidgetItem(str(filename)))
            self.tableWidget.setItem(row,2, QTableWidgetItem(str(fileToAnnos[int(idx)]) if (int(idx)) in fileToAnnos else '0'))
            self.tableWidget.setItem(row,3, QTableWidgetItem(str(exactid)))

            btn = QPushButton('open')
            self.tableWidget.setCellWidget(row,4, btn)

            btn.clicked.connect(partial(self.loadFile, self.los[row]))


    def createTable(self):
       # Create table
        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(5)
        self.tableWidget.setHorizontalHeaderLabels(['ID','Filename','Annotations', 'EXACT Image ID', ''])
        self.updateTable()
        self.tableWidget.move(0,0)
        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.viewport().installEventFilter(self)
        self.tableWidget.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)

    def loadFile(self, uid):
        
        slidepath=(uid[-1]+os.sep+uid[1]) if os.path.exists((str(uid[-1])+os.sep+str(uid[1]))) else uid[1]

        if (os.path.exists(slidepath)):
                self.loadSlide = slidepath
                self.close()
        else:
            QtWidgets.QMessageBox.information(self,'Not found',f'The file {slidepath} could not be found.')


    def removeFile(self, uid):
        reply = QtWidgets.QMessageBox.question(self, 'Question',
                                        'Do you really want to delete the file and all annotations from the database?', QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.No:
            return
        self.DB.removeFileFromDatabase(uid[0])
        self.DB.commit()
        self.updateTable()
        self.show()

    def removeExactLink(self, uids:list):
        if (len(uids)>1):
            reply = QtWidgets.QMessageBox.question(self, 'Question',
                                            'Do you really want to remove the link to EXACT for these slides?', QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
        else:
            reply = QtWidgets.QMessageBox.question(self, 'Question',
                                            'Do you really want to remove the link to EXACT for this slide?', QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.No:
            return
        for uid in uids:
            self.DB.execute(f'UPDATE Slides SET exactImageID=Null where uid=={uid}')
        self.DB.commit()
        self.updateTable()
        self.show()

    def eventFilter(self, source, event):
        if(event.type() == QtCore.QEvent.MouseButtonPress and
           event.buttons() == QtCore.Qt.RightButton and
           source is self.tableWidget.viewport()):
            rows = np.unique([x.row() for x in self.tableWidget.selectedItems()])
            rowuids = [self.los[x][0] for x in rows]
            item = self.tableWidget.itemAt(event.pos())
            if item is not None:
                menu = QMenu(self)
                menu.addAction('Open '+self.los[item.row()][1], partial(self.loadFile, self.los[item.row()]))         #(QAction('test'))
                menu.addAction('Remove '+self.los[item.row()][1], partial(self.removeFile, self.los[item.row()]))         #(QAction('test'))
                if (len(rows)>1):
                    menu.addAction('Remove EXACT link selected rows ', partial(self.removeExactLink, rowuids))         #(QAction('test'))
                else:
                    menu.addAction('Remove EXACT link for '+self.los[item.row()][1], partial(self.removeExactLink, rowuids))         #(QAction('test'))
                menu.exec_(event.globalPos())
        return super(DatabaseManager, self).eventFilter(source, event)

 

