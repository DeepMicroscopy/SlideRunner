from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QSplashScreen
from PyQt5.QtCore import  Qt

import os

ARTWORK_DIR_NAME = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))+os.sep+'artwork'+os.sep

def splashScreen(app, version) -> QSplashScreen:


    # This first part is for loading the splash screen before anything else

    # Create and display the splash screen
    splash_pix = QPixmap(ARTWORK_DIR_NAME+'SplashScreen.png')
    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
    splash.showMessage('Version %s\n'%version, alignment = Qt.AlignHCenter + Qt.AlignBottom, color=Qt.black)
    splash.setMask(splash_pix.mask())
    splash.show()
    app.processEvents()

    return splash