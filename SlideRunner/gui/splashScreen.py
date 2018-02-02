from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QSplashScreen
from PyQt5.QtCore import  Qt

def splashScreen(app, version) -> QSplashScreen:


    # This first part is for loading the splash screen before anything else

    # Create and display the splash screen
    splash_pix = QPixmap('artwork/SplashScreen.png')
    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
    splash.showMessage('Version %s\n'%version, alignment = Qt.AlignHCenter + Qt.AlignBottom, color=Qt.black)
    splash.setMask(splash_pix.mask())
    splash.show()
    app.processEvents()

    return splash