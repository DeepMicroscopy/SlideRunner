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

from SlideRunner.gui.types import *
from PyQt5.QtWidgets import QMenu
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from functools import partial
import numpy as np
import matplotlib.path as path
import cv2
from SlideRunner.gui import annotation as GUIannotation

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

def wheelEvent(self, event):
    """
        WheelEvent is the callback for wheel events of the operating system.
        Dependent on the OS, this can be a trackpad or a mouse wheel
    """

    if not (self.imageOpened):
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
    posx,posy = self.getMouseEventPosition(event)
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

    if (self.ui.mode == UIMainMode.MODE_ANNOTATE_POLYGON) & (self.ui.annotationMode>0):
        self.ui.moveDots+=1
        self.ui.annotationsList.append(self.screenToSlide(self.getMouseEventPosition(event)))            
        self.showImage()



def leftClickImage(self, event):
        """
            Callback function for a left click in the main image
        """
        posx, posy = self.getMouseEventPosition(event)
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
        
        # Find annotation
        foundAnno=None
        for annotation in self.annotationsFlags:
            dist = np.sqrt(np.square(annotation[0]-posx)+np.square(annotation[1]-posy))
            if (dist < (annotation[2]+3)):
                foundAnno = annotation[5]
                self.showDBEntry(annotation[5], type='flag')
                break

        for annotation in self.annotationsArea:
            if ((annotation[0]<=posx) & (annotation[2]>=posx) & 
                (annotation[1]<=posy) & (annotation[3]>=posy)):
                self.showDBEntry(annotation[5],type='area')
        for annotation in self.annotationsSpots:
            dist = np.sqrt(np.square(annotation[0]-posx)+np.square(annotation[1]-posy))
            if (dist < (annotation[2]+3)):
                # We found a match!
                self.showDBEntry(annotation[5])
                foundAnno=annotation[5]
                break
        for annotation in self.annotationPolygons:
            p = path.Path(annotation[0])
            if (p.contains_point(self.screenToSlide((posx,posy)))):
                self.showDBEntry(annotation[2],type='poly')
                foundAnno=annotation[2]
                break
        
        if foundAnno is not None and (self.ui.mode == UIMainMode.MODE_ANNOTATE_SPOT):
            # fast annotation on previous anno
            # check: did I annotate this item already?
            if (self.db.checkIfAnnotatorLabeled(foundAnno, self.retrieveAnnotator(event))):
                menu = QMenu(self)
                addmenu = menu.addMenu('Add another label')
                menuitems = list()
                for clsname in self.db.getAllClasses():
                    act=addmenu.addAction(clsname[0],partial(self.addAnnotationLabel, self,clsname[1], event, foundAnno))
                    menuitems.append(act)
                action = menu.exec_(self.mapToGlobal(event.pos()))
            else:
                self.db.addAnnotationLabel(self.lastAnnotationClass, self.retrieveAnnotator(event), foundAnno)
                self.writeDebug('new label for object with class %d, slide %d, person %d' % ( self.lastAnnotationClass, self.slideUID,self.retrieveAnnotator(event)))
                self.saveLastViewport()                
                if (self.discoveryMode):
                    self.discoverUnclassified()
                else:
                    self.showImage()

        if not foundAnno and (self.ui.mode==UIMainMode.MODE_VIEW):
            # Move image
            self.ui.anno_pt1 = (posx,posy)
            self.ui.clickToMove = True
            self.setCursor(Qt.ClosedHandCursor)


        if foundAnno is None and (self.ui.mode == UIMainMode.MODE_ANNOTATE_SPOT):
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
            self.ui.anno_pt1 =  self.getMouseEventPosition(event)
        
        if (self.ui.mode == UIMainMode.MODE_ANNOTATE_POLYGON):
            if (self.ui.annotationMode == 0):
                self.ui.annotationsList = list()
                self.ui.annotationMode=1
                self.ui.moveDots=0
            self.ui.annotationsList.append(self.screenToSlide(self.getMouseEventPosition(event)))            
            self.showImage()


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


    if (self.ui.mode==UIMainMode.MODE_ANNOTATE_POLYGON) & (self.ui.moveDots>1):
        menu = QMenu(self)
        addmenu = menu.addMenu('Annotate as:')
        menuitems = list()
        for clsname in self.db.getAllClasses():
            act=addmenu.addAction(clsname[0],partial(GUIannotation.addPolygonAnnotation,self, clsname[1], event))
            menuitems.append(act)
        addmenu = menu.addAction('Cancel', self.hitEscape)

        action = menu.exec_(self.mapToGlobal(event.pos()))


def rightClickImage(self, event):
    """
        Global callback for right click events.
        Dependent on the current mode, the menu displayed has different options. 
    """

    menu = QMenu(self)

    posx,posy = self.getMouseEventPosition(event)

    annoIsFlag=False

    if (self.db.isOpen()):

        annoFound=None
        for annotation in self.annotationsArea:
            if ((annotation[0]<=posx) & (annotation[2]>=posx) & 
                (annotation[1]<=posy) & (annotation[3]>=posy)):
                annoFound=annotation
                break



        for annotation in self.annotationsSpots:
            dist = np.sqrt(np.square(annotation[0]-posx)+np.square(annotation[1]-posy))
            if (dist < (annotation[2]+3)):
                # We found a match!
                annoFound=annotation

                break

        for annotation in self.annotationPolygons:
            p = path.Path(annotation[0])
            if (p.contains_point(self.screenToSlide((posx,posy)))):
                annoFound=[0,0,0,0,annotation[1],annotation[2]]
                break

        for annotation in self.annotationsFlags:
            dist = np.sqrt(np.square(annotation[0]-posx)+np.square(annotation[1]-posy))
            if (dist < (annotation[2]+3)):
                annoFound=annotation
                annoIsFlag = True
                break


        menuitems = list()
        if (annoFound is None):
            addmenu = menu.addMenu('Add annotation')
            menuitems = list()
            for clsname in self.db.getAllClasses():
                act=addmenu.addAction(clsname[0],partial(GUIannotation.addSpotAnnotation,self,clsname[1], event))
                menuitems.append(act)
        else:
            labels=self.db.findAllAnnotationLabels(annoFound[5])
            if not (annoIsFlag):
                for labelIdx in range(len(labels)):
                    label = labels[labelIdx]
                    addmenu = menu.addMenu('Change %s annotation' % self.numberToPosition(labelIdx))
                    for clsname in self.db.getAllClasses():
                        act=addmenu.addAction(clsname[0],partial(self.changeAnnotation,clsname[1], event, label[2], annoFound[5]))
                        act.setCheckable(True)
                        if (clsname[1]==label[1]):
                            act.setChecked(True)
                        menuitems.append(act)
                    if (labelIdx>0):
                        act = addmenu.addAction('-- remove --', partial(self.removeAnnotationLabel, label[2],annoFound[5]))
                        menuitems.append(act)

                addmenu = menu.addMenu('Add %s annotation' % self.numberToPosition((len(labels))))
                for clsname in self.db.getAllClasses():
                    act = addmenu.addAction(clsname[0], partial(self.addAnnotationLabel, clsname[1], event, annoFound[5]))
                    menuitems.append(act)
                menuitems.append(act)
            menu.addAction('Remove annotation', partial(self.removeAnnotation, annoFound[5]))


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

