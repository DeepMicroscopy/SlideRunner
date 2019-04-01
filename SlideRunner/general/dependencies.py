"""

        This is SlideRunner - An Open Source Annotation Tool 
        for Digital Histology Slides.

         Marc Aubreville, Pattern Recognition Lab, 
         Friedrich-Alexander University Erlangen-Nuremberg 
         marc.aubreville@fau.de

        If you use this software in research, please citer our paper:
        M. Aubreville, C. Bertram, R. Klopfleisch and A. Maier:
        SlideRunner - A Tool for Massive Cell Annotations in Whole Slide Images
        Bildverarbeitung fuer die Medizin 2018, Springer Verlag, Berlin-Heidelberg

"""
from PyQt5 import QtWidgets

def check_version(actual:str, target:str) -> bool:
    if (target is None):
        return True
    actual_tup = actual.split('.')
    target_tup = target.split('.')

    for idx in range(len(target_tup)):
        if int(target_tup[idx])>int(actual_tup[idx]):
            return False
        if int(target_tup[idx])<int(actual_tup[idx]):
            return True
    
    return True

def check_qt_dependencies():
    """
        Check all QT-related dependencies for SlideRunner
    """
    import sys

    try:
        __import__('PyQt5')
    except:
        print('Error: PyQT5 not found. Please install.')
        sys.exit(1)
    else:
        from PyQt5.QtCore import QT_VERSION_STR
        if not (check_version(QT_VERSION_STR, '5.6.0')):
            print('Your PyQT5 is too old (%s). Please upgrade to >= 5.6.0.' % QT_VERSION_STR)
            sys.exit(1)

def check_all_dependencies():


    libraries_with_versions = [
                ('numpy', 'np', '1.13'), 
                ('matplotlib', 'mp', '2.0.0'), 
                ('cv2','cv2','3.1.0'), 
                ('sqlite3','sqlite3', '2.6.0'),
                ('time','time',None), 
                ('random','random',None),
                ('os','os',None), 
                ('threading','threading',None),
                ('queue','queue', None),
                ('logging','logging','0.5'),
                ('signal','signal', None),
                ('matplotlib.path','path',None),
                ('time','time',None),
                ('functools','functools',None),
                ('openslide','openslide','1.1.1')] # (library_name, shorthand)

    for (name, short, version) in libraries_with_versions:
        try:
            lib = __import__(name)
        except:
            print('Missing or nonfunctional package %s: %s' % (name, sys.exc_info()[1]))
            sys.exit()
        else:
            globals()[short] = lib
            if ((hasattr(lib,'__version__') and not check_version(lib.__version__,version)) or
                (hasattr(lib,'version') and type(lib.version)==str and not check_version(lib.version,version))):

                reply = QtWidgets.QMessageBox.information(None, 'Error',
                    'Too old package %s: Version should be at least %s' % (name, version), QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)


import sys

check_qt_dependencies()

check_all_dependencies()

# The rest should now load fine

# More PyQt5 imports
from PyQt5.QtCore import QThread, QStringListModel, Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QColor, QImage, QStandardItemModel, QStandardItem, QBrush, QIcon, QKeySequence
#from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QDialog, QWidget, QFileDialog, QMenu,QInputDialog, QAction, QPushButton, QItemDelegate, QTableWidgetItem, QCheckBox

# internal imports
from SlideRunner.gui.SlideRunner_ui import Ui_MainWindow
from SlideRunner.gui.dialogs.about import aboutDialog
from SlideRunner.gui.dialogs.settings import settingsDialog
from SlideRunner.gui import shortcuts, toolbar, mouseEvents, annotation
from SlideRunner.dataAccess.database import Database
from SlideRunner.processing import screening, thumbnail
from SlideRunner.general import SlideRunnerPlugin
from SlideRunner.gui.types import *
from SlideRunner.gui.sidebar import *
from SlideRunner.general.types import pluginEntry

import matplotlib.cm 
partial = functools.partial
path = path.path
