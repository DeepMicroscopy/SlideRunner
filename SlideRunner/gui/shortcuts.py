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

        File description:
                Definition of UI shortcuts

"""


from PyQt5.QtWidgets import QShortcut
from PyQt5.QtGui import QKeySequence
from functools import partial

def defineShortcuts(self):

    shortcuts=[]

    for k in range(8):
        shortcut = QShortcut(QKeySequence("%d" % (k+1)),self)
        shortcut.activated.connect(partial(self.clickAnnoclass, k+1))
        shortcuts.append(shortcut)

    # Set keyboard shortcuts
    shortcutPlus = QShortcut(QKeySequence("+"), self)
    shortcutPlus.activated.connect(self.zoomIn)
    shortcuts.append(shortcutPlus)
    shortcutMinus = QShortcut(QKeySequence("-"), self)
    shortcutMinus.activated.connect(self.zoomOut)
    shortcuts.append(shortcutMinus)
    shortcutEsc = QShortcut(QKeySequence("Esc"), self)
    shortcutEsc.activated.connect(self.hitEscape)
    shortcuts.append(shortcutEsc)
    shortcutN = QShortcut(QKeySequence("N"), self)
    shortcutN.activated.connect(self.nextScreeningStep)
    shortcuts.append(shortcutN)

    return shortcuts

def defineMenuShortcuts(self):
    self.ui.action_Open.setShortcut("Ctrl+D")
    self.ui.action_Open.triggered.connect(self.openDatabase)
    self.ui.actionOpen.setShortcut("Ctrl+O")
    self.ui.actionOpen.triggered.connect(self.openSlideDialog)
    self.ui.actionOpen_custom.setShortcut("Ctrl+C")
    self.ui.actionCreate_new.triggered.connect(self.createNewDatabase)
    self.ui.actionOpen_custom.triggered.connect(self.openCustomDB)
    self.ui.actionAdd_annotator.triggered.connect(self.addAnnotator)
    self.ui.actionAdd_cell_class.triggered.connect(self.addCellClass)
    self.ui.action_Quit.setShortcut('Ctrl+Q')
    self.ui.action_Quit.triggered.connect(self.close)
