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

from functools import partial
from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QIcon
from SlideRunner.gui.types import *
"""
    Construct toolbar
"""
import os

ARTWORK_DIR_NAME = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))+os.sep+'artwork'+os.sep


def defineToolbar(self):
        self.ui.tb = self.addToolBar("Annotation")
        
        self.ui.iconView = QAction(QIcon(ARTWORK_DIR_NAME+"iconArrow.png"),"View",self)
        self.ui.iconCircle = QAction(QIcon(ARTWORK_DIR_NAME+"iconCircle.png"),"Annotate spots",self)
        self.ui.iconRect = QAction(QIcon(ARTWORK_DIR_NAME+"iconRect.png"),"Annotate areas",self)
        self.ui.iconDrawCircle = QAction(QIcon(ARTWORK_DIR_NAME+"drawCircle.png"),"Annotate circular area",self)
        self.ui.iconPolygon = QAction(QIcon(ARTWORK_DIR_NAME+"iconPolygon.png"),"Annotate polygon",self)
        self.ui.iconFlag = QAction(QIcon(ARTWORK_DIR_NAME+"icon_flag.png"),"Mark an important position",self)
        self.ui.iconBlinded = QAction(QIcon(ARTWORK_DIR_NAME+"iconBlinded.png"),"Blinded mode",self)
        self.ui.iconQuestion = QAction(QIcon(ARTWORK_DIR_NAME+"iconQuestion.png"),"Discovery mode",self)
        self.ui.iconScreening = QAction(QIcon(ARTWORK_DIR_NAME+"icon_screeningMode.png"),"Screening mode",self)
        self.ui.iconOverlay = QAction(QIcon(ARTWORK_DIR_NAME+"iconOverlay.png"),"Overlay screening map in overview",self)
        self.ui.iconAnnoTN = QAction(QIcon(ARTWORK_DIR_NAME+"annoInOverview.png"),"Overlay annotations in overview",self)
        self.ui.iconPreviousScreen = QAction(QIcon(ARTWORK_DIR_NAME+"icon_previousView.png"),"Previous view (screening)",self)
        self.ui.iconNextScreen = QAction(QIcon(ARTWORK_DIR_NAME+"icon_nextView.png"),"Next view (screening)",self)
        self.ui.iconBack = QAction(QIcon(ARTWORK_DIR_NAME+"backArrow.png"),"Back to last annotation",self)
        self.ui.iconRect.setCheckable(True)
        self.ui.iconView.setCheckable(True)
        self.ui.iconView.setChecked(True)
        self.ui.iconCircle.setCheckable(True)
        self.ui.iconDrawCircle.setCheckable(True)
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
        self.ui.iconPreviousScreen.setEnabled(False)
        self.ui.iconQuestion.setEnabled(False)


        self.ui.tb.addAction(self.ui.iconView)
        self.ui.tb.addAction(self.ui.iconCircle)
        self.ui.tb.addAction(self.ui.iconRect)
        self.ui.tb.addAction(self.ui.iconDrawCircle)
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
        self.ui.tb.addAction(self.ui.iconPreviousScreen)
        self.ui.tb.addAction(self.ui.iconNextScreen)
        self.ui.tb.addAction(self.ui.iconBack)

        # Connect triggers for toolbar
        self.ui.iconView.triggered.connect(partial(self.setUIMode, UIMainMode.MODE_VIEW))
        self.ui.iconCircle.triggered.connect(partial(self.setUIMode, UIMainMode.MODE_ANNOTATE_SPOT))
        self.ui.iconRect.triggered.connect(partial(self.setUIMode, UIMainMode.MODE_ANNOTATE_AREA))
        self.ui.iconDrawCircle.triggered.connect(partial(self.setUIMode, UIMainMode.MODE_ANNOTATE_CIRCLE))
        self.ui.iconPolygon.triggered.connect(partial(self.setUIMode, UIMainMode.MODE_ANNOTATE_POLYGON))
        self.ui.iconFlag.triggered.connect(partial(self.setUIMode, UIMainMode.MODE_ANNOTATE_FLAG))
        self.ui.iconBlinded.triggered.connect(self.setBlindedMode)
        self.ui.iconQuestion.triggered.connect(self.setDiscoveryMode)
        self.ui.iconOverlay.triggered.connect(self.setOverlayHeatmap)
        self.ui.iconBack.triggered.connect(self.backToLastAnnotation)
        self.ui.iconAnnoTN.triggered.connect(self.setOverlayHeatmap)
        self.ui.iconScreening.triggered.connect(self.startStopScreening)
        self.ui.iconNextScreen.triggered.connect(self.nextScreeningStep)
        self.ui.iconPreviousScreen.triggered.connect(self.previousScreeningStep)
