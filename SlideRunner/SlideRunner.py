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



        Prerequisites:
            Package             Tested version
            openslide           1.1.1
            cv2                 opencv3-3.1.0
            pyqt                pyqt5-5.5.0
            sqlite3             2.6.0
            matplotlib          2.0.0



"""
#####################################################
#
#
#
#
#
#
#

# This script expects images in the folder images/unclassified and sorts
# them into images/[ClassName] folders.


version = '1.8.0'

SLIDERUNNER_DEBUG = False

from SlideRunner.general import dependencies
import sys

dependencies.check_qt_dependencies()

from PyQt5 import QtWidgets, QtGui, QtCore
from SlideRunner.gui import splashScreen, menu, style
from PyQt5.QtWidgets import QMainWindow

app = QtWidgets.QApplication(sys.argv)
splash = splashScreen.splashScreen(app, version)

# Splash screen is displayed, go on with the rest.

from SlideRunner.general.dependencies import *

class SlideRunnerUI(QMainWindow):
    progressBarChanged = pyqtSignal(int)
    showImageRequest = pyqtSignal()
    annotator = bool # ID of curent annotator
    db = Database()

    def __init__(self):
        super(SlideRunnerUI, self).__init__()
        # Default value initialization
        self.relativeCoords = np.asarray([0,0], np.float32)
        self.colors = [[0,0,0,0],[0,0,255,255],[0,255,0,255],[255,255,0,255],[255,0,255,255],[0,127,0,255],[255,127,0,255],[0,0,0,255],[255,255,255,255]]
        self.lastAnnotationClass=0
        self.imageOpened=False # flag, if 
        self.annotator=0 # ID of current annotator
        self.eventIntegration=0
        # Set up the user interface from Designer.
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.moveDots=0
        self.currentZoom = 1
        self.annotationsSpots=list()
        self.annotationsArea = list()
        self.annotationsCircle = list()
        self.annotationsList = list()
        self.slidename=''
        self.slideUID = 0
        self.ui.annotationMode = 0
        self.annotatorsModel = QStringListModel()
        self.classButtons = list()
        self.updateTimer = None
        self.displayedImage = None
        self.overviewOverlayHeatmap = False
        self.annotationPolygons=[]
        self.ui.statisticView.setHidden(True)
        self.ui.MainImage.installEventFilter(self)
        self.ui.horizontalScrollBar.valueChanged.connect(self.changeScrollbars)
        self.ui.verticalScrollBar.valueChanged.connect(self.changeScrollbars)
        self.ui.opacitySlider.setValue(40)
        self.ui.opacitySlider.valueChanged.connect(self.changeOpacity)
        self.ui.threshold.valueChanged.connect(self.changeOpacity)

        self.ui.progressBar.setHidden(True)

        self.ui.progressBar.setValue(0)

        self.wheelEvent = partial(mouseEvents.wheelEvent,self)

        shortcuts.defineMenuShortcuts(self)

        self.ui.MainImage.setPixmap(self.vidImageToQImage(127*np.ones((600,600,3),np.uint8)))
        self.ui.MainImage.mousePressEvent = partial(mouseEvents.pressImage, self)
        self.ui.MainImage.mouseReleaseEvent = partial(mouseEvents.releaseImage, self)
        self.ui.MainImage.mouseMoveEvent = partial(mouseEvents.moveImage,self)
        self.ui.MainImage.mouseDoubleClickEvent = partial(mouseEvents.doubleClick,self)
        self.ui.OverviewLabel.setPixmap(self.vidImageToQImage(127*np.ones((200,200,3),np.uint8)))
        self.opacity = 0.4
        self.mainImageSize = np.asarray([self.ui.MainImage.frameGeometry().width(),self.ui.MainImage.frameGeometry().height()])
        self.ui.OverviewLabel.mousePressEvent = self.pressOverviewImage

        self.ui.opacitySlider.setHidden(True)
        self.ui.opacityLabel.setHidden(True)
        self.ui.threshold.setHidden(True)
        self.ui.threshold_label.setHidden(True)

        menu.defineAnnotationMenu(self)

        if (SLIDERUNNER_DEBUG):
            self.logger = logging.getLogger()
            self.logger.setLevel(logging.DEBUG)
            self.loggerFileHandle = logging.FileHandler('SlideRunner.log')
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            self.loggerFileHandle.setLevel(logging.DEBUG)
            self.loggerFileHandle.setFormatter(formatter)
            self.logger.addHandler(self.loggerFileHandle)
            self.writeDebug('Startup, version %s' % version)

        toolbar.defineToolbar(self)

        self.blindedMode = False
        self.screeningMap = None
        self.discoveryMode = False
        self.ui.filenameLabel.setHidden(True)
        self.ui.actionAbout.triggered.connect( partial(aboutDialog,app, version))

        self.shortcuts = shortcuts.defineShortcuts(self)

        self.lastScreeningLeftUpper = np.zeros(2)

        self.ui.mode=UIMainMode.MODE_VIEW
        self.ui.overlayHeatmap = 0
        self.screeningMode = 0
        self.ui.menubar.setEnabled(True)
        self.ui.menubar.setNativeMenuBar(False)

        self.imageProcessingQueue = queue.Queue()
        self.imageOutQueue = queue.Queue()


        if (len(sys.argv)>1):
            if os.path.isfile(sys.argv[1]):
                self.openSlide(sys.argv[1])

        

    class NotImplementedException:
        pass


    """
    Signal that we accept drag&drop for files, and show the link icon.
    """

    def setProgressBar(self, number):
        if (number == -1):
            self.ui.progressBar.setHidden(True)
        else:
            self.ui.progressBar.setValue(number)
            self.ui.progressBar.setHidden(False)

    def dragEnterEvent(self, e):
         if (e.mimeData().hasUrls()):
            e.setDropAction(QtCore.Qt.LinkAction)
            e.accept()
         else:
            e.ignore() 

    """
    Helper function to reset screening completely
    """

    def resetGuidedScreening(self):
            self.lastScreeningLeftUpper = np.zeros(2)
            self.screeningMap.reset()
            self.nextScreeningStep()

    """

    Helper function for the screening mode. Redefines the last position for screening.
    
    """

    def redefineScreeningLastUpper(self):
        if not (self.imageOpened):
            return

        if not (self.screeningMode):
            return

        relOffset_x = self.mainImageSize[0] / self.slide.level_dimensions[0][0]
        relOffset_y =  self.mainImageSize[1] / self.slide.level_dimensions[0][1]



        self.lastScreeningLeftUpper[0] = self.relativeCoords[0]-relOffset_x+0.5
        self.lastScreeningLeftUpper[1] = self.relativeCoords[1]-relOffset_y+0.5

    """

        Function to jump to next piece in screening map that has not been covered yet.

    """


    def nextScreeningStep(self):
        if not (self.imageOpened):
            return

        if not (self.screeningMode):
            return

        self.writeDebug('Next screen in screening mode')

        relOffset_x = self.mainImageSize[0] / self.slide.level_dimensions[0][0]
        relOffset_y =  self.mainImageSize[1] / self.slide.level_dimensions[0][1]

        newImageFound=False
        # find next image in grid. 
        while (not newImageFound):
            # advance one step to the right

            # Find next open spot in current row, if not, advance rows until one is found
            self.lastScreeningLeftUpper[0] += relOffset_x*0.9

            if (self.lastScreeningLeftUpper[0] > 1):
                self.lastScreeningLeftUpper[1] += relOffset_y*0.9
                self.lastScreeningLeftUpper[0] = 0

            if (self.lastScreeningLeftUpper[1] > 1):
                self.ui.iconScreening.setEnabled(False)
                reply = QtWidgets.QMessageBox.information(self, 'Message',
                           'All image parts have been covered. Thank you!', QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)
                return

            if (self.screeningMap.checkIsNew(self.lastScreeningLeftUpper)):
                newImageFound=True

        # there is at least one pixel that was not covered
        leftupper_x = self.lastScreeningLeftUpper[0]
        leftupper_y = self.lastScreeningLeftUpper[1]

        center = ( leftupper_x+relOffset_x/2, leftupper_y+relOffset_y/2)

        self.setCenterTo( (leftupper_x+relOffset_x/2)*self.slide.level_dimensions[0][0], (leftupper_y+relOffset_y/2)*self.slide.level_dimensions[0][1])
        self.showImage()

    
    """
        Start or stop the guided screening mode.

    """

    def startStopScreening(self):
        if not (self.imageOpened):
            return
        self.screeningMode = self.ui.iconScreening.isChecked()
        self.ui.iconNextScreen.setEnabled(self.screeningMode)

        if (self.screeningMode):
            self.setZoomValue(1.0) # no magnification
            self.setCenterTo(0+self.mainImageSize[0]/2,+self.mainImageSize[1]/2)
            self.showImage()
    
        self.writeDebug('Screening mode: %d' % self.screeningMode)

    """
        Helper function to go back to last view area. This is handy in 
        the discovery mode, when the screen moved automatically.
    """

    def backToLastAnnotation(self):
        self.relativeCoords = np.copy(self.lastviewport_center)
        self.setZoomValue(np.copy(self.lastviewport_zoom))
        self.showImage()

    """
        Save the last view area to be able to return to this. This is done
        in case an annotation is set.
    """

    def saveLastViewport(self):
        self.ui.iconBack.setEnabled(True)
        self.lastviewport_center = np.copy(self.relativeCoords)
        self.lastviewport_zoom = np.copy(self.getZoomValue())

    """
        Helper function to zoom out.
    """

    def zoomOut(self):
        self.setZoomValue(self.getZoomValue() * 1.25)
        self.showImage()

    """
        Helper function to zoom in.
    """

    def zoomIn(self):
        self.setZoomValue(self.getZoomValue() / 1.25)
        self.showImage()


    def setOverlayHeatmap(self):
        self.overviewOverlayHeatmap = self.ui.iconOverlay.isChecked()
        self.showImage()


    """
        Discover annotations unclassified by current viewer. The outer 
        50 pixels of the screen are discarded, since annotations might be
        only partially shown.
    """
    def discoverUnclassified(self):

        if not (self.db.isOpen()): 
            return

        leftUpper = self.region[0] 
        leftUpper[0] += 50
        leftUpper[1] += 50
        rightLower = self.region[0] + self.region[1] - (50,50)
        rightLower[0] -= 50
        rightLower[1] -= 50
        
        if not (self.db.checkIfUnknownAreInScreen(leftUpper,rightLower,self.slideUID, self.annotator)):
            [cx,cy,anno] = self.db.pickRandomUnlabeled(self.slideUID, 1, self.annotator)
            if (anno is not None):
                self.setCenterTo(cx,cy)
            else:
                # All spot annotations seem to be done, continue with polygons
                [cx,cy,anno] = self.db.pickRandomUnlabeled(self.slideUID, 3, self.annotator)
                if (anno is not None):
                    coords = np.asarray(self.db.findAllAnnotations(anno))
                    minC = np.min(coords,axis=0)
                    maxC = np.max(coords,axis=0)
                    diff = maxC-minC
                    cent = np.int32(minC+(maxC-minC)/2)
                    self.setCenterTo(cent[0],cent[1])
                    self.setZoomTo(diff[0],diff[1])
                else:
                    reply = QtWidgets.QMessageBox.information(self, 'Message',
                                           'All objects have been rated by you. Thanks :)', QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)


        self.showImage()

    def setDiscoveryMode(self):
        self.discoveryMode= self.ui.iconQuestion.isChecked()
        if (self.discoveryMode):
            self.discoverUnclassified()

    def setBlindedMode(self):
        self.modelItems[0].setChecked(True) # enable unknown class
        self.blindedMode = self.ui.iconBlinded.isChecked()
        self.showImage()

    def changeOpacity(self, e):
        self.opacity = self.ui.opacitySlider.value()/self.ui.opacitySlider.maximum()
        self.showImage()

    def dropEvent(self, e):
        """   
             Accept drag&drop for SVS files. 
        """
        for url in e.mimeData().urls():
            filename = str(url.toLocalFile())        
        ext = os.path.splitext(filename)[1]
        if (ext.upper() == '.SVS'):
            e.setDropAction(QtCore.Qt.LinkAction)
            e.accept() 

            self.openSlide(filename)
    
    def hitEscape(self):
        if (self.ui.mode==UIMainMode.MODE_ANNOTATE_POLYGON) & (self.ui.annotationMode>0):
            self.ui.annotationMode=0
            self.showImage()

    def setUIMode(self,mode: UIMainMode):
        self.ui.mode = mode
        self.menuItemAnnotateCenter.setChecked(False)
        self.menuItemView.setChecked(False)
        self.menuItemAnnotateArea.setChecked(False)
        self.menuItemAnnotateOutline.setChecked(False)
        self.menuItemAnnotateFlag.setChecked(False)
        self.ui.iconRect.setChecked(False)
        self.ui.iconView.setChecked(False)
        self.ui.iconCircle.setChecked(False)
        self.ui.iconPolygon.setChecked(False)
        self.ui.iconFlag.setChecked(False)

        if (self.ui.mode == UIMainMode.MODE_VIEW):
            self.menuItemView.setChecked(True)
            self.ui.iconView.setChecked(True)
        elif (self.ui.mode == UIMainMode.MODE_ANNOTATE_SPOT):
            self.menuItemAnnotateCenter.setChecked(True)
            self.ui.iconCircle.setChecked(True)
        elif (self.ui.mode == UIMainMode.MODE_ANNOTATE_AREA):
            self.menuItemAnnotateArea.setChecked(True)
            self.ui.iconRect.setChecked(True)
        elif (self.ui.mode == UIMainMode.MODE_ANNOTATE_POLYGON):
            self.menuItemAnnotateOutline.setChecked(True)
            self.ui.iconPolygon.setChecked(True)
        elif (self.ui.mode == UIMainMode.MODE_ANNOTATE_FLAG):
            self.menuItemAnnotateFlag.setChecked(True)
            self.ui.iconFlag.setChecked(True)

    def toQImage(self, im, copy=False):
        qim = QImage(im.data, im.shape[1], im.shape[0], im.strides[0], QImage.Format_RGBA8888)
        return qim

    def vidImageToQImage(self, cvImg):
        height, width, channel = cvImg.shape
        bytesPerLine = 3 * width
        qImg = QImage(cvImg.data, width, height, QtGui.QImage.Format_RGB888)
        return QtGui.QPixmap.fromImage(qImg)


    def setZoomTo(self,w,h):
        zoom_w = w/self.mainImageSize[0]
        zoom_h = h/self.mainImageSize[1]
        if (zoom_w>zoom_h):
            zoom=zoom_w*1.1
        else:
            zoom=zoom_h*1.1

        self.setZoomValue(zoom)
        self.showImage()

    def setCenterTo(self,cx,cy):
        if (self.imageOpened):

            image_dims=self.slide.level_dimensions[0]
            self.relativeCoords = np.asarray([cx/image_dims[0], cy/image_dims[1]])

            if (self.relativeCoords[1]>1.0):
                self.relativeCoords[1]=1.0

            self.relativeCoords -= 0.5
        

    def pressOverviewImage(self,event):
        if (self.imageOpened):
            self.relativeCoords=np.asarray([event.x()/self.thumbnail.size[0], event.y()/self.thumbnail.size[1]])
            if (self.relativeCoords[1]>1.0):
                self.relativeCoords[1]=1.0

            self.relativeCoords -= 0.5
            self.showImage()
            self.updateScrollbars()

    def eventFilter(self, source, event):

        if not (self.imageOpened):
            return QWidget.eventFilter(self, source, event)
        
        if (isinstance(event,QtGui.QNativeGestureEvent)):
            if (event.gestureType()==QtCore.Qt.BeginNativeGesture):
                self.eventIntegration=0
                self.eventCounter=0

            if (event.gestureType()==QtCore.Qt.ZoomNativeGesture):
                self.eventIntegration+=event.value()
                self.eventCounter+= 1

            if ((event.gestureType()==QtCore.Qt.EndNativeGesture) or
                ((event.gestureType() == QtCore.Qt.ZoomNativeGesture) and (self.eventCounter>5))):
                self.setZoomValue(self.getZoomValue() * np.power(1.25, -self.eventIntegration*5))
                self.eventIntegration = 0
                self.eventCounter = 0
                self.showImage()

        return QWidget.eventFilter(self, source, event)

            

    def getMouseEventPosition(self,event):
        """
            Retrieves the current position of a mouse pointer event
        """
        return (int(event.localPos().x()+2), int(event.localPos().y()))

 
    def writeDebug(self, message):
        if SLIDERUNNER_DEBUG:
            self.logger.debug(message)


    def showPolygon(self, tempimage, polygon, color):
        markersize = 5
        listIdx=-1
        for listIdx in range(len(polygon)-1):
            anno = self.slideToScreen(polygon[listIdx])
            cv2.line(img=tempimage, pt1=anno, pt2=self.slideToScreen(polygon[listIdx+1]), thickness=2, color=color, lineType=cv2.LINE_AA)       

            pt1_rect = (max(0,anno[0]-markersize),
                        max(0,anno[1]-markersize))
            pt2_rect = (min(tempimage.shape[1],anno[0]+markersize),
                        min(tempimage.shape[0],anno[1]+markersize))
            cv2.rectangle(img=tempimage, pt1=(pt1_rect), pt2=(pt2_rect), color=[255,255,255,255], thickness=2)
            cv2.rectangle(img=tempimage, pt1=(pt1_rect), pt2=(pt2_rect), color=color, thickness=1)
        listIdx+=1
        anno = self.slideToScreen(polygon[listIdx])
        pt1_rect = (max(0,anno[0]-markersize),
                    max(0,anno[1]-markersize))
        pt2_rect = (min(tempimage.shape[1],anno[0]+markersize),
                    min(tempimage.shape[0],anno[1]+markersize))
        cv2.rectangle(img=tempimage, pt1=(pt1_rect), pt2=(pt2_rect), color=[255,255,255,255], thickness=2)
        cv2.rectangle(img=tempimage, pt1=(pt1_rect), pt2=(pt2_rect), color=[0,0,0,255], thickness=1)

        return tempimage

    def showDBEntry(self, entryId, type='spot'):
        table_model = QtGui.QStandardItemModel()
        table_model.setColumnCount(2)
        table_model.setHorizontalHeaderLabels("Name;Description".split(";"))

        coords, classes, persons = self.db.fetchSpotAnnotation(entryId)

        lab1 = QStandardItem('Unique ID ')
        item = QStandardItem(str(entryId))
        table_model.appendRow([lab1,item])
        if (type=='spot'):
            lab1 = QStandardItem('Position ')
            item = QStandardItem('x=%d, y=%d' % coords)
            table_model.appendRow([lab1,item])
        elif (type=='flag'):
            lab1 = QStandardItem('Position ')
            item = QStandardItem('x=%d, y=%d' % coords)
            table_model.appendRow([lab1,item])
        elif (type=='area'):
            coords1, coords2, classes, persons= self.db.fetchAreaAnnotation(entryId)
            lab1 = QStandardItem('Position1 ')
            item = QStandardItem('x1=%d, y1=%d' % coords1)
            table_model.appendRow([lab1,item])

            lab1 = QStandardItem('Position2 ')
            item = QStandardItem('x1=%d, y1=%d' % coords2)
            table_model.appendRow([lab1,item])
            
        for k in range(len(classes)):
            lab1 = QStandardItem('Anno %d ' % (k+1))
            item = QStandardItem('%s (%s)' % (classes[k][0], persons[k][0]))
            table_model.appendRow([lab1,item])

        self.ui.tableView.setModel(table_model)
        self.ui.tableView.resizeRowsToContents()



    def defineAnnotator(self, uid):
        self.annotator = uid
        allPers=self.db.getAllPersons()
        for persIdx in range(len(allPers)):
            person=allPers[persIdx]
            if (person[1] == uid):
                self.ui.comboBox.setCurrentIndex(persIdx)
        

    def changeAnnotator(self):
        allPers=self.db.getAllPersons()
        if len(allPers)==0:
            self.annotator = 0
        else:
            self.annotator = allPers[self.ui.comboBox.currentIndex()][1]
        self.showImage()
        


    def retrieveAnnotator(self,event):
        allPers=self.db.getAllPersons()
        if len(allPers)==0:
            return 0
        if (self.annotator<1):
            menu = QMenu(self)
            for clsname in allPers:
                act=menu.addAction('as: '+clsname[0],partial(self.defineAnnotator,clsname[1]))

            action = menu.exec_(self.mapToGlobal(event.pos()))

        return self.annotator

    def numberToPosition(self, number):
        nth = ['1st','2nd','3rd','4th','5th','6th','7th','8th','9th','10th']
        return nth[number]

    def changeAnnotation(self, classId, event, labelIdx, annoId):
        self.db.setAnnotationLabel(classId, self.retrieveAnnotator(event), labelIdx, annoId)
        self.writeDebug('changed label for object with class %d, slide %d, person %d' % ( classId, self.slideUID,self.retrieveAnnotator(event)))
        self.showImage()

    def addAnnotationLabel(self, classId, event, annoId ):
        self.writeDebug('new label for object with class %d, slide %d, person %d' % ( classId, self.slideUID,self.retrieveAnnotator(event)))
        self.db.addAnnotationLabel(classId, self.retrieveAnnotator(event), annoId)
        self.saveLastViewport()
        self.showImage()


    def removeAnnotation(self,annoId):
        """
            Callback if the user wants to remove an annotation
        """
        quit_msg = "Are you sure you want to remove this annotation?"
        reply = QtWidgets.QMessageBox.question(self, 'Message',
                                           quit_msg, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            self.db.removeAnnotation(annoId)
            self.showImage()



    def removeAnnotationLabel(self, labelId, annoId):
        """
            Callback for removal of an annotation of a label 
        """
        self.db.removeAnnotationLabel(labelId,annoId)

    
    def screenToSlide(self,co):
        """
            convert screen coordinates to slide coordinates
        """
        p1 = self.region[0]
        xpos = int(co[0] * self.getZoomValue() + p1[0])
        ypos = int(co[1] * self.getZoomValue() + p1[1])
        return (xpos,ypos)

    
    def slideToScreen(self,pos):
        """
            convert slide coordinates to screen coordinates
        """
        xpos,ypos = pos
        p1 = self.region[0]
        cx = int((xpos - p1[0]) / self.getZoomValue())
        cy = int((ypos - p1[1]) / self.getZoomValue())
        return (cx,cy)        

    def showAnnotationsInOverview(self):
        """
            Show annotations in overview image.
        """
        if not (self.imageOpened):
            return
        self.tn_annot = self.thumbnail.getCopy()
        if (self.db.isOpen()):
            tnsize = np.float32(self.thumbnail.shape[1::-1])*self.thumbnail.downsamplingFactor
            self.tn_annot = self.overlayAnnotations(self.tn_annot, region=[np.zeros(2),tnsize], zoomLevel=self.thumbnail.downsamplingFactor, thickness=1, adjustList = False)



    def addAnnotator(self):
        """
            Add new annotator (person) to database.
        """
        name, ok = QInputDialog.getText(self, "Please give a name for the new expert",
                                          "Full name:")
        if (ok):
            self.db.insertAnnotator(name)
            # show DB overview
            self.showDatabaseUIelements()

    def addCellClass(self):
        """
            Add new cell class to database.
        """
        name, ok = QInputDialog.getText(self, "Please give a name for the new category",
                                          "Name:")
        if (ok):
            self.db.insertClass(name)
            # show DB overview
            self.showDatabaseUIelements()

    def overlayAnnotations(self, image, region = None, zoomLevel = None, thickness=2, adjustList = True):
        """
            Create annotation overlay for current view. This function is called for both, the current screen
            and the overview image.
        """
        if (self.db.isOpen() == False):
            return image
        if (region is None):
            region = self.region
        if (zoomLevel is None):
            zoomLevel = self.getZoomValue()
        leftUpper = region[0]
        rightLower = region[0] + region[1]
        if (adjustList):
            self.annotationsSpots=list()
            self.annotationsFlags = list()
            self.annotationsArea=list()
            self.annotationsCircle=list()
        radius=int(25/zoomLevel)
        if (thickness==1): # thumbnail annotation
            radius = 1

        allAnnotations = self.db.findSpotAnnotations(leftUpper, rightLower, self.slideUID, self.blindedMode, self.annotator)      

        for annotation in allAnnotations:
            if (adjustList) and (annotation[5]==4): # flag annotation
                    xpos=int((annotation[0]-leftUpper[0])/zoomLevel)
                    ypos=int((annotation[1]-leftUpper[1])/zoomLevel)
                    image = cv2.circle(image, thickness=thickness, center=(xpos, ypos), radius=14, color=[0, 0, 0], lineType=cv2.LINE_AA)
                    image = cv2.circle(image, thickness=thickness, center=(xpos, ypos), radius=13, color=[255, 255, 255,255], lineType=cv2.LINE_AA)
                    image = cv2.line(img=image, pt1=(xpos-10,ypos-10), pt2=(xpos+10,ypos+10), color=[0, 0, 0], lineType=cv2.LINE_AA)
                    image = cv2.line(img=image, pt1=(xpos-10,ypos+10), pt2=(xpos+10,ypos-10), color=[0, 0, 0], lineType=cv2.LINE_AA)
                    
                    self.annotationsFlags.append([xpos,ypos,14,0,annotation[2], annotation[4] ])

            elif (self.itemsSelected[annotation[2]]):
                # Normal spot annotations (e.g. cells)
                xpos=int((annotation[0]-leftUpper[0])/zoomLevel)
                ypos=int((annotation[1]-leftUpper[1])/zoomLevel)
                if (thickness == 1 ):
                    image[ypos,xpos,:] = self.colors[annotation[2]][0:3]
                else:
                    image = cv2.circle(image, thickness=thickness, center=(xpos, ypos), radius=radius, color=self.colors[annotation[2]], lineType=cv2.LINE_AA)

                if (adjustList):
                    self.annotationsSpots.append([xpos,ypos,int(25/zoomLevel),0,annotation[2], annotation[4] ])

        # 2nd job: Find area annotations
        allAnnotations = self.db.findAreaAnnotations(leftUpper,rightLower,self.slideUID, self.blindedMode, self.annotator)
        for annotation in allAnnotations:
            if (self.itemsSelected[annotation[4]]):
                if (annotation[6]==5): # circular type
                    xpos1=((annotation[0]-leftUpper[0])/zoomLevel)
                    ypos1=((annotation[1]-leftUpper[1])/zoomLevel)
                    xpos2=((annotation[2]-leftUpper[0])/zoomLevel)
                    ypos2=((annotation[3]-leftUpper[1])/zoomLevel)
                    circCenter = (int(0.5*(xpos1+xpos2)), int(0.5*(ypos1+ypos2)))
                    radius = int((xpos2-xpos1)*0.5)
                    image = cv2.circle(image, thickness=thickness, center=circCenter, radius=radius,color=self.colors[annotation[4]], lineType=cv2.LINE_AA)
                else:
                    xpos1=max(0,int((annotation[0]-leftUpper[0])/zoomLevel))
                    ypos1=max(0,int((annotation[1]-leftUpper[1])/zoomLevel))
                    xpos2=min(image.shape[1],int((annotation[2]-leftUpper[0])/zoomLevel))
                    ypos2=min(image.shape[0],int((annotation[3]-leftUpper[1])/zoomLevel))
                    image = cv2.rectangle(image, thickness=thickness, pt1=(xpos1,ypos1), pt2=(xpos2,ypos2),color=self.colors[annotation[4]], lineType=cv2.LINE_AA)
                if (adjustList):
                    self.annotationsArea.append([xpos1,ypos1,xpos2,ypos2,annotation[4], annotation[5], annotation[6] ])


        # finally: find polygons
        annotationPolygons = self.db.findPolygonAnnotatinos(leftUpper,rightLower,self.slideUID, self.blindedMode, self.annotator)
        for poly in annotationPolygons:
            image = self.showPolygon(tempimage=image, polygon=poly[0], color=self.colors[poly[1]])

        if (adjustList):
            self.annotationPolygons = annotationPolygons


        return image

    def changeScrollbars(self):
        """
            Callback function when the scrollbars (horizontal/vertical) are changed.
        """
        if (self.imageOpened):
            self.relativeCoords[0] = (self.ui.horizontalScrollBar.value()/self.ui.hsteps)-0.5
            self.relativeCoords[1] = (self.ui.verticalScrollBar.value()/self.ui.vsteps)-0.5
            self.showImage()


    def updateScrollbars(self):
        """
            Update the scrollbars when the position was changed by another method.
        """
        if not (self.imageOpened):
            return

        try:
            self.ui.horizontalScrollBar.valueChanged.disconnect()
            self.ui.verticalScrollBar.valueChanged.disconnect()
        except Exception: pass
        viewsize = self.mainImageSize * self.getZoomValue()

        self.ui.horizontalScrollBar.setMaximum(0)
        self.ui.hsteps=int(10*self.slide.level_dimensions[0][0]/viewsize[0])
        self.ui.vsteps=int(10*self.slide.level_dimensions[0][1]/viewsize[1])
        self.ui.horizontalScrollBar.setMaximum(self.ui.hsteps)
        self.ui.horizontalScrollBar.setMinimum(0)

        self.ui.verticalScrollBar.setMaximum(self.ui.vsteps)
        self.ui.verticalScrollBar.setMinimum(0)

        self.ui.horizontalScrollBar.setValue(int((self.relativeCoords[0]+0.5)*self.ui.hsteps))
        self.ui.verticalScrollBar.setValue(int((self.relativeCoords[1]+0.5)*self.ui.vsteps))

        self.ui.horizontalScrollBar.valueChanged.connect(self.changeScrollbars)
        self.ui.verticalScrollBar.valueChanged.connect(self.changeScrollbars)

    def findSlideUID(self):
        """
            Find slide in the database. If not found, ask if it should be added
        """
        if (self.db.isOpen()) and (self.imageOpened):
            slideUID = self.db.findSlideWithFilename(self.slidename)

            if (slideUID is None):
                msg = "Slide is not in database. Do you wish to add it?"
                reply = QtWidgets.QMessageBox.question(self, 'Message',
                                                       msg, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

                if reply == QtWidgets.QMessageBox.Yes:
                    self.db.insertNewSlide(self.slidename)
                    self.findSlideUID()
                    return
                else:
                    self.openSlideDialog()
            else:
                self.slideUID = slideUID

            self.showDBstatistics()
        else:
            self.slideUID = None

    def resizeEvent(self, event):
        """
            Resize event, used as callback function when the application is resized.
        """
        if (self.imageOpened):
            self.mainImageSize = np.asarray([self.ui.MainImage.frameGeometry().width(),self.ui.MainImage.frameGeometry().height()])

            self.showImage()
            self.updateScrollbars()
        if (event is not None):
            event.accept()

    def sliderToZoomValue(self):
        """
            Convert slider position to zoom value
        """
        return np.power(2,self.ui.horizontalSlider.value()/100*(np.log2(0.5/ self.getMaxZoom())))*self.getMaxZoom()

    def getMaxZoom(self):
        """
            Returns the maximum zoom available for this image.
        """
        return self.slide.level_dimensions[0][0] / self.mainImageSize[0]

    def setZoomValue(self, zoomValue):
        """
            Sets the zoom of the current image.
        """
        self.currentZoom = zoomValue
        if (self.currentZoom < 0.5):
            self.currentZoom = 0.5
        maxzoom = self.getMaxZoom()
        if (self.currentZoom > maxzoom):
            self.currentZoom = maxzoom
        
        sliderVal = 100*np.log2(self.currentZoom/(maxzoom))/(np.log2(0.5/maxzoom))

        self.ui.horizontalSlider.valueChanged.disconnect()

        self.ui.horizontalSlider.setValue(sliderVal)
        self.ui.horizontalSlider.valueChanged.connect(self.sliderChanged)

    def getZoomValue(self):
        """
            returns the current zoom value
        """
        return self.currentZoom



    def showImage(self):
        """
            showImage is an important function that is used for refreshing the image display.

            It's also being called a lot, basically after every change in the UI.
        """

        if (not self.imageOpened):
            return

        slidecenter = np.asarray(self.slide.level_dimensions[0])/2

        if (self.ui.iconAnnoTN.isChecked()):
            npi = np.copy(self.tn_annot)
        else:
            npi = self.thumbnail.getCopy()


        # find the top left conter (p1) and the width of the current screen
        imgarea_p1 = slidecenter - self.mainImageSize * self.getZoomValue() / 2 + self.relativeCoords*slidecenter*2
        imgarea_w =  self.mainImageSize * self.getZoomValue()

        # Annotate current screen being presented on overview map
        npi = self.thumbnail.annotateCurrentRegion(npi, imgarea_p1, imgarea_w)

        # annotate on screening map
        self.screeningMap.annotate(imgarea_p1, imgarea_w)

        if (self.overviewOverlayHeatmap):
            npi = self.screeningMap.overlayHeatmap(npi)

        # Set pixmap of overview image (display overview image)
        self.ui.OverviewLabel.setPixmap(self.vidImageToQImage(npi))

        # Now for the main image

        # Find the closest available downsampling factor
        closest_ds = self.slide.level_downsamples[np.argmin(np.abs(np.asarray(self.slide.level_downsamples)-self.getZoomValue()))]

        act_level = np.argmin(np.abs(np.asarray(self.slide.level_downsamples)-self.getZoomValue()))

        self.region = [imgarea_p1, imgarea_w]

        # Calculate size of the image
        size_im = (int(imgarea_w[0]/closest_ds), int(imgarea_w[1]/closest_ds))
        location_im = (int(imgarea_p1[0]), int(imgarea_p1[1]))

        # Read from Whole Slide Image
        tn = self.slide.read_region(location=location_im,level=act_level,size=size_im)

        aspectRatio_image = float(self.slide.level_dimensions[-1][0]) / self.slide.level_dimensions[-1][1]


        # Calculate real image size on screen
        if (self.ui.MainImage.frameGeometry().width()/aspectRatio_image<self.ui.MainImage.frameGeometry().height()):
            im_size=(self.ui.MainImage.frameGeometry().width(),int(self.ui.MainImage.frameGeometry().width()/aspectRatio_image))
        else:
            im_size=(int(self.ui.MainImage.frameGeometry().height()*aspectRatio_image),self.ui.MainImage.frameGeometry().height())

        # Convert to numpy array
        npi = np.array(tn, dtype=np.uint8)

        # Resize to real image size
        npi=cv2.resize(npi, dsize=(self.mainImageSize[0],self.mainImageSize[1]))

        # Overlay Annotations by the user
        if (self.db.isOpen()):
            npi = self.overlayAnnotations(npi)
        
        # Show the current polygon (if in polygon annotation mode)
        if (self.db.isOpen()) & (self.ui.mode==UIMainMode.MODE_ANNOTATE_POLYGON) & (self.ui.annotationMode>0):
            npi = self.showPolygon(npi, self.ui.annotationsList, color=[0,0,0,255])

        # Copy displayed image
        self.displayedImage = npi

        # Display image in GUI
        self.ui.MainImage.setPixmap(QPixmap.fromImage(self.toQImage(self.displayedImage)))

       
    def selectClasses(self,event):
        """
            Helper function to select classes for enabling/disabling display of annotations

        """

        items=np.zeros(len(self.modelItems))
        for item in range(len(self.modelItems)):
            if (self.modelItems[item].checkState()):
                items[item] = 1

        self.itemsSelected=items
        self.showAnnotationsInOverview()
        self.showImage()



    def openDatabase(self, flag=False, filename = None):
        """

            openDatabase - opens the database for SlideRunner.

            The function checks, if the database exists. 

        """

        import os
        SLIDE_DIRNAME = os.path.expanduser("~") + os.sep    

        if (filename is None):
            filename = SLIDE_DIRNAME+'Slides.sqlite'

        success = self.db.open(filename)
        
        if not success:
            reply = QtWidgets.QMessageBox.information(self, 'Message',
                    'Warning: Database %s not found. Do you want to create a new database?' % filename, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

            if (reply == QtWidgets.QMessageBox.Yes):
                success = self.db.create(filename)

        if success:            
            self.showDatabaseUIelements()
            self.showAnnotationsInOverview()
            self.writeDebug('Opened database')

            self.ui.iconBlinded.setEnabled(True)
            self.ui.iconQuestion.setEnabled(True)

            classes =   self.db.getAllClasses()
            for cls in classes:
                self.writeDebug('Found class %s (%d)' % ( cls[0],cls[1]))


    """
        Helper function to open custom database.
    """

    def openCustomDB(self):
        filename = QFileDialog.getOpenFileName(filter='SQLite databases (*.db, *.sqlite)')[0]
        if filename is not None and len(filename)>0:
            self.openDatabase(True,filename=filename)



    def showDBentryCount(self):
        """
            Show the overall annotation count.
        """
        num = self.db.countEntries()
        dbinfo = '<html>'+self.db.getDBname()+'(%d entries)' % (num) +'<br><html>'
        self.ui.label_4.setText(dbinfo)

        self.showDBstatistics()


    def showDBstatistics(self):
        """
            Show class-based statistics of current database
        """
        if (self.db.isOpen() == False):
            return
        self.ui.statisticView.setHidden(False)
        table_model = QtGui.QStandardItemModel()
        table_model.setColumnCount(3)
        table_model.setHorizontalHeaderLabels("Name;# on slide;# total".split(";"))

        names, statistics = self.db.countEntryPerClass(self.slideUID)

        for idx in range(len(names)):
            txt = QStandardItem(names[idx])
            col1 = QStandardItem('%d' % statistics[0,idx])
            col2 = QStandardItem('%d' % statistics[1,idx])
            table_model.appendRow([txt,col1,col2])

        self.ui.statisticView.setModel(table_model)
        self.ui.statisticView.resizeRowsToContents()
        self.ui.statisticView.resizeColumnsToContents()
    

    def showAnnoclass(self):
        """
            Visualize on GUI which annotation class is active
        """
        for k in range(len(self.classButtons)):
            btn = self.classButtons[k]
            if (k+1==self.lastAnnotationClass):
                btn.setText('active')
                style = 'background:#%x%x%x' % (int(self.colors[k+1][0]/16),
                                                int(self.colors[k+1][1]/16),
                                                int(self.colors[k+1][2]/16))
                btn.setStyleSheet(style)
            else:
                btn.setText('')
                btn.setStyleSheet('')


    def clickAnnoclass(self, classid):
        """
            User clicked on an annotation class
        """
        if (classid <= (len(self.classButtons))):
            self.lastAnnotationClass=classid
            self.showAnnoclass()


    def showDatabaseUIelements(self):
        """
            Show and update UI controls related to the database
        """
        self.ui.actionAdd_annotator.setEnabled(True)
        self.ui.actionAdd_cell_class.setEnabled(True)

        self.showDBentryCount()

        persons = self.db.getAllPersons()
        personList=[]
        for person in persons:
            personList.append(person[0])

        self.annotatorsModel.setStringList(personList)
        self.ui.comboBox.setVisible(True)
        self.ui.comboBox.setEnabled(True)
        model = QStandardItemModel()
        
        self.ui.comboBox.currentIndexChanged.connect(self.changeAnnotator)

        model = QStandardItemModel()

        self.modelItems = list()
        classes =   self.db.getAllClasses()
        self.classButtons = list()
        self.ui.categoryView.setRowCount(len(classes)+1)
        self.ui.categoryView.setColumnCount(4)
        item = QTableWidgetItem('unknown')
        pixmap = QPixmap(10,10)
        pixmap.fill(QColor.fromRgb(self.colors[0][0],self.colors[0][1],self.colors[0][2]))
        itemcol = QTableWidgetItem('')
        itemcol.setBackground(QColor.fromRgb(self.colors[0][0],self.colors[0][1],self.colors[0][2]))
        checkbx = QCheckBox()
        checkbx.setChecked(False)
        checkbx.stateChanged.connect(self.selectClasses)
        self.ui.categoryView.setItem(0,2, item)
        self.ui.categoryView.setItem(0,1, itemcol)
        self.ui.categoryView.setCellWidget(0,0, checkbx)
        self.modelItems.append(checkbx)

        # For all classes in the database, make an entry in the table with
        # a class button and respective correct color
        
        for clsid in range(len(classes)):
            clsname = classes[clsid]
            item = QTableWidgetItem(clsname[0])
            pixmap = QPixmap(10,10)
            pixmap.fill(QColor.fromRgb(self.colors[clsid+1][0],self.colors[clsid+1][1],self.colors[clsid+1][2]))
            btn = QPushButton('')

            btn.clicked.connect(partial(self.clickAnnoclass, clsid+1))
            self.classButtons.append(btn)
            itemcol = QTableWidgetItem('')
            checkbx = QCheckBox()
            checkbx.setChecked(True)
            itemcol.setBackground(QColor.fromRgb(self.colors[clsid+1][0],self.colors[clsid+1][1],self.colors[clsid+1][2]))
            self.modelItems.append(checkbx)
            self.ui.categoryView.setItem(clsid+1,2, item)
            self.ui.categoryView.setItem(clsid+1,1, itemcol)
            self.ui.categoryView.setCellWidget(clsid+1,0, checkbx)
            self.ui.categoryView.setCellWidget(clsid+1,3, btn)
            checkbx.stateChanged.connect(self.selectClasses)

        model.itemChanged.connect(self.selectClasses)

        self.itemsSelected = np.ones(len(classes)+1)
        self.itemsSelected[0] = 0
        self.ui.categoryView.verticalHeader().setVisible(False)
        vheader = self.ui.categoryView.verticalHeader()
        vheader.setDefaultSectionSize(vheader.fontMetrics().height()+2)
        self.ui.categoryView.horizontalHeader().setVisible(False)
        self.ui.categoryView.setColumnWidth(0, 20)
        self.ui.categoryView.setColumnWidth(1, 20)
        self.ui.categoryView.setColumnWidth(2, 120)
        self.ui.categoryView.setColumnWidth(3, 50)
        self.ui.categoryView.setShowGrid(False)

        self.findSlideUID()

        self.ui.comboBox.setModel(self.annotatorsModel)

        if (self.imageOpened):
            self.showImage()

    def sliderChanged(self):
        """
            Callback function for when a slider was changed.
        """
        self.setZoomValue(self.sliderToZoomValue())
        self.showImage()
        self.updateScrollbars()

    def createNewDatabase(self):
        """
            Callback function to create a new database structure.
        """

        dbfilename = QFileDialog.getSaveFileName(filter='*.sqlite')[0]
        if (len(dbfilename)==0):
            return
        if (os.path.isfile(dbfilename)):

            reply = QtWidgets.QMessageBox.question(self, 'Question',
                                           'This database already exists. Do you REALLY wish to overwrite it?', QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

            if reply == QtWidgets.QMessageBox.No:
                return

        self.writeDebug('Creating new DB as %s' % dbfilename)

        # create and automatically open DB
        self.db.create(dbfilename)
        self.showDatabaseUIelements()


    def openSlideDialog(self):
        """
            Callback function to select a slide
        """
        filename = QFileDialog.getOpenFileName(filter='OpenSlide files (*.svs *.tif *.bif *.svslide *.mrxs *.scn *.vms *.vmu *.ndpi *.tiff);;Aperio SVS format (*.svs);;All files (*.*)')[0]
        if (len(filename)==0):
            return
        self.openSlide(filename)
    
    def initZoomSlider(self):
        """
            Initialize the scrollbar slider.
        """
        self.ui.horizontalSlider.setMaximum(100)
        self.ui.horizontalSlider.setMinimum(0)
        self.ui.horizontalSlider.valueChanged.connect(self.sliderChanged)


    def openSlide(self, filename):
        """
            Helper function to open a whole slide image
        """

        self.slide = openslide.open_slide(filename)
        self.slidename = os.path.basename(filename)

        # unhide label and show filename
        self.ui.filenameLabel.setText(self.slidename)
        self.ui.filenameLabel.setHidden(False)
        self.slidepathname = filename
        self.imageOpened=True
        self.ui.statusbar.showMessage(filename+': '+str(self.slide.dimensions))

        self.findSlideUID()
        self.relativeCoords = np.asarray([0,0], np.float32)
        self.lastScreeningLeftUpper = np.zeros(2)

        self.thumbnail = thumbnail.thumbnail(self.slide)

        # Read overview thumbnail from slide
        overview = self.slide.read_region(location=(0,0), level=self.slide.level_count-1, size=self.slide.level_dimensions[-1])
        overview = cv2.cvtColor(np.asarray(overview), cv2.COLOR_BGRA2RGB)

        # Initialize a new screening map
        self.screeningMap = screening.screeningMap(overview, self.mainImageSize, self.slide.level_dimensions, self.thumbnail.size)

        self.resizeEvent(None)
        self.initZoomSlider()
        self.imageCenter=[0,0]
        self.setZoomValue(self.getMaxZoom())

        self.showAnnotationsInOverview()
        self.showImage()

        self.updateScrollbars()

        self.showDBstatistics()


def main():
    style.setStyle(app)    

    myapp = SlideRunnerUI()
    myapp.show()
    myapp.raise_()
    splash.finish(myapp)

    sys.exit(app.exec_())

if __name__ == "__main__":

    main()
