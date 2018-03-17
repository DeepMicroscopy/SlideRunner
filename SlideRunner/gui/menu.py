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
from SlideRunner.gui.types import *
def defineAnnotationMenu(self):
        annomode = self.ui.menuAnnotation.addMenu('Mode')
        annomode.setEnabled(True)
        self.menuItemView = annomode.addAction('View', partial(self.setUIMode, UIMainMode.MODE_VIEW))
        self.menuItemView.setCheckable(True)
        self.menuItemView.setChecked(True)
        self.menuItemView.setEnabled(True)


        self.menuItemAnnotateCenter = annomode.addAction('Annotate object center', partial(self.setUIMode, UIMainMode.MODE_ANNOTATE_SPOT) )
        self.menuItemAnnotateCenter.setCheckable(True)
        self.menuItemAnnotateCenter.setEnabled(True)
        self.menuItemAnnotateArea = annomode.addAction('Annotate outline (area)', partial(self.setUIMode, UIMainMode.MODE_ANNOTATE_AREA))
        self.menuItemAnnotateArea.setCheckable(True)
        self.menuItemAnnotateArea.setChecked(False)
        self.menuItemAnnotateArea.setEnabled(True)

        self.menuItemAnnotateOutline = annomode.addAction('Annotate outline (polygon)', partial(self.setUIMode, UIMainMode.MODE_ANNOTATE_POLYGON))
        self.menuItemAnnotateOutline.setCheckable(True)
        self.menuItemAnnotateOutline.setChecked(False)
        self.menuItemAnnotateOutline.setEnabled(True)

        self.menuItemAnnotateFlag= annomode.addAction('Annotate important position', partial(self.setUIMode, UIMainMode.MODE_ANNOTATE_FLAG))
        self.menuItemAnnotateFlag.setCheckable(True)
        self.menuItemAnnotateFlag.setChecked(False)
        self.menuItemAnnotateFlag.setEnabled(True)

        self.menuItemAnnotateCircle = annomode.addAction('Annotate outline (circle)', partial(self.setUIMode, UIMainMode.MODE_ANNOTATE_CIRCLE))
        self.menuItemAnnotateCircle.setCheckable(True)
        self.menuItemAnnotateCircle.setChecked(False)
        self.menuItemAnnotateCircle.setEnabled(True)
