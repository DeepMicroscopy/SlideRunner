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

from PyQt6 import QtGui, QtWidgets, QtCore
import sys
from time import time,sleep
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QDialog, QApplication, QMainWindow
from PyQt6.QtWidgets import QSplashScreen
from PyQt6.QtCore import  Qt
from functools import partial

import os
ARTWORK_DIR_NAME = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))+os.sep+'artwork'+os.sep


def closeDlg(splash,e):
        splash.close()

def aboutDialog(app,version):

        # Create and display the about screen
        splash_pix = QPixmap(ARTWORK_DIR_NAME+'AboutScreen.png')
        splash = QSplashScreen(splash_pix, Qt.WindowType.WindowStaysOnTopHint)

        splash.showMessage('Version %s\n'%version, alignment = Qt.AlignmentFlag.AlignHCenter + Qt.AlignmentFlag.AlignBottom, color=Qt.GlobalColor.black)
        splash.setMask(splash_pix.mask())
        splash.show()

        splash.mousePressEvent = partial(closeDlg, splash)

        start = time()
        while splash.isActiveWindow() & (time() - start < 10):
            sleep(0.001)
            app.processEvents()
        
        if (splash.isActiveWindow()):
            splash.close()

 