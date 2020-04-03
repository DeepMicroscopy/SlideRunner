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

import numpy as np
from SlideRunner.gui import mouseEvents as mouseEvents
from PyQt5 import QtWidgets
from PyQt5.QtGui import QColor
from SlideRunner.dataAccess.database import hex_to_rgb, rgb_to_hex
from shapely.geometry import * 


def addSpotAnnotation(self, classID, event, typeAnno=1):
    self.saveLastViewport()
    pos_image = mouseEvents.getMouseEventPosition(self,event)

    p1 = self.region[0]
    xpos_orig = int(pos_image[0] * self.getZoomValue() + p1[0])
    ypos_orig = int(pos_image[1] * self.getZoomValue() + p1[1])
    annotation = [xpos_orig, ypos_orig]
    if (classID is not None):
        self.lastAnnotationClass = classID
        self.showAnnoclass()
        self.writeDebug('added object center annotation of class %d, slide %d, person %d' % ( classID, self.slideUID,self.retrieveAnnotator(event)))
    xpos = int((annotation[0] - p1[0]) / self.getZoomValue())
    
    self.db.insertNewSpotAnnotation(xpos_orig,ypos_orig, self.slideUID, classID,self.retrieveAnnotator(event), type=typeAnno )
    self.showDBentryCount()
    self.showImage()

    self.showAnnotationsInOverview()

def renameClass(self, classID, event = None):
    text = self.db.getClassByID(classID)
    name, ok = QtWidgets.QInputDialog.getText(self, "Please give a new name for the new category",
                                        "Name:", text=text)
    if (ok):
        self.db.renameClass(classID, name)
        self.showDatabaseUIelements()

def changeClassColor(self,oldcolor, classID, event = None):
    text = self.db.getClassByID(classID)
    replyCol = QtWidgets.QColorDialog.getColor(QColor.fromRgb(*hex_to_rgb(oldcolor)))

    if (replyCol.isValid()):
        self.db.setClassColor(classID, rgb_to_hex([replyCol.red(), replyCol.green(), replyCol.blue()]))
        self.showDatabaseUIelements()
        self.showImage()


def deleteClass(self, classID, event = None):
    text = self.db.getClassByID(classID)
    reply = QtWidgets.QMessageBox.question(self, 'Question',
                                    'Do you really wish to delete this class and all of its objects?', QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

    if reply == QtWidgets.QMessageBox.No:
        return

    self.db.deleteClass(classID)
    self.showDatabaseUIelements()


def deleteAllFromClassOnSlide(self, classID, event = None):
    if not (self.db.isOpen()):
        return

    reply = QtWidgets.QMessageBox.question(self, 'Question',
                                    'Do you really wish to delete all objects of this class from the current slide?', QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

    if reply == QtWidgets.QMessageBox.No:
        return


    deletekeys=[]
    for annoIdx in self.db.annotations.keys():
        anno = self.db.annotations[annoIdx]
        if (anno.majorityLabel()==classID):
            deletekeys.append(anno.uid)
    for uid in deletekeys:
        self.db.removeAnnotation(uid)

    self.showDBentryCount()
    self.showImage()

def copyAllAnnotations(self, pluginAnnoClass, classID, event = None):
    if not (self.db.isOpen()) or (self.activePlugin == None):
        return
    
    annos = self.activePlugin.instance.getAnnotationsOfLabel(pluginAnnoClass)

    reply = QtWidgets.QMessageBox.question(self, 'Question',
                                    'Do you really wish to copy %d annotation items of this class to the database?' % len(annos), QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

    if reply == QtWidgets.QMessageBox.No:
        return
    
    for pluginAnno in annos:
        self.db.addAnnotationToDatabase(pluginAnno, slideUID=self.slideUID, classID=classID, annotatorID=self.retrieveAnnotator(event), description=pluginAnno.text)
    
    self.showImage()
    self.showDBentryCount()

def copyAnnotation(self,pluginAnno, classID,event):
    self.db.addAnnotationToDatabase(pluginAnno, slideUID=self.slideUID, classID=classID, annotatorID=self.retrieveAnnotator(event), description=pluginAnno.text)
    self.db.loadIntoMemory(slideId=self.slideUID)
    self.showImage()
    self.showDBentryCount()

def addPolygonAnnotation(self,classID,event, annoList):
    """
        Polygon annotation is ready. Add to database.
    """
    self.saveLastViewport()
    if (self.ui.annotationMode==2): #replace polygon object
         self.writeDebug('extended polygon annotation of class %d, slide %d, person %d' % ( classID, self.slideUID,self.retrieveAnnotator(event)))
         self.db.exchangePolygonCoordinates(self.ui.annotationUID, self.slideUID, annoList)
         self.db.annotations[self.ui.annotationUID].deleted=False # make visible again
    else:
        self.writeDebug('added polygon annotation of class %d, slide %d, person %d' % ( classID, self.slideUID,self.retrieveAnnotator(event)))
        self.db.insertNewPolygonAnnotation(annoList,
                                    self.slideUID,classID, self.retrieveAnnotator(event))
    self.ui.annotationMode=0
    self.showImage()
    self.showAnnotationsInOverview()
    self.showDBentryCount()

def addToPolygon(self, annotation, annoList):

    p1 = Polygon(np.array(annotation.convertToPath().vertices))
    p2 = Polygon(np.array(annoList))

    try:
        unionPolygon = p1.union(p2).exterior.coords.xy
    except:
        reply = QtWidgets.QMessageBox.about(self, "Error", 'Polygon union did not work. Sorry!')
        return

    unionCoords = np.float32(np.c_[unionPolygon[0],unionPolygon[1]])

    self.db.exchangePolygonCoordinates(annotation.uid, self.slideUID, unionCoords)
    self.ui.annotationMode=0
    self.showImage()

def removeFromPolygon(self, annotation, annoList):

    p1 = Polygon(annotation.convertToPath().vertices)
    p2 = Polygon(annoList)

    try:
        diffPolygon = p1.difference(p2)
    except:
        reply = QtWidgets.QMessageBox.about(self, "Error", 'Polygon difference did not work. Sorry!')
        return

    if isinstance(diffPolygon, Polygon) and not isinstance(diffPolygon.exterior.coords, list):
        diffPolyCoords = diffPolygon.exterior.coords.xy 

        unionCoords = np.float32(np.c_[diffPolyCoords[0],diffPolyCoords[1]])

        self.db.exchangePolygonCoordinates(annotation.uid, self.slideUID, unionCoords)
        self.ui.annotationMode=0
        self.showImage()
    else:
        reply = QtWidgets.QMessageBox.about(self, "Error", 'Polygon difference reported no single polygon as output.')
        

def addCircleAnnotation(self, classID, event):
    self.saveLastViewport()
    pt2 = mouseEvents.getMouseEventPosition(self,event)
    x1 = min(pt2[0],self.ui.anno_pt1[0])
    x2 = max(pt2[0],self.ui.anno_pt1[0])
    y1 = min(pt2[1],self.ui.anno_pt1[1])
    y2 = max(pt2[1],self.ui.anno_pt1[1])

    pos_image = mouseEvents.getMouseEventPosition(self,event)
    leftUpper = self.region[0]
    xpos_orig_1 = int(x1 * self.getZoomValue() + leftUpper[0])
    ypos_orig_1 = int(y1 * self.getZoomValue() + leftUpper[1])
    xpos_orig_2 = int(x2 * self.getZoomValue() + leftUpper[0])
    ypos_orig_2 = int(y2 * self.getZoomValue() + leftUpper[1])

    center_x = int(self.ui.anno_pt1[0] * self.getZoomValue() + leftUpper[0])
    center_y = int(self.ui.anno_pt1[1] * self.getZoomValue() + leftUpper[1])

    radius = int(self.getZoomValue() * np.sqrt(np.square(pt2[0]-self.ui.anno_pt1[0])+np.square(pt2[1]-self.ui.anno_pt1[1])))

    xpos_orig_1 = center_x-radius
    xpos_orig_2 = center_x+radius
    ypos_orig_1 = center_y-radius
    ypos_orig_2 = center_y+radius

    self.lastAnnotationClass = classID
    self.showAnnoclass()

    self.db.insertNewAreaAnnotation(xpos_orig_1,ypos_orig_1,xpos_orig_2,ypos_orig_2,
                                self.slideUID,classID, self.retrieveAnnotator(event), 5)

    self.showDBentryCount()
    self.showImage()
    self.showAnnotationsInOverview()
    self.writeDebug('added circle annotation of class %d, slide %d, person %d' % ( classID, self.slideUID,self.retrieveAnnotator(event)))


def addAreaAnnotation(self, classID, event):
    self.saveLastViewport()
    pt2 = mouseEvents.getMouseEventPosition(self,event)
    x1 = min(pt2[0],self.ui.anno_pt1[0])
    x2 = max(pt2[0],self.ui.anno_pt1[0])
    y1 = min(pt2[1],self.ui.anno_pt1[1])
    y2 = max(pt2[1],self.ui.anno_pt1[1])

    pos_image = mouseEvents.getMouseEventPosition(self,event)
    leftUpper = self.region[0]
    xpos_orig_1 = int(x1 * self.getZoomValue() + leftUpper[0])
    ypos_orig_1 = int(y1 * self.getZoomValue() + leftUpper[1])
    xpos_orig_2 = int(x2 * self.getZoomValue() + leftUpper[0])
    ypos_orig_2 = int(y2 * self.getZoomValue() + leftUpper[1])

    self.lastAnnotationClass = classID
    self.showAnnoclass()

    self.db.insertNewAreaAnnotation(xpos_orig_1,ypos_orig_1,xpos_orig_2,ypos_orig_2,
                                self.slideUID,classID, self.retrieveAnnotator(event))

    self.showDBentryCount()
    self.showImage()
    self.showAnnotationsInOverview()
    self.showDBentryCount()
    self.writeDebug('added area annotation of class %d, slide %d, person %d' % ( classID, self.slideUID,self.retrieveAnnotator(event)))
