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


        Style definitions
"""

from PyQt6.QtWidgets import  QStyleFactory
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

from PyQt6 import QtGui, QtCore

#from PyQt6.QtWidgets import QDialog, QStyleFactory, QWidget, QFileDialog, QMenu,QInputDialog, QAction, QPushButton, QItemDelegate, QTableWidgetItem, QCheckBox

def setStyle(app):

    app.setStyle(QStyleFactory.create("Fusion"))

    darkPalette = QPalette()
    
    darkPalette.setColor(QPalette.ColorRole.Window, QColor.fromRgb(53,53,53))
    darkPalette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    darkPalette.setColor(QPalette.ColorRole.Base, QColor.fromRgb(25,25,25))
    darkPalette.setColor(QPalette.ColorRole.AlternateBase, QColor.fromRgb(53,53,53))
    darkPalette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    darkPalette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    darkPalette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    darkPalette.setColor(QPalette.ColorRole.Button, QColor.fromRgb(53,53,53))
    darkPalette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    darkPalette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    darkPalette.setColor(QPalette.ColorRole.Link, QColor.fromRgb(42, 130, 218))

    darkPalette.setColor(QPalette.ColorRole.Highlight, QColor.fromRgb(42, 130, 218))
    darkPalette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)

    import os

    ARTWORK_DIR_NAME = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))+os.sep+'artwork'+os.sep

    import platform
    print('<%s>' % platform.system())
    if (platform.system() == 'Darwin'):
        app_icon = QtGui.QIcon(ARTWORK_DIR_NAME+'SlideRunner.icns')
    else:
        app_icon = QtGui.QIcon(ARTWORK_DIR_NAME+'icon.png')

    app.setWindowIcon(app_icon)
    app.setApplicationName('SlideRunner')

    app.setPalette(darkPalette)

    app.setStyleSheet("""QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; } QTabWidget::pane { /* The tab widget frame */
border-top: 2px solid #C2C7CB;
}
QTabWidget::tab-bar {
left: 5px; /* move to the right by 5px */
}

QTabWidget {
font-size:8px;
}
QTabBar::tab:selected, QTabBar::tab:hover {
background: QLinearGradient( x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #ffa02f, stop: 1 #ff862f);
}
/* Style the tab using the tab sub-control. Note that it reads QTabBar _not_ QTabWidget */
QTabBar::tab {
border: 2px solid #C4C4C3;
border-bottom-color: #C2C7CB; /* same as the pane color */
border-top-left-radius: 4px;
border-top-right-radius: 4px;
font-size:8px;
min-width: 8ex;
padding: 2px;
}
QMenu::item:selected
{
    background: QLinearGradient( x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #ffa02f, stop: 1 #ff862f);
}
QMenu::item:!selected
{
    background: QLinearGradient( x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #343434, stop: 1 #343434);
}
QMenuBar::item:selected
{
    background: QLinearGradient( x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #ffa02f, stop: 1 #ff862f);
}
QProgressBar::chunk
{
    background-color: #d7801a;
    width: 2.15px;
    margin: 0.5px;
}

QTabBar::tab:!selected {
margin-top: 2px; /* make non-selected tabs look smaller */
}
""")
