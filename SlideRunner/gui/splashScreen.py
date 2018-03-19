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