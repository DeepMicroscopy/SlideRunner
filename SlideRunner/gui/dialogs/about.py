from PyQt5 import QtGui, QtWidgets, QtCore
import sys
from time import time,sleep
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QDialog, QApplication, QMainWindow
from PyQt5.QtWidgets import QSplashScreen
from PyQt5.QtCore import  Qt
from functools import partial



def closeDlg(splash,e):
        splash.close()

def aboutDialog(app,version):

        # Create and display the about screen
        splash_pix = QPixmap('artwork/AboutScreen.png')
        splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)

        splash.showMessage('Version %s\n'%version, alignment = Qt.AlignHCenter + Qt.AlignBottom, color=Qt.black)
        splash.setMask(splash_pix.mask())
        splash.show()

        splash.mousePressEvent = partial(closeDlg, splash)

        start = time()
        while splash.isActiveWindow() & (time() - start < 10):
            sleep(0.001)
            app.processEvents()
        
        if (splash.isActiveWindow()):
            splash.close()

 