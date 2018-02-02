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
from functools import partial
from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QIcon
from gui.types import *
"""
    Construct toolbar
"""

def defineToolbar(self):
        self.ui.tb = self.addToolBar("Annotation")
        self.ui.iconView = QAction(QIcon("artwork/iconArrow.png"),"View",self)
        self.ui.iconCircle = QAction(QIcon("artwork/iconCircle.png"),"Annotate spots",self)
        self.ui.iconRect = QAction(QIcon("artwork/iconRect.png"),"Annotate areas",self)
        self.ui.iconPolygon = QAction(QIcon("artwork/iconPolygon.png"),"Annotate polygon",self)
        self.ui.iconFlag = QAction(QIcon("artwork/icon_flag.png"),"Mark an important position",self)
        self.ui.iconBlinded = QAction(QIcon("artwork/iconBlinded.png"),"Blinded mode",self)
        self.ui.iconQuestion = QAction(QIcon("artwork/iconQuestion.png"),"Discovery mode",self)
        self.ui.iconScreening = QAction(QIcon("artwork/icon_screeningMode.png"),"Screening mode",self)
        self.ui.iconOverlay = QAction(QIcon("artwork/iconOverlay.png"),"Overlay screening map in overview",self)
        self.ui.iconAnnoTN = QAction(QIcon("artwork/annoInOverview.png"),"Overlay annotations in overview",self)
        self.ui.iconNextScreen = QAction(QIcon("artwork/icon_nextView.png"),"Next view (screening)",self)
        self.ui.iconBack = QAction(QIcon("artwork/backArrow.png"),"Back to last annotation",self)
        self.ui.iconRect.setCheckable(True)
        self.ui.iconView.setCheckable(True)
        self.ui.iconView.setChecked(True)
        self.ui.iconCircle.setCheckable(True)
        self.ui.iconPolygon.setCheckable(True)
        self.ui.iconBlinded.setCheckable(True)
        self.ui.iconFlag.setCheckable(True)
        self.ui.iconQuestion.setCheckable(True)
        self.ui.iconOverlay.setCheckable(True)
        self.ui.iconAnnoTN.setCheckable(True)
        self.ui.iconBack.setEnabled(False)
        self.ui.iconScreening.setCheckable(True)
        self.ui.iconBlinded.setEnabled(False)
        self.ui.iconNextScreen.setEnabled(False)
        self.ui.iconQuestion.setEnabled(False)


        self.ui.tb.addAction(self.ui.iconView)
        self.ui.tb.addAction(self.ui.iconCircle)
        self.ui.tb.addAction(self.ui.iconRect)
        self.ui.tb.addAction(self.ui.iconPolygon)
        self.ui.tb.addAction(self.ui.iconFlag)
        self.ui.tb.addSeparator()
        self.ui.tb.addAction(self.ui.iconBlinded)
        self.ui.tb.addAction(self.ui.iconQuestion)
        self.ui.tb.addAction(self.ui.iconScreening)
        self.ui.tb.addSeparator()
        self.ui.tb.addAction(self.ui.iconOverlay)
        self.ui.tb.addAction(self.ui.iconAnnoTN)
        self.ui.tb.addSeparator()
        self.ui.tb.addAction(self.ui.iconNextScreen)
        self.ui.tb.addAction(self.ui.iconBack)

        # Connect triggers for toolbar
        self.ui.iconView.triggered.connect(partial(self.setUIMode, UIMainMode.MODE_VIEW))
        self.ui.iconCircle.triggered.connect(partial(self.setUIMode, UIMainMode.MODE_ANNOTATE_SPOT))
        self.ui.iconRect.triggered.connect(partial(self.setUIMode, UIMainMode.MODE_ANNOTATE_AREA))
        self.ui.iconPolygon.triggered.connect(partial(self.setUIMode, UIMainMode.MODE_ANNOTATE_POLYGON))
        self.ui.iconFlag.triggered.connect(partial(self.setUIMode, UIMainMode.MODE_ANNOTATE_FLAG))
        self.ui.iconBlinded.triggered.connect(self.setBlindedMode)
        self.ui.iconQuestion.triggered.connect(self.setDiscoveryMode)
        self.ui.iconOverlay.triggered.connect(self.setOverlayHeatmap)
        self.ui.iconBack.triggered.connect(self.backToLastAnnotation)
        self.ui.iconAnnoTN.triggered.connect(self.setOverlayHeatmap)
        self.ui.iconScreening.triggered.connect(self.startStopScreening)
        self.ui.iconNextScreen.triggered.connect(self.nextScreeningStep)
