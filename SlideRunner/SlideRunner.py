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


version = '1.20.0'

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
from SlideRunner.dataAccess.annotations import ViewingProfile
from PyQt5.QtCore import QSettings

# Thread for receiving images from the plugin
class imageReceiverThread(threading.Thread):

    def __init__(self, queue, selfObj):
        threading.Thread.__init__(self)
        self.queue = queue
        self.selfObj = selfObj
        print('Created 1 image receiver thread')

    def run(self):
        while True:
            (img, procId) = self.queue.get()
            print('Received an image from the plugin queue')
            self.selfObj.overlayMap = img
            self.selfObj.showImageRequest.emit(np.empty(0), procId)

class SlideReaderThread(threading.Thread):
    queue = queue.Queue()
    def __init__(self, SlideRunnerObject):
        threading.Thread.__init__(self)
        self.SlideRunnerObject = SlideRunnerObject
    
    def run(self):
        while (True):
            (location, level, size, id) = self.queue.get()
            img = self.SlideRunnerObject.read_region(location, level, size)
            if (self.queue.empty()): # new request pending
                if (img is not None):
                    self.SlideRunnerObject.readRegionCompleted.emit(img,id)



# Thread for receiving progress bar events
class PluginStatusReceiver(threading.Thread):

    def __init__(self, queue, selfObj):
        threading.Thread.__init__(self)
        self.queue = queue
        self.selfObj = selfObj

    def run(self):
        while True:
            # grabs host from queue
            msgId, value = self.queue.get()
            if (msgId == SlideRunnerPlugin.StatusInformation.PROGRESSBAR):
                self.selfObj.progressBarChanged.emit(value)
            elif (msgId == SlideRunnerPlugin.StatusInformation.TEXT):
                self.selfObj.statusViewChanged.emit(value)
            elif (msgId == SlideRunnerPlugin.StatusInformation.ANNOTATIONS):
                self.selfObj.annotationReceived.emit(value)
            elif (msgId == SlideRunnerPlugin.StatusInformation.SET_ZOOM):
                self.selfObj.setZoomReceived.emit(value)
            elif (msgId == SlideRunnerPlugin.StatusInformation.SET_CENTER):
                self.selfObj.setCenterReceived.emit(value)
            elif (msgId == SlideRunnerPlugin.StatusInformation.POPUP_MESSAGEBOX):
                self.selfObj.pluginPopupMessageReceived.emit(value)
            elif (msgId == SlideRunnerPlugin.StatusInformation.UPDATE_CONFIG):
                self.selfObj.updatePluginConfig.emit(value)

class SlideRunnerUI(QMainWindow):
    progressBarChanged = pyqtSignal(int)
    showImageRequest = pyqtSignal(np. ndarray, int)
    readRegionCompleted = pyqtSignal(np.ndarray, int)
    statusViewChanged = pyqtSignal(str)
    annotationReceived = pyqtSignal(list)
    updatedCacheAvailable = pyqtSignal(dict)
    setZoomReceived = pyqtSignal(float)
    setCenterReceived = pyqtSignal(tuple)
    updatePluginConfig = pyqtSignal(SlideRunnerPlugin.PluginConfigUpdate)
    pluginPopupMessageReceived = pyqtSignal(str)
    annotator = bool # ID of curent annotator
    db = Database()
    receiverThread = None
    activePlugin = None
    overlayMap = None
    processingStep = 0
    statusViewOffTimer = None
    slideMagnification = 1
    slideMicronsPerPixel = 20
    pluginAnnos = list()
    cachedLevel = None
    currentVP = ViewingProfile()
    lastReadRequest = None
    cachedLocation = None
    pluginTextLabels = dict()
    cachedImage = None
    pluginParameterSliders = dict()
    refreshTimer = None
    settings = QSettings('Pattern Recognition Lab, FAU Erlangen Nuernberg', 'SlideRunner')


    def __init__(self):
        super(SlideRunnerUI, self).__init__()

        # Default value initialization
        self.relativeCoords = np.asarray([0,0], np.float32)
        self.lastAnnotationClass=0
        self.imageOpened=False # flag, if 
        self.annotator=0 # ID of current annotator
        self.eventIntegration=0
        # Set up the user interface from Designer.
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # Add sidebar
        self.ui = addSidebar(self.ui)
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
        self.overlayExtremes = None
        self.overviewOverlayHeatmap = False
        self.annotationPolygons=[]
        self.ui.MainImage.installEventFilter(self)
        self.ui.horizontalScrollBar.valueChanged.connect(self.changeScrollbars)
        self.ui.verticalScrollBar.valueChanged.connect(self.changeScrollbars)
        self.ui.opacitySlider.setValue(50)
        self.ui.opacitySlider.valueChanged.connect(self.changeOpacity)
        self.ui.progressBar.setHidden(True)
        self.cachedLastImage = None

        self.removeLastPolygonPoint = mouseEvents.removeLastPolygonPoint #redirect
        self.disableStatusView()

        self.ui.progressBar.setValue(0)
        self.progressBarQueue = queue.Queue()
        self.progressBarChanged.connect(self.setProgressBar)
        self.statusViewChanged.connect(self.setStatusView)
        self.showImageRequest.connect(self.showImage_part2)
        self.annotationReceived.connect(self.receiveAnno)
        self.updatePluginConfig.connect(self.updatePluginConfiguration)
        self.updatedCacheAvailable.connect(self.updateCache)
        self.setZoomReceived.connect(self.setZoom)
        self.setCenterReceived.connect(self.setCenter)
        self.readRegionCompleted.connect(self.showImage_part2)
        self.pluginPopupMessageReceived.connect(self.popupmessage)

        self.pluginStatusReceiver = PluginStatusReceiver(self.progressBarQueue, self)
        self.pluginStatusReceiver.setDaemon(True)
        self.pluginStatusReceiver.start()

        self.slideReaderThread = SlideReaderThread(self)
        self.slideReaderThread.setDaemon(True)
        self.slideReaderThread.start()


        self.wheelEvent = partial(mouseEvents.wheelEvent,self)

        self.ui.MainImage.setPixmap(self.vidImageToQImage(127*np.ones((600,600,3),np.uint8)))
        self.ui.MainImage.mousePressEvent = partial(mouseEvents.pressImage, self)
        self.ui.MainImage.mouseReleaseEvent = partial(mouseEvents.releaseImage, self)
        self.ui.MainImage.mouseMoveEvent = partial(mouseEvents.moveImage,self)
        self.ui.MainImage.mouseDoubleClickEvent = partial(mouseEvents.doubleClick,self)
        self.ui.OverviewLabel.setPixmap(self.vidImageToQImage(127*np.ones((200,200,3),np.uint8)))
        self.opacity = 1.0
        self.mainImageSize = np.asarray([self.ui.MainImage.frameGeometry().width(),self.ui.MainImage.frameGeometry().height()])
        self.ui.OverviewLabel.mousePressEvent = self.pressOverviewImage

        self.ui.opacitySlider.setHidden(True)
        self.ui.opacityLabel.setHidden(True)

        menu.defineMenu(self.ui, self)
        menu.defineAnnotationMenu(self)

        shortcuts.defineMenuShortcuts(self)

        self.checkSettings()
        self.currentVP.spotCircleRadius = self.settings.value('SpotCircleRadius')


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


        if (len(sys.argv)>1):
            if os.path.isfile(sys.argv[1]):
                self.openSlide(sys.argv[1])

        if (len(sys.argv)>2):
            if os.path.isfile(sys.argv[2]):
                self.openDatabase(True, filename=sys.argv[2])

    def get_color(self, idx):
        colors = [[0,0,0,0],[0,0,255,255],[0,255,0,255],[255,255,0,255],[255,0,255,255],[0,127,0,255],[255,127,0,255],[127,127,0,255],[255,255,255,255],[10, 166, 168,255],[166, 10, 168,255],[166,168,10,255]]

        return colors[idx % len(colors)]


    def checkSettings(self):
        if (self.settings.value('OverlayColorMap') == None):
            self.settings.setValue('OverlayColorMap', 'Greens')
        if (self.settings.value('SpotCircleRadius') == None):
            self.settings.setValue('SpotCircleRadius', 25)


    class NotImplementedException:
        pass


    """
    Handle status bar
    """

    def setStatusView(self, strValue):
        self.ui.statusbar.showMessage(strValue)
        
    def disableStatusView(self):
        self.ui.statusLabel.setVisible(False)
        
    """
    Signal that we accept drag&drop for files, and show the link icon.
    """

    def popupmessage(self, msg):
        reply = QtWidgets.QMessageBox.about(self, "Plugin says", msg)
    
    def updatePluginConfiguration(self, newConfig:SlideRunnerPlugin.PluginConfigUpdate):
        for entry in newConfig.updateList:
            if (entry.getType()==SlideRunnerPlugin.PluginConfigurationType.SLIDER_WITH_FLOAT_VALUE):
                self.pluginParameterSliders[entry.uid].setValue(1000*entry.value)
        self.triggerPluginConfigChanged()

    def receiveAnno(self, anno):
        self.pluginAnnos = anno
        self.showImage_part2(np.empty(shape=(1)), self.processingStep)

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
        This is triggered, whenever a plugin configuration option has been changed
    """

    def triggerPluginConfigChanged(self):
        self.overlayMap = None
        self.pluginAnnos = list()
        self.showImage()
        for key in self.pluginConfigLabels.keys():
            self.pluginConfigLabels[key].setText('%.3f' % (self.pluginParameterSliders[key].value() / 1000.0 ))

    def pluginFilePickerButtonHit(self, config: SlideRunnerPlugin.FilePickerConfigurationEntry, labelObj:QtWidgets.QLabel):
        self.overlayMap = None
        self.pluginAnnos = list()
        if (config.dialogType == SlideRunnerPlugin.FilePickerDialogType.OPEN_FILE):
            ret,err = QFileDialog.getOpenFileName(self,config.title, "",config.mask)

        elif (config.dialogType == SlideRunnerPlugin.FilePickerDialogType.SAVE_FILE):
            ret,err = QFileDialog.getSaveFileName(self,config.title, "",config.mask)
        
        elif (config.dialogType == SlideRunnerPlugin.FilePickerDialogType.OPEN_DIRECTORY):
            ret,err = QFileDialog.getExistingDirectory(self,config.title, "",config.mask)
        
        labelObj.setText(ret)
        if (ret is not None) and (self.imageOpened):
            self.triggerPlugin(self.cachedLastImage, trigger=config)

    def pluginControlButtonHit(self, btn):
        self.overlayMap = None
        self.pluginAnnos = list()
        self.triggerPlugin(self.cachedLastImage, trigger=btn)
#        self.showImage()

    """
     Add configuration options of active plugin to sidebar
    """
    def addActivePluginToSidebar(self, plugin:SlideRunnerPlugin):
        if len(plugin.configurationList)>0:
            self.pluginParameterSliders=dict()
            self.pluginConfigLabels=dict()
            self.pluginTextLabels = dict()
            self.pluginPushbuttons = dict()
            self.pluginFilepickers = dict()
            sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
            sizePolicy.setHorizontalStretch(1.0)
            sizePolicy.setVerticalStretch(0)
            for pluginConfig in plugin.configurationList:
                if (pluginConfig.type == SlideRunnerPlugin.PluginConfigurationType.PUSHBUTTON):
                    newButton = QtWidgets.QPushButton(self.ui.tab3widget)
                    newButton.setText(pluginConfig.name)
                    newButton.setSizePolicy(sizePolicy)
                    newButton.setStyleSheet('font-size:8px')
                    newButton.clicked.connect(partial(self.pluginControlButtonHit, pluginConfig))
                    self.ui.tab3Layout.addWidget(newButton)
                    self.pluginPushbuttons[pluginConfig.uid] = newButton
                elif (pluginConfig.type == SlideRunnerPlugin.PluginConfigurationType.FILEPICKER):
                    hLayout = QtWidgets.QHBoxLayout(self.ui.tab3widget)
                    newButton = QtWidgets.QPushButton(self.ui.tab3widget)
                    newButton.setText(pluginConfig.name)
                    newButton.setSizePolicy(sizePolicy)
                    newButton.setStyleSheet('font-size:8px')
                    self.ui.tab3Layout.addWidget(newButton)
                    newLabel = QtWidgets.QLabel(self.ui.tab3widget)
                    newLabel.setText('None')
                    newLabel.setSizePolicy(sizePolicy)
                    newLabel.setStyleSheet('font-size:8px')
                    hLayout.addWidget(newButton)
                    hLayout.addWidget(newLabel)
                    newButton.clicked.connect(partial(self.pluginFilePickerButtonHit, pluginConfig, newLabel))
                    self.ui.tab3Layout.addLayout(hLayout)
                    self.pluginFilepickers[pluginConfig.uid] = {'button' : newButton, 'label' : newLabel}
                    print('Added new filepicker')
                    
                elif (pluginConfig.type == SlideRunnerPlugin.PluginConfigurationType.SLIDER_WITH_FLOAT_VALUE):
                    newLabel = QtWidgets.QLabel(self.ui.tab3widget)
                    newLabel.setText(pluginConfig.name)
                    newLabel.setSizePolicy(sizePolicy)
                    newLabel.setStyleSheet('font-size:8px')
                    self.ui.tab3Layout.addWidget(newLabel)
                    self.pluginTextLabels[pluginConfig.uid] = newLabel
                    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Minimum)
                    sizePolicy.setHorizontalStretch(1.0)
                    sizePolicy.setVerticalStretch(0)
                    newSlider = QtWidgets.QSlider(self.ui.tab3widget)
                    newSlider.setMinimum(pluginConfig.minValue*1000)
                    newSlider.setMaximum(pluginConfig.maxValue*1000)
                    newSlider.setValue(pluginConfig.initValue*1000)
                    newSlider.setOrientation(QtCore.Qt.Horizontal)
                    newSlider.setSizePolicy(sizePolicy)
                    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
                    sizePolicy.setHorizontalStretch(1.0)
                    sizePolicy.setVerticalStretch(0)
                    newSlider.valueChanged.connect(self.triggerPluginConfigChanged)
                    hLayout = QtWidgets.QHBoxLayout(self.ui.tab3widget)
                    hLayout.addWidget(newSlider)
                    valLabel = QtWidgets.QLabel(self.ui.tab3widget)
                    valLabel.setText('%.3f' % pluginConfig.initValue)
                    valLabel.setStyleSheet('font-size:8px')
                    sizePolicy.setHorizontalStretch(0.0)
                    valLabel.setSizePolicy(sizePolicy)
                    hLayout.addWidget(valLabel)
                    self.ui.tab3Layout.addLayout(hLayout)
                    self.pluginParameterSliders[pluginConfig.uid] = newSlider
                    self.pluginConfigLabels[pluginConfig.uid] = valLabel
                    newSlider.setStyleSheet("""
    QSlider:horizontal {
        min-height: 10px;
    }
    
    QSlider::groove:horizontal {
        margin: 0px 0; /* decrease this size (make it more negative)—I changed mine from –2px to –8px. */
    }
    """)


                
                

    """
    Helper function to toggle Plugin activity
    """
    def togglePlugin(self, plugin:pluginEntry):
        active = False
        for pluginItem in self.ui.pluginItems:
            if (plugin.commonName == pluginItem.text()):
                active = pluginItem.isChecked()
            else:
                pluginItem.setChecked(False)

        if (len(self.pluginParameterSliders) > 0):
            for slider in self.pluginParameterSliders.keys():
                self.ui.tab3Layout.removeWidget(self.pluginParameterSliders[slider])
                self.pluginParameterSliders[slider].deleteLater()
            for label in self.pluginConfigLabels.keys():
                self.ui.tab3Layout.removeWidget(self.pluginConfigLabels[label])
                self.pluginConfigLabels[label].deleteLater()
            for label in self.pluginTextLabels.keys():
                self.ui.tab3Layout.removeWidget(self.pluginTextLabels[label])
                self.pluginTextLabels[label].deleteLater()
            for btn in self.pluginPushbuttons.keys():
                self.ui.tab3Layout.removeWidget(self.pluginPushbuttons[btn])
                self.pluginPushbuttons[btn].deleteLater()
            for uid in self.pluginFilepickers.keys():
                self.ui.tab3Layout.removeWidget(self.pluginFilepickers[uid]['button'])
                self.ui.tab3Layout.removeWidget(self.pluginFilepickers[uid]['label'])
                self.pluginFilepickers[uid]['label'].deleteLater()
                self.pluginFilepickers[uid]['button'].deleteLater()



            self.pluginParameterSliders = dict()
            self.pluginConfigLabels = dict()
            self.pluginTextLabels = dict()
            self.pluginPushbuttons = dict()
            self.pluginFilepickers = dict()

        if (plugin.receiverThread is None):
            plugin.receiverThread = imageReceiverThread(plugin.outQueue, self)
            plugin.receiverThread.setDaemon(True)
            plugin.receiverThread.start()

        if (active):
            if (self.activePlugin is not plugin):
                    self.overlayMap=None
                    self.overlayExtremes=None

            self.activePlugin = plugin
            self.addActivePluginToSidebar(plugin.plugin)
            if (plugin.plugin.outputType != SlideRunnerPlugin.PluginOutputType.NO_OVERLAY):
                self.ui.opacitySlider.setValue(int(plugin.plugin.initialOpacity*100))
                self.ui.opacitySlider.setHidden(False)
                self.ui.opacitySlider.setEnabled(True)
                self.ui.opacityLabel.setHidden(False)
            else:
                self.ui.opacityLabel.setHidden(True)
                self.ui.opacitySlider.setHidden(True)
        else:
            self.activePlugin = None
            self.ui.opacityLabel.setHidden(True)
            self.ui.opacitySlider.setHidden(True)



        print('Active plugin is now ', self.activePlugin)
        self.overlayMap = None
        self.pluginAnnos = list()
        self.showImage()

    """
        Aggregate plugin configuration alltogether
    """

    def gatherPluginConfig(self):
        config = dict()
        for key in self.pluginParameterSliders.keys():
            config[key] = self.pluginParameterSliders[key].value()/1000.0
        for key in self.pluginFilepickers.keys():
            config[key] = self.pluginFilepickers[key]['label'].text()
        return config


    """
        Send annotation to plugin
    """

    def sendAnnoToPlugin(self, anno, actionUID = None ):
        self.triggerPlugin(self.rawImage, (anno,), actionUID=actionUID)
#        self.triggerPlugin(self.rawImage, (self.db.annoDetails(anno),))

    """
    Helper function to trigger the plugin
    """
    def triggerPlugin(self,currentImage, annotations=None, trigger=None, actionUID=None):

        print('Plugin triggered...')
        image_dims=self.slide.level_dimensions[0]
        actual_downsample = self.getZoomValue()
        visualarea = self.mainImageSize
        slidecenter = np.asarray(self.slide.level_dimensions[0])/2

        imgarea_p1 = slidecenter - visualarea * actual_downsample / 2 + self.relativeCoords*slidecenter*2
        imgarea_w =  visualarea * actual_downsample

        coordinates = (int(imgarea_p1[0]), int(imgarea_p1[1]), int(imgarea_w[0]), int(imgarea_w[1]))

        self.activePlugin.inQueue.put(SlideRunnerPlugin.jobToQueueTuple(currentImage=currentImage, slideFilename=self.slidepathname, configuration=self.gatherPluginConfig(), annotations=annotations, trigger=trigger,coordinates=coordinates, actionUID=actionUID, openedDatabase=self.db))


    """
    Helper function to reset screening completely
    """

    def resetGuidedScreening(self):
            self.lastScreeningLeftUpper = np.zeros(2)
            self.screeningMap.reset()
            self.lastScreeningCenters = list()
            self.screeningIndex = 0
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


    def previousScreeningStep(self):
        if not (self.imageOpened):
            return

        if not (self.screeningMode):
            return

        self.screeningIndex -= 1

        self.setCenterTo(self.screeningHistory[self.screeningIndex-1][0],self.screeningHistory[self.screeningIndex-1][1])

        if (self.screeningIndex+len(self.screeningHistory)<=0):
            self.ui.iconPreviousScreen.setEnabled(False)

        self.showImage()
        return

    def nextScreeningStep(self):
        if not (self.imageOpened):
            return

        if not (self.screeningMode):
            return

        self.ui.iconPreviousScreen.setEnabled(True)
        self.writeDebug('Next screen in screening mode')

        if (self.screeningIndex<0):
            self.screeningIndex+= 1
    #        self.setCenterTo(self.screeningHistory[self.screeningIndex])
            self.setCenterTo(self.screeningHistory[self.screeningIndex-1][0],self.screeningHistory[self.screeningIndex-1][1])
            self.showImage()
            return


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

        self.screeningMap.screeningHistory = self.relativeCoords

        self.setCenterTo( (leftupper_x+relOffset_x/2)*self.slide.level_dimensions[0][0], (leftupper_y+relOffset_y/2)*self.slide.level_dimensions[0][1])
        self.screeningHistory.append( ( (leftupper_x+relOffset_x/2)*self.slide.level_dimensions[0][0], (leftupper_y+relOffset_y/2)*self.slide.level_dimensions[0][1] ) )
        self.showImage()

    def setCenter(self, target):
        self.setCenterTo(target[0], target[1])
        self.showImage()

    def setZoom(self, target):
        self.setZoomValue(target)
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
            self.nextScreeningStep()
#            self.showImage()
    
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

    def zoomMaxoptical(self):
        self.setZoomValue(1.0)
        self.showImage()

    def setOverlayHeatmap(self):
        self.overviewOverlayHeatmap = self.ui.iconOverlay.isChecked()
        self.showImage()


    """
        Discover annotations unclassified by current viewer. The outer 
        50 pixels of the screen are discarded, since annotations might be
        only partially shown.
    """
    def discoverUnclassified(self, force=False):

        if not (self.db.isOpen()): 
            return

        leftUpper = self.region[0] 
        leftUpper[0] += 50
        leftUpper[1] += 50
        rightLower = self.region[0] + self.region[1] - (50,50)
        rightLower[0] -= 50
        rightLower[1] -= 50
        
        unknownInScreen = self.db.getUnknownInCurrentScreen(leftUpper, rightLower, self.annotator)
        if not (unknownInScreen) or force:
            unknownAnno = self.db.pickRandomUnlabeled(self.annotator)
            if (unknownAnno is not None):
                annoCenter = unknownAnno.getCenter()
                annoDims = unknownAnno.getDimensions()
                self.setCenterTo(annoCenter.x,annoCenter.y)
                self.setZoomTo(annoDims[0],annoDims[1])
            else:
                reply = QtWidgets.QMessageBox.information(self, 'Message',
                                        'All objects have been rated by you. Thanks :)', QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)


        self.showImage()

    def setDiscoveryMode(self):
        self.discoveryMode= self.ui.iconQuestion.isChecked()
        if (self.discoveryMode):
            self.discoverUnclassified(force=True)

    def setBlindedMode(self):
        self.modelItems[0].setChecked(True) # enable unknown class
        self.blindedMode = self.ui.iconBlinded.isChecked()
        self.currentVP.blindMode = self.blindedMode
        self.currentVP.annotator = self.annotator
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
        if (self.ui.mode == UIMainMode.MODE_ANNOTATE_POLYGON) and not (mode == UIMainMode.MODE_ANNOTATE_POLYGON ) and (self.ui.annotationMode>0):
            reply = QtWidgets.QMessageBox.question(self, 'Question',
                                          'Do you want to stop your polygon annotation? Hint: If you want to move the image during annotation, hold shift while dragging the image.', QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

            if reply == QtWidgets.QMessageBox.No:
                return
            
            self.ui.mode = mode
            self.ui.annotationsList = list()
            self.showImage()



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
            self.overlayMap=None
            if (self.activePlugin is not None) and (self.activePlugin.plugin.getAnnotationUpdatePolicy() == SlideRunnerPlugin.AnnotationUpdatePolicy.UPDATE_ON_SCROLL_CHANGE):
                self.pluginAnnos = list()
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

            

 
    def writeDebug(self, message):
        if SLIDERUNNER_DEBUG:
            self.logger.debug(message)


    def showPolygon(self, tempimage, polygon, color):
        zoomLevel = self.getZoomValue()
        markersize = int(5/zoomLevel)
        listIdx=-1

        # small assertion to fix bug #12
        if (len(polygon)==0):
            return tempimage

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

    def showDBEntry(self, entry:annotation):
        table_model = QtGui.QStandardItemModel()
        table_model.setColumnCount(2)
        table_model.setHorizontalHeaderLabels("Name;Description".split(";"))

        lab1 = QStandardItem('Unique ID ')
        item = QStandardItem(str(entry.uid))
        table_model.appendRow([lab1,item])

        getdesc = entry.getDescription(self.db)
        for (label, item) in getdesc:
            lab1 = QStandardItem(label)
            itemi = QStandardItem(item)
            table_model.appendRow([lab1,itemi])

        self.ui.inspectorTableView.setModel(table_model)
        self.ui.inspectorTableView.resizeRowsToContents()



    def defineAnnotator(self, uid):
        self.annotator = uid
        self.currentVP.annotator = self.annotator
        allPers=self.db.getAllPersons()
        for persIdx in range(len(allPers)):
            person=allPers[persIdx]
            if (person[1] == uid):
                self.ui.annotatorComboBox.setCurrentIndex(persIdx)
        

    def changeAnnotator(self):
        allPers=self.db.getAllPersons()
        if len(allPers)==0:
            self.annotator = 0
        else:
            self.annotator = allPers[self.ui.annotatorComboBox.currentIndex()][1]
        self.currentVP.annotator = self.annotator
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
        self.writeDebug('changed label for object with class %d, slide %d, person %d, ID %d' % ( classId, self.slideUID,self.retrieveAnnotator(event), annoId))
        self.showImage()

    def addAnnotationLabel(self, classId, event, annoId ):
        self.writeDebug('new label for object with class %d, slide %d, person %d, ID %d' % ( classId, self.slideUID,self.retrieveAnnotator(event), annoId))
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
        if (region is None):
            region = self.region
        if (region is None):
            print('Region is none - whoopsy.')
            return image
        leftUpper = region[0]
        if (zoomLevel is None):
            zoomLevel = self.getZoomValue()

        if (self.activePlugin):
            for anno in self.pluginAnnos:
                anno.draw(image, leftUpper, zoomLevel, thickness, self.get_color(0))
        else:
            pass

        if (self.db.isOpen() == False):
            return image
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
                    image[ypos,xpos,:] = self.get_color(annotation[2])[0:3]
                else:
                    image = cv2.circle(image, thickness=thickness, center=(xpos, ypos), radius=radius, color=self.get_color(annotation[2]), lineType=cv2.LINE_AA)

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
                    if (radius<0):
                        print('Error with data set / Radius <0:', xpos1,ypos1,xpos2,ypos2,circCenter,radius)
                    else:
                        image = cv2.circle(image, thickness=thickness, center=circCenter, radius=radius,color=self.get_color(annotation[4]), lineType=cv2.LINE_AA)
                else:
                    xpos1=max(0,int((annotation[0]-leftUpper[0])/zoomLevel))
                    ypos1=max(0,int((annotation[1]-leftUpper[1])/zoomLevel))
                    xpos2=min(image.shape[1],int((annotation[2]-leftUpper[0])/zoomLevel))
                    ypos2=min(image.shape[0],int((annotation[3]-leftUpper[1])/zoomLevel))
                    image = cv2.rectangle(image, thickness=thickness, pt1=(xpos1,ypos1), pt2=(xpos2,ypos2),color=self.get_color(annotation[4]), lineType=cv2.LINE_AA)
                if (adjustList):
                    self.annotationsArea.append([xpos1,ypos1,xpos2,ypos2,annotation[4], annotation[5], annotation[6] ])


        # finally: find polygons
        annotationPolygons = self.db.findPolygonAnnotatinos(leftUpper,rightLower,self.slideUID, self.blindedMode, self.annotator)
        for poly in annotationPolygons:
            image = self.showPolygon(tempimage=image, polygon=poly[0], color=self.get_color(poly[1]))

        if (adjustList):
            self.annotationPolygons = annotationPolygons

        return image

    def changeScrollbars(self):
        """
            Callback function when the scrollbars (horizontal/vertical) are changed.
        """
        if (self.imageOpened):
            self.overlayMap=None
            if (self.activePlugin is not None) and (self.activePlugin.plugin.getAnnotationUpdatePolicy() == SlideRunnerPlugin.AnnotationUpdatePolicy.UPDATE_ON_SCROLL_CHANGE):
                self.pluginAnnos = list()
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

        self.overlayMap=None
        if (self.activePlugin is not None) and (self.activePlugin.plugin.getAnnotationUpdatePolicy() == SlideRunnerPlugin.AnnotationUpdatePolicy.UPDATE_ON_SCROLL_CHANGE):
            self.pluginAnnos = list()
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

    def findSlideUID(self, dimensions = None):
        """
            Find slide in the database. If not found, ask if it should be added
        """
        if (self.db.isOpen()) and (self.imageOpened):
            slideUID = self.db.findSlideWithFilename(self.slidename,self.slidepathname)

            if (slideUID is None):
                msg = "Slide is not in database. Do you wish to add it?"
                reply = QtWidgets.QMessageBox.question(self, 'Message',
                                                       msg, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

                if reply == QtWidgets.QMessageBox.Yes:
                    self.db.insertNewSlide(self.slidename,self.slidepathname)
                    self.findSlideUID(dimensions)
                    self.db.setSlideDimensions(slideUID, dimensions)
                    return
                else:
                    slname = self.openSlideDialog()
                    if (len(slname) == 0):
                        self.imageOpened=False
                        self.showImage()
            else:
                self.slideUID = slideUID
                self.db.setSlideDimensions(slideUID, dimensions)
            self.showDBstatistics()
        else:
            self.slideUID = None

    def resizeEvent(self, event):
        """
            Resize event, used as callback function when the application is resized.
        """
        super().resizeEvent(event)
        self.overlayMap=None
        if (self.activePlugin is not None) and (self.activePlugin.plugin.getAnnotationUpdatePolicy() == SlideRunnerPlugin.AnnotationUpdatePolicy.UPDATE_ON_SCROLL_CHANGE):
            self.pluginAnnos = list()
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
        return np.power(2,self.ui.zoomSlider.getValue()/100*(np.log2(0.5/ self.getMaxZoom())))*self.getMaxZoom()

    def updateImageCache(self):
        """
          Update image cache during times of inactivity
        """
        if (self.lastReadRequest is not None):
            self.read_region(self.lastReadRequest['location'], self.lastReadRequest['level'], self.lastReadRequest['size'], forceRead=True)
            newcache = dict()
            newcache['image'] = self.cachedImage
            newcache['level'] = self.cachedLevel
            newcache['location'] = self.cachedLocation

            self.updatedCacheAvailable.emit(newcache)


    def getMaxZoom(self):
        """
            Returns the maximum zoom available for this image.
        """
        return self.slide.level_dimensions[0][0] / self.mainImageSize[0]

    def setZoomValue(self, zoomValue):
        """
            Sets the zoom of the current image.
        """
        self.overlayMap=None
        if (self.activePlugin is not None) and (self.activePlugin.plugin.getAnnotationUpdatePolicy() == SlideRunnerPlugin.AnnotationUpdatePolicy.UPDATE_ON_SCROLL_CHANGE):
            self.pluginAnnos = list()
        self.currentZoom = zoomValue
        if (self.currentZoom < 0.5):
            self.currentZoom = 0.5
        maxzoom = self.getMaxZoom()
        if (self.currentZoom > maxzoom):
            self.currentZoom = maxzoom

        sliderVal = 100*np.log2(self.currentZoom/(maxzoom))/(np.log2(0.5/maxzoom))

        self.ui.zoomSlider.valueChanged.disconnect()
        self.ui.zoomSlider.setValue(sliderVal)
        self.ui.zoomSlider.valueChanged.connect(self.sliderChanged)
        if (self.currentZoom<1):
            self.ui.zoomSlider.setText('(%.1f x)' % (float(self.slideMagnification)/self.currentZoom))
        else:
            self.ui.zoomSlider.setText('%.1f x' % (float(self.slideMagnification)/self.currentZoom))

    def getZoomValue(self):
        """
            returns the current zoom value
        """
        return self.currentZoom

    def prepare_region_from_overview(self, location, level, size):
        locationInOverview = ( int(location[0]/self.slide.level_downsamples[-1]),
                               int(location[1]/self.slide.level_downsamples[-1]))
        scale = self.slide.level_downsamples[-1]/self.slide.level_downsamples[level]
        M = np.array([[scale,0,-locationInOverview[0]*scale],
             [0, scale, -locationInOverview[1]*scale]])
        sp = cv2.warpAffine(self.slideOverview[:,:,0:3], M, dsize=size)
        subpix_a = np.expand_dims(cv2.warpAffine(self.slideOverview[:,:,3], M, dsize=size),axis=2)
        return np.concatenate((sp, subpix_a), axis=2)
    """
        read_region: cached version of openslide's read_region.

        Reads from the original slide with 50% overlap to each side.

    """

    def image_in_cache(self, location, level, size):
        readNew = False
        coords = None
        if (not(level == self.cachedLevel) or (self.cachedLocation is None)):
            readNew = True
        
        if (self.cachedLocation is not None):
            x0 = int((location[0]-self.cachedLocation[0])/self.slide.level_downsamples[level])
            y0 = int((location[1]-self.cachedLocation[1])/self.slide.level_downsamples[level])
            x1 = x0 + size[0]
            y1 = y0 + size[1]
            if (x0<0) or (y0<0): # out of cache
                readNew = True
            
            if ((y1>self.cachedImage.shape[0]) or
                (x1>self.cachedImage.shape[1])):
                readNew = True

            coords = (x0,x1,y0,y1)
        return readNew,coords

    def read_region(self, location, level, size, forceRead = False):
        self.lastReadRequest = dict()
        self.lastReadRequest['location'] = location
        self.lastReadRequest['level'] = level
        self.lastReadRequest['size'] = size
        reader_location = (int(location[0]-1.*size[0]*self.slide.level_downsamples[level]),
                          int(location[1]-1.*size[1]*self.slide.level_downsamples[level]))
        reader_size = (int(size[0]*3), int(size[1]*3))
        readNew,coords = self.image_in_cache(location, level, size)
        
        if not readNew:
            (x0,x1,y0,y1) = coords
            ret = self.cachedImage[y0:y1,x0:x1,:]
            return ret
        else:
            # refill cache
            region = self.slide.read_region(location=reader_location,level=level,size=reader_size)
            # Convert to numpy array
            self.cachedImage = np.array(region, dtype=np.uint8)
            self.cachedLevel = level
            self.cachedLocation = reader_location
            x0 = int((location[0]-self.cachedLocation[0])/self.slide.level_downsamples[level])
            y0 = int((location[1]-self.cachedLocation[1])/self.slide.level_downsamples[level])
            x1 = x0 + size[0]
            y1 = y0 + size[1]
            return self.cachedImage[y0:y1,x0:x1,:]


    def updateCache(self, newcache):
        self.cachedImage = newcache['image']
        self.cachedLevel = newcache['level']
        self.cachedLocation = newcache['location']
#        self.showImage()


    def showImage(self):
        """
            showImage is an important function that is used for refreshing the image display.

            It's also being called a lot, basically after every change in the UI.
        """

        if (not self.imageOpened):
            return
        
        self.ui.zoomSlider.setMaxZoom(self.getMaxZoom())
        self.ui.zoomSlider.setMinZoom(2.0*np.float32(self.slideMagnification))

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
        npi = self.prepare_region_from_overview(location_im, act_level, size_im)

        self.processingStep += 1
        outOfCache,_ = self.image_in_cache(location_im, act_level, size_im)
#        npi = self.read_region(location=location_im,level=act_level,size=size_im)
        if (act_level == self.slide.level_count-1): # overview image is always correct from cache
            self.showImage_part2(npi, self.processingStep)
        elif not (outOfCache):
            npi = self.read_region(location_im, act_level, size_im)
            self.showImage_part2(npi, self.processingStep)

        else:
            npi=cv2.resize(npi, dsize=(self.mainImageSize[0],self.mainImageSize[1]))
            self.ui.MainImage.setPixmap(QPixmap.fromImage(self.toQImage(npi)))
            
            self.slideReaderThread.queue.put((location_im, act_level, size_im, self.processingStep))

    def showImage_part2(self, npi, id):
        if (len(npi.shape)==1): # empty was given as parameter - i.e. trigger comes from plugin
            npi = self.cachedLastImage

        self.cachedLastImage = npi

        if (id<self.processingStep):
            return

        aspectRatio_image = float(self.slide.level_dimensions[-1][0]) / self.slide.level_dimensions[-1][1]

        # Calculate real image size on screen
        if (self.ui.MainImage.frameGeometry().width()/aspectRatio_image<self.ui.MainImage.frameGeometry().height()):
            im_size=(self.ui.MainImage.frameGeometry().width(),int(self.ui.MainImage.frameGeometry().width()/aspectRatio_image))
        else:
            im_size=(int(self.ui.MainImage.frameGeometry().height()*aspectRatio_image),self.ui.MainImage.frameGeometry().height())


        # Resize to real image size
        npi=cv2.resize(npi, dsize=(self.mainImageSize[0],self.mainImageSize[1]))
        self.rawImage = np.copy(npi)

        # reset timer to reload image
        from threading import Timer
        if (self.refreshTimer is not None):
                self.refreshTimer.cancel()
        self.refreshTimer = Timer(1, self.updateImageCache)                
        self.refreshTimer.start()

        if (self.activePlugin is not None) and (self.overlayMap is None) and (len(self.pluginAnnos)==0):
            from threading import Timer
            if (self.updateTimer is not None):
                self.updateTimer.cancel()
            self.updateTimer = Timer(self.activePlugin.plugin.updateTimer, partial(self.triggerPlugin,np.copy(npi)))                
            self.updateTimer.start()

        if (self.overlayMap is not None) and (self.activePlugin is not None):
                if (self.activePlugin.plugin.outputType == SlideRunnerPlugin.PluginOutputType.BINARY_MASK):
                    olm = self.overlayMap
                    if ((len(olm.shape)==2) or ((len(olm.shape)==3) and (olm.shape[2]==1))) and np.all(npi.shape[0:2] == olm.shape[0:2]): 
                        self.overlayExtremes = [np.min(olm), np.max(olm)+np.finfo(np.float32).eps]
                        # Normalize overlay
                        olm = cv2.resize(self.overlayMap, dsize=(npi.shape[1],npi.shape[0]))
                        olm = (olm - self.overlayExtremes[0]) / (np.diff(np.array(self.overlayExtremes)))
                        
                        cm = matplotlib.cm.get_cmap(self.settings.value('OverlayColorMap'))

                        colorMap = cm(olm)
                        # alpha blend
                        npi = np.uint8(npi * (1-self.opacity) + colorMap * 255 * (self.opacity))

                    else:
                        print('Overlay map shape not proper')
                        print('OLM shape: ', olm.shape, 'NPI shape: ', npi.shape)
                elif (self.activePlugin.plugin.outputType == SlideRunnerPlugin.PluginOutputType.RGB_IMAGE):
                    olm = self.overlayMap
                    self.overlayExtremes = None
                    if (len(olm.shape)==3) and (olm.shape[2]==3) and np.all(npi.shape[0:2] == olm.shape[0:2]): 
                        for c in range(3):
                            npi[:,:,c] = np.uint8(np.clip(np.float32(npi[:,:,c])* (1-self.opacity) + self.opacity * (olm[:,:,c] ),0,255))
                    


        # Overlay Annotations by the user
        #npi = self.overlayAnnotations(npi)
        if (self.db.isOpen()):
            self.db.annotateImage(npi, self.region[0], self.region[0]+self.region[1], self.getZoomValue(), self.currentVP)
        
        if (self.activePlugin):
            for anno in self.pluginAnnos:
                anno.draw(npi, self.region[0], self.getZoomValue(), 2, self.get_color(0))

        # Show the current polygon (if in polygon annotation mode)
        if (self.db.isOpen()) & (self.ui.mode==UIMainMode.MODE_ANNOTATE_POLYGON) & (self.ui.annotationMode>0):
            npi = self.showPolygon(npi, self.ui.annotationsList, color=[0,0,0,255])

        # Copy displayed image
        self.displayedImage = npi

        # Display microns
        viewMicronsPerPixel = float(self.slideMicronsPerPixel) * float(self.currentZoom)

        legendWidth=150.0
        legendQuantization = 2.5
        if (viewMicronsPerPixel*legendWidth>2000):
            legendQuantization = 500.0
        elif (viewMicronsPerPixel*legendWidth>1000):
            legendQuantization = 100.0
        elif (viewMicronsPerPixel*legendWidth>200):
            legendQuantization = 100.0
        elif (viewMicronsPerPixel*legendWidth>50):
            legendQuantization = 25.0
        legendMicrons = np.floor(legendWidth*viewMicronsPerPixel/legendQuantization)*legendQuantization

        actualLegendWidth = int(legendMicrons/viewMicronsPerPixel)


        positionLegendX = 40
        positionLegendY = npi.shape[0]-40
        
        npi[positionLegendY:positionLegendY+20,positionLegendX:positionLegendX+actualLegendWidth,3] = 255
        npi[positionLegendY:positionLegendY+20,positionLegendX:positionLegendX+actualLegendWidth,:] = 255
        npi[positionLegendY:positionLegendY+20,positionLegendX+actualLegendWidth:positionLegendX+actualLegendWidth,:] = np.clip(npi[positionLegendY:positionLegendY+20,positionLegendX+actualLegendWidth:positionLegendX+actualLegendWidth,:]*0.2,0,255)
        npi[positionLegendY:positionLegendY+20,positionLegendX:positionLegendX,:] = np.clip(npi[positionLegendY:positionLegendY+20,positionLegendX:positionLegendX,:]*0.2,0,255)
        npi[positionLegendY,positionLegendX:positionLegendX+actualLegendWidth,:] = np.clip(npi[positionLegendY,positionLegendX:positionLegendX+actualLegendWidth,:]*0.2,0,255)
        npi[positionLegendY+20,positionLegendX:positionLegendX+actualLegendWidth,:] = np.clip(npi[positionLegendY+20,positionLegendX:positionLegendX+actualLegendWidth,:]*0.2,0,255)
        
        cv2.putText(npi, '%d microns' % legendMicrons, (positionLegendX, positionLegendY+15), cv2.FONT_HERSHEY_PLAIN , 0.7,(0,0,0),1,cv2.LINE_AA)

        if (self.overlayExtremes is not None):
            # Add legend for colour code
            positionColorLegendX = npi.shape[1]-80
            positionColorLegendY = npi.shape[0]-200
            colorLegendWidth = 20
            colorLegendHeight = 150


            opacity = np.zeros((colorLegendHeight,colorLegendWidth,3))
            cm = matplotlib.cm.get_cmap(self.settings.value('OverlayColorMap'))
            color = cm((np.linspace(1,0,colorLegendHeight)).reshape(-1,1) * np.ones((1,colorLegendWidth)))
            cv2.rectangle(img=npi, pt1=(positionColorLegendX,positionColorLegendY),
                          pt2=(positionColorLegendX+colorLegendWidth, positionColorLegendY+colorLegendHeight), color=[0,0,0,0])

            npi[positionColorLegendY:positionColorLegendY+colorLegendHeight,positionColorLegendX:positionColorLegendX+colorLegendWidth] = color*255
            
            _tsize = cv2.getTextSize( '%.2f' % np.max(np.abs(self.overlayExtremes[1])),cv2.FONT_HERSHEY_PLAIN , 0.7,1)
            npi[positionColorLegendY+colorLegendHeight-_tsize[0][1]-5:positionColorLegendY+colorLegendHeight+5,positionColorLegendX+colorLegendWidth+5:positionColorLegendX+colorLegendWidth+_tsize[0][0]+15,:] = np.clip(npi[positionColorLegendY+colorLegendHeight-_tsize[0][1]-5:positionColorLegendY+colorLegendHeight+5,positionColorLegendX+colorLegendWidth+5:positionColorLegendX+colorLegendWidth+_tsize[0][0]+15,:]*0.5+127,0,255)
            npi[positionColorLegendY-_tsize[0][1]:positionColorLegendY+10,positionColorLegendX+colorLegendWidth+5:positionColorLegendX+colorLegendWidth+_tsize[0][0]+15,:] = np.clip(npi[positionColorLegendY-_tsize[0][1]:positionColorLegendY+10,positionColorLegendX+colorLegendWidth+5:positionColorLegendX+colorLegendWidth+_tsize[0][0]+15,:]*0.5+127,0,255)
            cv2.putText(npi, '%.2f' % self.overlayExtremes[1], (positionColorLegendX+colorLegendWidth+10, positionColorLegendY+5),cv2.FONT_HERSHEY_PLAIN , 0.7,(0,0,0),1,cv2.LINE_AA)
            cv2.putText(npi, '%.2f' % self.overlayExtremes[0], (positionColorLegendX+colorLegendWidth+10, positionColorLegendY+colorLegendHeight),cv2.FONT_HERSHEY_PLAIN , 0.7,(0,0,0),1,cv2.LINE_AA)



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
        self.currentVP.activeClasses = items
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
            filename = self.settings.value('DefaultDatabase')
            if (filename is None):
                filename = SLIDE_DIRNAME + os.sep + 'Slides.sqlite'
                self.settings.setValue('DefaultDatabase', filename)
        success = self.db.open(filename)
        
        if not success:
            reply = QtWidgets.QMessageBox.information(self, 'Message',
                    'Warning: Database %s not found. Do you want to create a new database?' % filename, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

            if (reply == QtWidgets.QMessageBox.Yes):
                success = self.db.create(filename)

        if success:            
            filename = os.path.abspath(filename)
            lastdatabaseslist = self.settings.value('lastDatabases', type=list)
            if filename in (lastdatabaseslist):
                lastdatabaseslist.remove(filename)
            
            if (self.imageOpened):
                self.findSlideUID(self.slide.dimensions)
                self.db.loadIntoMemory(self.slideUID)


            lastdatabaseslist.append(filename)
            lastdatabaseslist = lastdatabaseslist[-11:]
            self.settings.setValue('lastDatabases', lastdatabaseslist)
            print('Last databases list is now: ',lastdatabaseslist)

            menu.updateOpenRecentDatabase(self)


            self.showDatabaseUIelements()
            self.showAnnotationsInOverview()
            self.writeDebug('Opened database')


            self.ui.iconBlinded.setEnabled(True)
            self.ui.iconQuestion.setEnabled(True)
            self.ui.saveto.setEnabled(True)

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
        self.ui.databaseLabel.setText(dbinfo)

        self.showDBstatistics()

    def findAnnoByID(self):
        if (self.db.isOpen() == False):
            return
        num,ok = QInputDialog.getInt(self, "Find by ID",  "Please give UID of annotation")
        if (ok):
            allAnnos = self.db.findAllAnnotations(num, self.slideUID)
            if (allAnnos is None) or len(allAnnos)==0:
                correctSlide = self.db.findSlideForAnnotation(num)
                if (correctSlide is None) or len(correctSlide)==0:
                    reply = QtWidgets.QMessageBox.information(self, 'Message',
                           'Not found in database.', QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)
                else:
                    reply = QtWidgets.QMessageBox.information(self, 'Message',
                           'Not found on slide. Please open "%s".' % correctSlide[0], QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)
                return
                
            coords = np.asarray(allAnnos)
            minC = np.min(coords,axis=0)
            maxC = np.max(coords,axis=0)
            diff = maxC-minC
            cent = np.int32(minC+(maxC-minC)/2)
            self.setCenterTo(cent[0],cent[1])
            self.setZoomTo(diff[0],diff[1])



    def showDBstatistics(self):
        """
            Show class-based statistics of current database
        """
        if (self.db.isOpen() == False):
            return
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
                style = 'background:#%x%x%x' % (int(self.get_color(k+1)[0]/16),
                                                int(self.get_color(k+1)[1]/16),
                                                int(self.get_color(k+1)[2]/16))
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
        self.ui.inspectorTableView.setVisible(True)
        self.ui.categoryView.setVisible(True)
        self.ui.annotatorComboBox.setVisible(True)

        self.showDBentryCount()

        persons = self.db.getAllPersons()
        personList=[]
        for person in persons:
            personList.append(person[0])

        self.annotatorsModel.setStringList(personList)
        self.ui.annotatorComboBox.setVisible(True)
        self.ui.annotatorComboBox.setEnabled(True)
        model = QStandardItemModel()
        
        self.ui.annotatorComboBox.currentIndexChanged.connect(self.changeAnnotator)

        model = QStandardItemModel()

        self.modelItems = list()
        classes =   self.db.getAllClasses()
        self.classButtons = list()
        self.ui.categoryView.setRowCount(len(classes)+1)
        self.ui.categoryView.setColumnCount(4)
        item = QTableWidgetItem('unknown')
        pixmap = QPixmap(10,10)
        pixmap.fill(QColor.fromRgb(self.get_color(0)[0],self.get_color(0)[1],self.get_color(0)[2]))
        itemcol = QTableWidgetItem('')
        itemcol.setBackground(QColor.fromRgb(self.get_color(0)[0],self.get_color(0)[1],self.get_color(0)[2]))
        checkbx = QCheckBox()
        checkbx.setChecked(True)
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
            pixmap.fill(QColor.fromRgb(self.get_color(clsid+1)[0],self.get_color(clsid+1)[1],self.get_color(clsid+1)[2]))
            btn = QPushButton('')

            btn.clicked.connect(partial(self.clickAnnoclass, clsid+1))
            self.classButtons.append(btn)
            itemcol = QTableWidgetItem('')
            checkbx = QCheckBox()
            checkbx.setChecked(True)
            itemcol.setBackground(QColor.fromRgb(self.get_color(clsid+1)[0],self.get_color(clsid+1)[1],self.get_color(clsid+1)[2]))
            self.modelItems.append(checkbx)
            self.ui.categoryView.setItem(clsid+1,2, item)
            self.ui.categoryView.setItem(clsid+1,1, itemcol)
            self.ui.categoryView.setCellWidget(clsid+1,0, checkbx)
            self.ui.categoryView.setCellWidget(clsid+1,3, btn)
            checkbx.stateChanged.connect(self.selectClasses)
            

        model.itemChanged.connect(self.selectClasses)

        self.itemsSelected = np.ones(len(classes)+1)
        self.currentVP.activeClasses = self.itemsSelected
        self.ui.categoryView.verticalHeader().setVisible(False)
        vheader = self.ui.categoryView.verticalHeader()
        vheader.setDefaultSectionSize(vheader.fontMetrics().height()+2)
        self.ui.categoryView.horizontalHeader().setVisible(False)
        self.ui.categoryView.setColumnWidth(0, 20)
        self.ui.categoryView.setColumnWidth(1, 20)
        self.ui.categoryView.setColumnWidth(2, 120)
        self.ui.categoryView.setColumnWidth(3, 50)
        self.ui.categoryView.setShowGrid(False)

        if (self.imageOpened):
            self.findSlideUID(self.slide.dimensions)
        else:
            self.findSlideUID()

        self.ui.annotatorComboBox.setModel(self.annotatorsModel)

        if (self.imageOpened):
            self.showImage()


    def sliderChanged(self):
        """
            Callback function for when a slider was changed.
        """
        print('Slider changed')
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
        filename = QFileDialog.getOpenFileName(filter='OpenSlide files (*.svs *.tif *.png *.bif *.svslide *.mrxs *.scn *.vms *.vmu *.ndpi *.tiff *.bmp);;Aperio SVS format (*.svs);;All files (*.*)')[0]
        if (len(filename)==0):
            return ''
        self.openSlide(filename)
        return filename
    
    def initZoomSlider(self):
        """
            Initialize the scrollbar slider.
        """
        self.ui.zoomSlider.valueChanged.connect(self.sliderChanged)

    def saveDBto(self):
        filename = QFileDialog.getSaveFileName(filter='*.sqlite')[0]
        if filename is not None and len(filename)>0:
            self.db.saveTo(filename)

    def settingsDialog(self):
        settingsDialog(self.settings)
        self.currentVP.spotCircleRadius = self.settings.value('SpotCircleRadius')
        self.showImage()

    def openSlide(self, filename):
        """
            Helper function to open a whole slide image
        """
        if not (os.path.exists(filename)):
            reply = QtWidgets.QMessageBox.information(self, 'Error',
                           'File not found: %s' % filename, QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)
            return

        self.slide = openslide.open_slide(filename)
        if (openslide.PROPERTY_NAME_OBJECTIVE_POWER in self.slide.properties):
            self.slideMagnification = self.slide.properties[openslide.PROPERTY_NAME_OBJECTIVE_POWER]
        else:
            self.slideMagnification = 1

        if (openslide.PROPERTY_NAME_MPP_X in self.slide.properties):
            self.slideMicronsPerPixel = self.slide.properties[openslide.PROPERTY_NAME_MPP_X]
        else:
            self.slideMicronsPerPixel = 1E-6
        self.slidename = os.path.basename(filename)

        # unhide label and show filename
        self.ui.filenameLabel.setText(self.slidename)
        self.ui.filenameLabel.setHidden(False)
        self.slidepathname = filename
        self.imageOpened=True
        self.ui.statusbar.showMessage(filename+': '+str(self.slide.dimensions))

        if (self.db.isOpen()):
            self.findSlideUID(self.slide.dimensions)
            t = time.time()
            self.db.loadIntoMemory(self.slideUID)
            print('Took: ',time.time()-t)

        self.relativeCoords = np.asarray([0,0], np.float32)
        self.lastScreeningLeftUpper = np.zeros(2)
        self.screeningHistory = list()
        self.screeningIndex = 0

        self.thumbnail = thumbnail.thumbnail(self.slide)

        # Read overview thumbnail from slide
        overview = self.slide.read_region(location=(0,0), level=self.slide.level_count-1, size=self.slide.level_dimensions[-1])
        self.slideOverview = np.asarray(overview)
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

        filename = os.path.abspath(filename)
        lastslideslist = self.settings.value('LastSlides', type=list)
        if filename in (lastslideslist):
            lastslideslist.remove(filename)

        lastslideslist.append(filename)
        lastslideslist = lastslideslist[-11:]
        self.settings.setValue('LastSlides', lastslideslist)
        menu.updateOpenRecentSlide(self)




def main():
    style.setStyle(app)    

    myapp = SlideRunnerUI()
    myapp.show()
    myapp.raise_()
    splash.finish(myapp)

    if (myapp.activePlugin is not None):
        myapp.activePlugin.inQueue.put(None)
        myapp.activePlugin.inQueue.put(SlideRunnerPlugin.jobToQueueTuple(description=SlideRunnerPlugin.JobDescription.QUIT_PLUGIN_THREAD))

    sys.exit(app.exec_())

if __name__ == "__main__":

    main()
