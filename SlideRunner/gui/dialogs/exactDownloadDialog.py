from SlideRunner.general.dependencies import *
from SlideRunner.dataAccess.database import Database
from functools import partial
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSlot
import sys
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QAction, QTableWidget,QTableWidgetItem,QVBoxLayout
from PyQt5.QtGui import QIcon
from SlideRunner.dataAccess.exact import *
from functools import partial

class ExactDownloadDialog(QDialog):

    def __init__(self, DB:Database, settingsObject):
        super().__init__()
        self.title = 'Download from EXACT (%s)' % settingsObject.value('exactHostname', 'https://exact.cs.fau.de').replace('//','//'+settingsObject.value('exactUsername', 'Demo')+'@')
        self.left = 50
        self.top = 50
        self.width = 900
        self.height = 500
        self.DB = DB
        self.setModal(True)
        hostname = settingsObject.value('exactHostname', 'https://exact.cs.fau.de')
        if hostname[-1] != '/':
            hostname += '/'
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
        self.loi = self.exm.retrieve_imagesets()
        rowcount=0
        self.los = []
        for imageset in self.loi:
            for row,image in enumerate(imageset['images']):
                for product in imageset['products']:
                    self.los.append([image_and_product_to_id(image['id'], product['id'],imageset['id']),imageset['name']+'('+product['name']+')', str(image['name']),fileToAnnos[image_and_product_to_id(image['id'], product['id'],imageset['id'])] if image_and_product_to_id(image['id'], product['id'],imageset['id']) in fileToAnnos else '' ])
                    rowcount+=1
        self.tableWidget.setRowCount(rowcount)
        for row,(id,imset,im,linked) in enumerate(self.los):
            self.tableWidget.setItem(row,0, QTableWidgetItem(str(id)))
            self.tableWidget.setItem(row,1, QTableWidgetItem(str(imset)))
            self.tableWidget.setItem(row,2, QTableWidgetItem(str(im)))
            self.tableWidget.setItem(row,3, QTableWidgetItem(str(linked)))
            btn = QPushButton('download')
            self.tableWidget.setCellWidget(row,4, btn)
            btn.clicked.connect(partial(self.download, self.los[row]))

    def createTable(self):
       # Create table
        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(5)
        self.tableWidget.setHorizontalHeaderLabels(['ID','Imageset','Image','Assigned to'])
        self.updateTable()
        self.tableWidget.move(0,0)
        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.viewport().installEventFilter(self)
        
    
    def download(self, los):
        print('Lets download ...')
        exactid, _, imname, linked = los
        if not (linked==''):
            reply = QtWidgets.QMessageBox.question(self, 'Question',
                                            f'This image exists already in the database. Check out new copy?', QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

            if reply == QtWidgets.QMessageBox.No:
                return
        
        savefolder = QtWidgets.QFileDialog.getExistingDirectory()
        if (savefolder==''):
            return

        (image_id, product_id, imageset_id) = [int(x) for x in exactid.split('/')]

        reply = QtWidgets.QMessageBox.question(self, 'Question',
                                        f'Add image and annotations to database?', QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)


        progress = QtWidgets.QProgressDialog("Downloading image ..", "Cancel", 0, 100, self)
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.show()

        outfilename = self.exm.download_image(image_id=image_id, target_folder=savefolder, callback=progress.setValue)

        if reply == QtWidgets.QMessageBox.Yes:
            fpath,fname = os.path.split(outfilename)
            slideid = self.DB.insertNewSlide(fname,fpath)

            self.DB.execute(f'UPDATE Slides set exactImageID="{exactid}" where uid=={slideid}')
            progress.setWindowTitle('Synchronizing annotations')
            
            self.exm.sync(dataset_id=image_id, imageset_id=imageset_id, product_id=product_id, slideuid=slideid, filename=imname, database=self.DB, callback=progress.setValue)

            reply = QtWidgets.QMessageBox.information(self, 'Finished',
                           'Download finished', QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)

        progress.close()
#        self.DB.execute(f'UPDATE Slides set exactImageID={exactid} where uid=={self.DB.annotationsSlide}')
        self.updateTable()
        self.show()

    def eventFilter(self, source, event):
        if(event.type() == QtCore.QEvent.MouseButtonPress and
           event.buttons() == QtCore.Qt.RightButton and
           source is self.tableWidget.viewport()):
            item = self.tableWidget.itemAt(event.pos())
            if item is not None:
                menu = QMenu(self)
                menu.addAction('Download this image', partial(self.download, self.los[item.row()]))         #(QAction('test'))
                menu.exec_(event.globalPos())
        return super(ExactDownloadDialog, self).eventFilter(source, event)

 

