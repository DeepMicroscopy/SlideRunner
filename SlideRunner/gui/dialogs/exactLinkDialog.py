from SlideRunner.general.dependencies import *
from SlideRunner.dataAccess.database import Database
from functools import partial
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSlot
import sys
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QAction, QTableWidget,QTableWidgetItem,QVBoxLayout
from PyQt5.QtGui import QIcon
from SlideRunner.dataAccess.exact import *


class ExactLinkDialog(QDialog):

    def __init__(self, DB:Database, settingsObject, imageset):
        super().__init__()
        self.title = 'EXACT overview (%s)' % settingsObject.value('exactHostname', 'https://exact.cs.fau.de').replace('//','//'+settingsObject.value('exactUsername', 'Demo')+'@')
        self.left = 50
        self.top = 50
        self.width = 600
        self.height = 500
        self.DB = DB
        self.setModal(True)
        self.imageset = imageset
        hostname = settingsObject.value('exactHostname', 'https://exact.cs.fau.de')
        self.exm = ExactManager(settingsObject.value('exactUsername', 'Demo'), 
                                settingsObject.value('exactPassword', 'demodemo'),
                                hostname)
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
        def image_and_product_to_id(image_id, product_id, imageset_id):
            return str(image_id)+'/'+str(product_id)+'/'+str(imageset_id)
        DB = self.DB
        fileToAnnos = {exactimageid:slide for slide,exactimageid in DB.execute('SELECT filename, exactImageID from Slides').fetchall()}

        print('Retrieving imageset: ',self.imageset)
        self.loi = self.exm.APIs.image_sets_api.retrieve_image_set(self.imageset, expand='images,product_set')
        rowcount=0
        self.los = []

        for product in self.loi.product_set:
            for im in self.loi.images:
                self.los.append([image_and_product_to_id(im['id'], product['id'],self.imageset), str(im['name']),fileToAnnos[image_and_product_to_id(im['id'], product['id'],self.imageset)] if image_and_product_to_id(im['id'], product['id'],self.imageset) in fileToAnnos else '' ])
                rowcount+=1

        self.tableWidget.setRowCount(rowcount)
        for row,(id,im,linked) in enumerate(self.los):
            self.tableWidget.setItem(row,0, QTableWidgetItem(str(id)))
            self.tableWidget.setItem(row,1, QTableWidgetItem(str(im)))
            self.tableWidget.setItem(row,2, QTableWidgetItem(str(linked)))

    def createTable(self):
       # Create table
        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(3)
        self.tableWidget.setHorizontalHeaderLabels(['ID','Image','Assigned to'])
        self.updateTable()
        self.tableWidget.move(0,0)
        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.viewport().installEventFilter(self)
        
    
    def link(self, los):
        exactid, _, linked = los
        if not (linked==''):
            reply = QtWidgets.QMessageBox.question(self, 'Question',
                                            'Do you really want to link this image to a new image?', QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

            if reply == QtWidgets.QMessageBox.No:
                return
        (image_id, product_id, imageset_id) = [int(x) for x in exactid.split('/')]
        self.DB.execute(f'UPDATE Slides set exactImageID="{exactid}" where uid=={self.DB.annotationsSlide}')
        self.updateTable()
        self.show()

    def eventFilter(self, source, event):
        if(event.type() == QtCore.QEvent.MouseButtonPress and
           event.buttons() == QtCore.Qt.RightButton and
           source is self.tableWidget.viewport()):
            item = self.tableWidget.itemAt(event.pos())
            if item is not None:
                menu = QMenu(self)
                menu.addAction('Link to this image '+item.text(), partial(self.link, self.los[item.row()]))         #(QAction('test'))
                menu.exec_(event.globalPos())
        return super(ExactLinkDialog, self).eventFilter(source, event)

 

