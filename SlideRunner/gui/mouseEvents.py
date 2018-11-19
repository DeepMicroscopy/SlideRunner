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


from SlideRunner.gui.types import *
from PyQt5.QtWidgets import QMenu
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QWheelEvent
from functools import partial
import numpy as np
import matplotlib.path as path
import cv2
from SlideRunner.gui import annotation as GUIannotation
from SlideRunner.general import SlideRunnerPlugin

def doubleClick(self, event):
    """
        Doubleclick event on the main image
    """
    if (self.ui.mode==UIMainMode.MODE_ANNOTATE_POLYGON):
        menu = QMenu(self)
        addmenu = menu.addMenu('Annotate as:')
        menuitems = list()
        for clsname in self.db.getAllClasses():
            act=addmenu.addAction(clsname[0],partial(GUIannotation.addPolygonAnnotation,self,clsname[1], event))
            menuitems.append(act)
        addmenu = menu.addAction('Cancel', self.hitEscape)

        action = menu.exec_(self.mapToGlobal(event.pos()))

def wheelEvent(self, event: QWheelEvent):
    """
        WheelEvent is the callback for wheel events of the operating system.
        Dependent on the OS, this can be a trackpad or a mouse wheel
    """

    if not (self.imageOpened):
        return
    
    # Disable wheel if x position is leaving image compartment
    if (event.x()>self.ui.verticalScrollBar.pos().x()):
        return

    if (event.source() == Qt.MouseEventSynthesizedBySystem):
        # touch pad geasture - use direct scrolling, not zooming
        # this is usually indicative for Mac OS
        subs = np.asarray([float(event.pixelDelta().x()), float(event.pixelDelta().y())])/32000.0*self.getZoomValue()
        self.relativeCoords -= subs
        if (self.relativeCoords[0]<-0.5):
            self.relativeCoords[0]=-0.5

        if (self.relativeCoords[1]<-0.5):
            self.relativeCoords[1]=-0.5

        
    else: # mouse wheel - use scrolling
        inc = 1
        if (event.angleDelta().y()>0):
            inc = -1
        self.setZoomValue(self.getZoomValue() * np.power(1.25, -inc))
    
    self.showImage()
    self.updateScrollbars()


def moveImage(self, event):
    """
        Mouse move event on the main image
    """

    if not (self.imageOpened):
        return

    # Move image if shift+left click
    modifiers = QtWidgets.QApplication.keyboardModifiers()
    posx,posy = getMouseEventPosition(self, event)
    if (modifiers == Qt.ShiftModifier) or (self.ui.clickToMove):
        self.setCursor(Qt.ClosedHandCursor)
        cx,cy = self.screenToSlide((posx,posy))
        anno_abs = self.screenToSlide(self.ui.anno_pt1)
        offsetx = anno_abs[0]-cx           
        offsety = anno_abs[1]-cy           
        image_dims=self.slide.level_dimensions[0]
        self.relativeCoords += np.asarray([offsetx/image_dims[0], offsety/image_dims[1]])
        self.ui.anno_pt1 = (posx,posy)

        self.updateScrollbars()
        self.showImage()
    else:
        self.setCursor(Qt.ArrowCursor)

    if (self.ui.mode == UIMainMode.MODE_ANNOTATE_AREA) & (self.ui.annotationMode>0):
        self.ui.annotationMode=2
        tempimage = np.copy(self.displayedImage)
        pt2 = (posx,posy)

        cv2.rectangle(img=tempimage, pt1=self.ui.anno_pt1, pt2=pt2, thickness=2, color=[127,127,127,255])

        self.ui.MainImage.setPixmap(QPixmap.fromImage(self.toQImage(tempimage)))
    if (self.ui.mode == UIMainMode.MODE_ANNOTATE_CIRCLE) & (self.ui.annotationMode>0):
        self.ui.annotationMode=2
        tempimage = np.copy(self.displayedImage)
        pt2 = (posx,posy)
        radius = int(np.sqrt(np.square(pt2[1]-self.ui.anno_pt1[1])+np.square(pt2[0]-self.ui.anno_pt1[0])))
        cv2.circle(img=tempimage, center=self.ui.anno_pt1, radius=radius, thickness=2, color=[127,127,127,255])

        self.ui.MainImage.setPixmap(QPixmap.fromImage(self.toQImage(tempimage)))

    if not (modifiers == Qt.ShiftModifier) and (self.ui.mode == UIMainMode.MODE_ANNOTATE_POLYGON) & (self.ui.annotationMode>0):
        self.ui.moveDots+=1
        self.ui.annotationsList.append(self.screenToSlide(getMouseEventPosition(self,event)))            
        self.showImage()



def leftClickImage(self, event):
        """
            Callback function for a left click in the main image
        """
        if not (self.imageOpened):
            return

        posx, posy = getMouseEventPosition(self, event)
        self.ui.clickToMove = False
        # Move image if shift+left click
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if (modifiers == Qt.ShiftModifier) or (self.db.isOpen() == False):
            self.ui.clickToMove = True
            self.ui.anno_pt1 = (posx,posy)
            self.setCursor(Qt.ClosedHandCursor)
            return

        if not (self.db.isOpen()):
            return
        
        mouseClickGlobal = self.screenToSlide((posx,posy))

        clickedAnno = self.db.findClickAnnotation(mouseClickGlobal, self.currentVP)
        if (clickedAnno is not None):
            self.showDBEntry(clickedAnno)
        
        if clickedAnno is not None and (self.ui.mode == UIMainMode.MODE_ANNOTATE_SPOT):
            # fast annotation on previous anno
            # check: did I annotate this item already?
            if (self.db.checkIfAnnotatorLabeled(clickedAnno.uid, self.retrieveAnnotator(event))):
                menu = QMenu(self)
                addmenu = menu.addMenu('Add another label')
                menuitems = list()
                for clsname in self.db.getAllClasses():
                    act=addmenu.addAction(clsname[0],partial(self.addAnnotationLabel, clsname[1], event, clickedAnno.uid))
                    menuitems.append(act)
                action = menu.exec_(self.mapToGlobal(event.pos()))
            else:
                self.db.addAnnotationLabel(self.lastAnnotationClass, self.retrieveAnnotator(event), clickedAnno.uid)
                self.writeDebug('new label for object with class %d, slide %d, person %d' % ( self.lastAnnotationClass, self.slideUID,self.retrieveAnnotator(event)))
                self.saveLastViewport()                
                if (self.discoveryMode):
                    self.discoverUnclassified()
                else:
                    self.showImage()

        if clickedAnno is None and (self.ui.mode==UIMainMode.MODE_VIEW):
            # Move image
            self.ui.anno_pt1 = (posx,posy)
            self.ui.clickToMove = True
            self.setCursor(Qt.ClosedHandCursor)


        if clickedAnno is None and (self.ui.mode == UIMainMode.MODE_ANNOTATE_SPOT):
            if (self.lastAnnotationClass==0):
                menu = QMenu(self)
                addmenu = menu.addMenu('Add annotation')
                menuitems = list()
                for clsname in self.db.getAllClasses():
                    act=addmenu.addAction(clsname[0],partial(GUIannotation.addSpotAnnotation,self, clsname[1], event))
                    menuitems.append(act)

                action = menu.exec_(self.mapToGlobal(event.pos()))
                
            else:
                # Fast annotation mode. Just add GUIannotation.
                GUIannotation.addSpotAnnotation( self, self.lastAnnotationClass, event)

        if (self.ui.mode == UIMainMode.MODE_ANNOTATE_FLAG):
                GUIannotation.addSpotAnnotation( self, None, event, typeAnno=4)
            
        
        if (self.ui.mode == UIMainMode.MODE_ANNOTATE_AREA) or (self.ui.mode == UIMainMode.MODE_ANNOTATE_CIRCLE):
            # Normal rectangular or circular GUIannotation. 
            self.ui.annotationMode=1
            self.ui.anno_pt1 =  getMouseEventPosition(self, event)
        
        if (self.ui.mode == UIMainMode.MODE_ANNOTATE_POLYGON):
            if (self.ui.annotationMode == 0):
                self.ui.annotationsList = list()
                self.ui.annotationMode=1
                self.ui.moveDots=0
            self.ui.annotationsList.append(self.screenToSlide(getMouseEventPosition(self,event)))            
            self.showImage()

def getMouseEventPosition(self,event):
    """
        Retrieves the current position of a mouse pointer event
    """
    pos = (int(event.localPos().x()), int(event.localPos().y()))
    return pos



def releaseImage(self, event):
    """
        Callback function for a mouse release event in the main image
    """
    self.ui.clickToMove = False
    self.setCursor(Qt.ArrowCursor)
    if (self.ui.mode == UIMainMode.MODE_ANNOTATE_AREA) & (self.ui.annotationMode>1):
        self.ui.annotationMode=0        
        if (self.lastAnnotationClass == 0):
            menu = QMenu(self)
            addmenu = menu.addMenu('Annotate as:')
            menuitems = list()
            for clsname in self.db.getAllClasses():
                act=addmenu.addAction(clsname[0],partial(GUIannotation.addAreaAnnotation,self, clsname[1], event))
                menuitems.append(act)

            action = menu.exec_(self.mapToGlobal(event.pos()))
            self.showImage()
        else:
            GUIannotation.addAreaAnnotation(self, self.lastAnnotationClass, event)
            self.showImage()

    if (self.ui.mode == UIMainMode.MODE_ANNOTATE_CIRCLE) & (self.ui.annotationMode>1):
        self.ui.annotationMode=0        
        menu = QMenu(self)
        if (self.lastAnnotationClass == 0):
            addmenu = menu.addMenu('Annotate as:')
            menuitems = list()
            for clsname in self.db.getAllClasses():
                act=addmenu.addAction(clsname[0],partial(GUIannotation.addCircleAnnotation,self, clsname[1], event))
                menuitems.append(act)

            action = menu.exec_(self.mapToGlobal(event.pos()))
        else:
            GUIannotation.addCircleAnnotation(self, self.lastAnnotationClass, event)
        self.showImage()

def removeLastPolygonPoint(self):
    if (self.ui.annotationMode == 1):
        self.ui.annotationsList.pop()           
        self.showImage()


def rightClickImage(self, event):
    """
        Global callback for right click events.
        Dependent on the current mode, the menu displayed has different options. 
    """

    menu = QMenu(self)

    posx,posy = getMouseEventPosition(self, event)

    annoIsFlag=False

    if (self.db.isOpen()):


        if (self.ui.mode==UIMainMode.MODE_ANNOTATE_POLYGON):
            menu = QMenu(self)
            addmenu = menu.addMenu('Annotate as:')
            menuitems = list()
            for clsname in self.db.getAllClasses():
                act=addmenu.addAction(clsname[0],partial(GUIannotation.addPolygonAnnotation,self,clsname[1], event))
                menuitems.append(act)
            addmenu = menu.addAction('Remove last point', partial(self.removeLastPolygonPoint,self))
            addmenu = menu.addAction('Cancel', self.hitEscape)


            action = menu.exec_(self.mapToGlobal(event.pos()))
            return

        mouseClickGlobal = self.screenToSlide((posx,posy))
        clickedAnno = self.db.findClickAnnotation(mouseClickGlobal, self.currentVP)


        menuitems = list()
        if (clickedAnno is None):
            addmenu = menu.addMenu('Add annotation')
            menuitems = list()
            for clsname in self.db.getAllClasses():
                act=addmenu.addAction(clsname[0],partial(GUIannotation.addSpotAnnotation,self,clsname[1], event))
                menuitems.append(act)
        else:
            labels=self.db.findAllAnnotationLabels(clickedAnno.uid)
            if not (annoIsFlag):
                for labelIdx in range(len(labels)):
                    label = labels[labelIdx]
                    addmenu = menu.addMenu('Change %s annotation' % self.numberToPosition(labelIdx))
                    for clsname in self.db.getAllClasses():
                        act=addmenu.addAction(clsname[0],partial(self.changeAnnotation,clsname[1], event, label[2], clickedAnno.uid))
                        act.setCheckable(True)
                        if (clsname[1]==label[1]):
                            act.setChecked(True)
                        menuitems.append(act)
                    if (labelIdx>0):
                        act = addmenu.addAction('-- remove --', partial(self.removeAnnotationLabel, label[2],clickedAnno.uid))
                        menuitems.append(act)

                addmenu = menu.addMenu('Add %s annotation' % self.numberToPosition((len(labels))))
                for clsname in self.db.getAllClasses():
                    act = addmenu.addAction(clsname[0], partial(self.addAnnotationLabel, clsname[1], event, clickedAnno.uid))
                    menuitems.append(act)
                menuitems.append(act)
            menu.addAction('Remove annotation', partial(self.removeAnnotation, clickedAnno.uid))

            if (self.activePlugin is not None):
                pluginActionMenu = menu.addMenu('Plugin:'+self.activePlugin.plugin.shortName)
                for pluginConfig in self.activePlugin.plugin.configurationList:
                    if (pluginConfig.type == SlideRunnerPlugin.PluginConfigurationType.ANNOTATIONACTION):
                        pluginActionMenu.addAction(pluginConfig.name, partial(self.sendAnnoToPlugin, clickedAnno, pluginConfig.uid))                        


        menu.addSeparator()
        submenu = menu.addMenu('Annotate as: ')
        for clsname in self.db.getAllPersons():
            act = submenu.addAction(' ' + clsname[0], partial(self.defineAnnotator, clsname[1]))
            act.setCheckable(True)
            if (self.annotator == clsname[1]):
                act.setChecked(True)

    if (self.screeningMode):
        menu.addSeparator()
        submenu = menu.addMenu('Guided screening ')
        act = submenu.addAction('reset and continue from top', self.resetGuidedScreening)
        act = submenu.addAction('continue from here', partial(self.redefineScreeningLastUpper))
        

    action = menu.exec_(self.mapToGlobal(event.pos()))

def pressImage(self, event):
    """
        Callback function for a click on the main image
    """
    if (event.button() == Qt.LeftButton):
            leftClickImage(self,event)
    elif (event.button()==Qt.RightButton):
            rightClickImage(self,event)

