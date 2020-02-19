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

        File description:
                Definition of UI shortcuts

"""


from PyQt5.QtWidgets import QShortcut
from PyQt5.QtGui import QKeySequence
from functools import partial

def defineShortcuts(self):

    shortcuts=[]

    for k in range(8):
        shortcut = QShortcut(QKeySequence("Ctrl+%d" % (k+1)),self)
        shortcut.activated.connect(partial(self.toggleOneClass, k+1))
        shortcuts.append(shortcut)

    for k in range(8):
        shortcut = QShortcut(QKeySequence("%d" % (k+1)),self)
        shortcut.activated.connect(partial(self.clickAnnoclass, k+1))
        shortcuts.append(shortcut)


    # Set keyboard shortcuts
    shortcutEsc = QShortcut(QKeySequence("Esc"), self)
    shortcutEsc.activated.connect(self.hitEscape)
    shortcuts.append(shortcutEsc)
    shortcutN = QShortcut(QKeySequence("N"), self)
    shortcutN.activated.connect(self.nextScreeningStep)
    shortcuts.append(shortcutN)

    shortcut = QShortcut(QKeySequence.Delete, self)
    shortcut.activated.connect(self.deleteCurrentSelection)
    shortcuts.append(shortcut)
    shortcut = QShortcut(QKeySequence.Backspace, self)
    shortcut.activated.connect(self.deleteCurrentSelection)
    shortcuts.append(shortcut)


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
    self.ui.actionManageDatabase.setShortcut("Ctrl+V")
    if (self.settings.value('exactSupportEnabled', 0)):
        self.ui.databaseExactMenuSync.setShortcut("Ctrl+Shift+Y")
        self.ui.exactMenuSyncImage.setShortcut("Ctrl+Y")
    self.ui.action_Quit.setShortcut('Ctrl+Q')
    self.ui.action_Quit.triggered.connect(self.close)
    self.menuItemAnnotateOutline.setShortcut('P')
    self.menuItemAnnotateCenter.setShortcut('S')
    self.menuItemAnnotateCircle.setShortcut('C')
    self.menuItemAnnotateArea.setShortcut('R')
    self.menuItemAnnotateFlag.setShortcut('F')
    self.menuItemAnnotateWand.setShortcut('W')
