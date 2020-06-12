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
            shapely             1.6.4
            rollbar             0.14



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



SLIDERUNNER_DEBUG = False


from SlideRunner.general import dependencies
import sys
import multiprocessing
from multiprocessing import freeze_support

dependencies.check_qt_dependencies()

from PyQt5 import QtWidgets, QtGui, QtCore
from SlideRunner.gui import splashScreen, menu, style
from PyQt5.QtWidgets import QMainWindow


# Splash screen is displayed, go on with the rest.

from SlideRunner.general.dependencies import *
from SlideRunner.dataAccess.annotations import ViewingProfile
from SlideRunner.dataAccess.slide import SlideReader
from PyQt5.QtCore import QSettings

# Thread for receiving images from the plugin
class imageReceiverThread(threading.Thread):

    def __init__(self, queue, selfObj):
        threading.Thread.__init__(self)
        self.queue = queue
        self.selfObj = selfObj

    def run(self):
        while True:
            (img, procId) = self.queue.get()
            self.selfObj.overlayMap = img
            self.selfObj.showImage3Request.emit(np.empty(0), procId)
                        

class SlideImageReceiverThread(threading.Thread):
    def __init__(self, selfObj, readerqueue):
        threading.Thread.__init__(self)
        self.queue = readerqueue
        self.selfObj = selfObj

    def run(self):
        while True:
            (img, procId) = self.queue.get()
            self.selfObj.readRegionCompleted.emit(img,procId)

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
            elif (msgId == SlideRunnerPlugin.StatusInformation.UPDATE_LABELS):
                self.selfObj.updatePluginLabels.emit()
            elif (msgId == SlideRunnerPlugin.StatusInformation.REFRESH_VIEW):
                self.selfObj.refreshReceived.emit()
            elif (msgId == SlideRunnerPlugin.StatusInformation.REFRESH_DATABASE):
                self.selfObj.refreshDatabase.emit()


class SlideRunnerUI(QMainWindow):
    progressBarChanged = pyqtSignal(int)
    showImageRequest = pyqtSignal(np. ndarray, int)
    showImage3Request = pyqtSignal(np. ndarray, int)
    readRegionCompleted = pyqtSignal(np.ndarray, int)
    statusViewChanged = pyqtSignal(str)
    annotationReceived = pyqtSignal(list)
    updatedCacheAvailable = pyqtSignal(dict)
    setZoomReceived = pyqtSignal(float)
    setCenterReceived = pyqtSignal(tuple)
    updatePluginConfig = pyqtSignal(SlideRunnerPlugin.PluginConfigUpdate)
    updatePluginLabels = pyqtSignal()
    refreshReceived = pyqtSignal()
    refreshDatabase = pyqtSignal()
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
    pluginFilepickers = dict()
    pluginComboboxes = dict()
    currentVP = ViewingProfile()
    currentPluginVP = ViewingProfile()
    lastReadRequest = None
    cachedLocation = None
    cachedLevel = None
    pluginTextLabels = dict()
    cachedImage = None
    selectedPluginAnno = None
    selectedAnno = None
    pluginParameterSliders = dict()
    refreshTimer = None


    def __init__(self,slideReaderThread, app, version,pluginList):
        super(SlideRunnerUI, self).__init__()

        self.settings = QSettings('Pattern Recognition Lab, FAU Erlangen Nuernberg', 'SlideRunner')

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
        self.onOpen = True
        self.ui = addSidebar(self.ui, self)
        self.ui.moveDots=0
        self.currentZoom = 1
        self.dragPoint=False
        self.annotationsSpots=list()
        self.annotationsArea = list()
        self.annotationsCircle = list()
        self.annotationsList = list()
        self.ui.wandAnnotation = WandAnnotation()
        self.slidename=''
        self.slideUID = 0
        self.region = [[0,0],[0,0]]
        self.slideReaderThread = slideReaderThread
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
        self.showImage3Request.connect(self.showImage_part3)
        self.annotationReceived.connect(self.receiveAnno)
        self.refreshReceived.connect(self.receiveRefresh)
        self.refreshDatabase.connect(self.reopenDatabase)
        self.updatePluginConfig.connect(self.updatePluginConfiguration)
        self.updatePluginLabels.connect(self.showDatabaseUIelements)
        self.updatedCacheAvailable.connect(self.updateCache)
        self.setZoomReceived.connect(self.setZoom)
        self.setCenterReceived.connect(self.setCenter)
        self.readRegionCompleted.connect(self.showImage_part2)
        self.pluginPopupMessageReceived.connect(self.popupmessage)
        self.ui.frameSlider.valueChanged.connect(self.frameChanged)

        self.pluginStatusReceiver = PluginStatusReceiver(self.progressBarQueue, self)
        self.pluginStatusReceiver.setDaemon(True)
        self.pluginStatusReceiver.start()

        
    
        self.slideImageReceiverThread = SlideImageReceiverThread(self, readerqueue=self.slideReaderThread.outputQueue)
        self.slideImageReceiverThread.setDaemon(True)
        self.slideImageReceiverThread.start()


        self.wheelEvent = partial(mouseEvents.wheelEvent,self)

        self.ui.MainImage.setPixmap(self.vidImageToQImage(127*np.ones((600,600,3),np.uint8)))
        self.ui.MainImage.mousePressEvent = partial(mouseEvents.pressImage, self)
        self.ui.MainImage.mouseReleaseEvent = partial(mouseEvents.releaseImage, self)
        self.ui.MainImage.mouseMoveEvent = partial(mouseEvents.moveImage,self)
        self.ui.MainImage.mouseDoubleClickEvent = partial(mouseEvents.doubleClick,self)
        self.ui.OverviewLabel.setPixmap(self.vidImageToQImage(127*np.ones((200,200,3),np.uint8)))
        self.overviewimage = 127*np.ones((200,200,3),np.uint8)
        self.opacity = 0.5
        self.ui.annotationsList = []
        self.ui.annotationUID=None

        self.mainImageSize = np.asarray([self.ui.MainImage.frameGeometry().width(),self.ui.MainImage.frameGeometry().height()])
        self.ui.OverviewLabel.mousePressEvent = self.pressOverviewImage

        self.ui.opacitySlider.setHidden(True)
        self.ui.opacityLabel.setHidden(True)
        self.pluginList = pluginList

        if (self.settings.value('exactSupportEnabled') is None):
            welcomeExactDialog(app, self.settings, self)
        

        menu.defineMenu(self.ui, self, pluginList)
        menu.defineAnnotationMenu(self)

        shortcuts.defineMenuShortcuts(self)

        self.checkSettings()
        self.currentVP.spotCircleRadius = self.settings.value('SpotCircleRadius')
        self.currentPluginVP.spotCircleRadius = self.settings.value('SpotCircleRadius')
        if (isinstance(self.settings.value('rotateImage',False),str)):
            self.rotateImage = True if self.settings.value('rotateImage').upper()=='TRUE' else False
        else:
            self.rotateImage = bool(self.settings.value('rotateImage',False))


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

    def show_exception(self, headline, exctype, value, tb):
        excmsg = '\n'.join(traceback.format_exception(exctype, value, tb))
        msgBox = QtWidgets.QMessageBox()
        msgBox.setText("Uncaught exception")
        msgBox.setInformativeText(headline)
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        btn = msgBox.addButton(QtWidgets.QPushButton('Report to developers'), QtWidgets.QMessageBox.YesRole)
        msgBox.setDetailedText(excmsg)
        msgBox.setDefaultButton(btn)
        ret = msgBox.exec()      
        if (ret == 0): # Yes was pressed  
            rollbar.report_exc_info((exctype, value, tb))

    def exceptionHook_threading(self, exctype, value, tb):
        self.show_exception("Thread was terminated", exctype, value, tb)

    def exceptionHook(self, exctype, value, tb):
        self.show_exception("Exception", exctype, value, tb)

    def refreshMenu(self):
        menu.defineMenu(self.ui, self, self.pluginList, initial=False)
        menu.defineAnnotationMenu(self)

        shortcuts.defineMenuShortcuts(self)


    def get_color(self, idx):
        colors = [[0,0,0,0],[0,0,255,255],[0,255,0,255],[255,255,0,255],[255,0,255,255],[0,127,0,255],[255,127,0,255],[127,127,0,255],[255,200,200,255],[10, 166, 168,255],[166, 10, 168,255],[166,168,10,255]]

        return colors[idx % len(colors)]


    def checkSettings(self):
        if (self.settings.value('OverlayColorMap') == None):
            self.settings.setValue('OverlayColorMap', 'hot')
        if (self.settings.value('SpotCircleRadius') == None):
            self.settings.setValue('SpotCircleRadius', 25)
        if (self.settings.value('GuidedScreeningThreshold') == None):
            self.settings.setValue('GuidedScreeningThreshold', 'OTSU')

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

    def receiveRefresh(self):
        self.showImage()

    def reopenDatabase(self):
        self.db.loadIntoMemory(self.slideUID)
        self.showDatabaseUIelements()
        self.showDBstatistics()

    def receiveAnno(self, anno):
        self.pluginAnnos = anno
        self.pluginMinCoords, self.pluginMaxCoords = SlideRunnerPlugin.generateMinMaxCoordsList(anno)
        self.showImage_part3(np.empty(shape=(1)), self.processingStep)

    #receivePluginInformation
    def receivePluginInformation(self, pluginInformation):
        self.pluginInformation = pluginInformation

        self.pluginTableWidget.clearContents()

        self.pluginTableWidget.setRowCount(len(pluginInformation))
        self.pluginTableWidget.setColumnCount(2)
        self.pluginTableWidget.setHorizontalHeaderLabels(["Key", "Value"])

        for id, key in enumerate(self.pluginInformation):
            self.pluginTableWidget.setItem(id,0, QTableWidgetItem(str(key)))
            self.pluginTableWidget.setItem(id,1, QTableWidgetItem(str(self.pluginInformation[key])))


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
        
        labelObj.setText('...'+ret[-20:] if len(ret)>20 else ret)
        self.pluginFilepickers[config.uid]['value'] = ret

        if (ret is not None) and (self.imageOpened):
            self.triggerPlugin(self.cachedLastImage, trigger=config)

    def pluginControlButtonHit(self, btn):
        self.overlayMap = None
        self.pluginAnnos = list()
        self.triggerPlugin(self.cachedLastImage, trigger=btn)

    def pluginComboboxChanged(self, option, index):

        option.selected_value = index.currentText()
        self.triggerPlugin(self.cachedLastImage, trigger=option)



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
            self.pluginComboboxes = dict()
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
                    self.pluginFilepickers[pluginConfig.uid] = {'button' : newButton, 'label' : newLabel, 'value' : ''}
                    
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
                elif (pluginConfig.type == SlideRunnerPlugin.PluginConfigurationType.TABLE):
                    self.pluginTableWidget = QTableWidget()
                    self.pluginTableWidget.setHorizontalHeaderLabels(['Key', 'Value'])

                    self.ui.tab3Layout.addWidget(self.pluginTableWidget)
                elif (pluginConfig.type == SlideRunnerPlugin.PluginConfigurationType.COMBOBOX):
                    cb = QtWidgets.QComboBox()
                    cb.setToolTip(pluginConfig.name)
                    cb.addItems(pluginConfig.options)

                    self.ui.tab3Layout.addWidget(cb)
                    self.pluginComboboxes[pluginConfig.uid] = cb
                    if (isinstance(pluginConfig.selected_value,int)):
                        cb.setCurrentIndex(pluginConfig.selected_value)
                    cb.currentIndexChanged.connect(partial(self.pluginComboboxChanged, pluginConfig, cb))

                
                

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
            for uid in self.pluginComboboxes.keys():
                self.ui.tab3Layout.removeWidget(self.pluginComboboxes[uid])
                self.pluginComboboxes[uid].deleteLater()



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
            self.pluginItemsSelected = None
            self.addActivePluginToSidebar(plugin.plugin)
            self.showDatabaseUIelements()
            if ((plugin.plugin.outputType != SlideRunnerPlugin.PluginOutputType.NO_OVERLAY)
                and (plugin.plugin.outputType != SlideRunnerPlugin.PluginOutputType.RGB_IMAGE)):
                self.ui.opacitySlider.valueChanged.disconnect(self.changeOpacity)                
                self.ui.opacitySlider.setValue(int(plugin.plugin.initialOpacity*100))
                self.opacity = plugin.plugin.initialOpacity
                self.ui.opacitySlider.valueChanged.connect(self.changeOpacity)
                self.ui.opacitySlider.setHidden(False)
                self.ui.opacitySlider.setEnabled(True)
                self.ui.opacityLabel.setHidden(False)
            else:
                self.ui.opacityLabel.setHidden(True)
                self.ui.opacitySlider.setHidden(True)
            if (self.imageOpened):
                self.triggerPlugin(self.rawImage)
        else:
            self.activePlugin = None
            self.ui.opacityLabel.setHidden(True)
            self.ui.opacitySlider.setHidden(True)

        print('Active plugin is now ', self.activePlugin)
        self.overlayMap = None
        self.pluginAnnos = list()
        if not active:
            self.showImage()

    """
        Aggregate plugin configuration alltogether
    """

    def gatherPluginConfig(self):
        config = dict()
        for key in self.pluginParameterSliders.keys():
            config[key] = self.pluginParameterSliders[key].value()/1000.0
        for key in self.pluginFilepickers.keys():
            config[key] = self.pluginFilepickers[key]['value']
        for key in self.pluginComboboxes.keys():
            config[key] = self.pluginComboboxes[key].currentIndex()
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

        print('Plugin triggered...',self.gatherPluginConfig())
        image_dims=self.slide.level_dimensions[0]
        actual_downsample = self.getZoomValue()
        visualarea = self.mainImageSize
        slidecenter = np.asarray(self.slide.level_dimensions[0])/2

        imgarea_p1 = slidecenter - visualarea * actual_downsample / 2 + self.relativeCoords*slidecenter*2
        imgarea_w =  visualarea * actual_downsample

        coordinates = (int(imgarea_p1[0]), int(imgarea_p1[1]), int(imgarea_w[0]), int(imgarea_w[1]))

        if (self.activePlugin is not None):
            self.activePlugin.inQueue.put(SlideRunnerPlugin.jobToQueueTuple(currentImage=currentImage, slideFilename=self.slidepathname, configuration=self.gatherPluginConfig(), annotations=annotations, trigger=trigger,coordinates=coordinates, actionUID=actionUID, openedDatabase=self.db))


    """
    Helper function to reset screening completely
    """

    def resetGuidedScreening(self):
            self.lastScreeningLeftUpper = np.zeros(2)
            self.screeningMap.reset(self.settings.value('GuidedScreeningThreshold'))
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

    def setRotate(self):
        self.rotateImage = not self.rotateImage
        self.settings.setValue('rotateImage',self.rotateImage)
        self.ui.rotate.setChecked(self.settings.value('rotateImage', False))
        self.slide.rotate = self.rotateImage
        if (self.db.isOpen() == True):
            self.db.loadIntoMemory(self.slideUID, transformer=self.slide.transformCoordinates)
        self.updateOverview()
        self.showImage()

    def previousScreeningStep(self):
        if not (self.imageOpened):
            return

        if not (self.screeningMode):
            return


        if (self.screeningIndex-1<=-len(self.screeningHistory)):
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
            self.ui.iconPreviousScreen.setEnabled(True)


        relOffset_x = self.mainImageSize[0] / self.slide.level_dimensions[0][0]
        relOffset_y =  self.mainImageSize[1] / self.slide.level_dimensions[0][1]

        newImageFound=False
        # find next image in grid. 
        while (not newImageFound):
            # advance one step to the right

            if (self.screeningMap.checkIsNew(self.lastScreeningLeftUpper)):
                newImageFound=True
                continue

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
        self.ui.iconPreviousScreen.setEnabled(False)

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
            reply = QtWidgets.QMessageBox.question(self, 'Question',
                                          'Do you want to cancel your polygon annotation?', QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

            if reply == QtWidgets.QMessageBox.No:
                return

            if (self.ui.annotationMode==2): #replace polygon object
                self.db.annotations[self.ui.annotationUID].deleted=False # make visible again
            self.ui.annotationMode=0
            self.showImage()

    def setUIMode(self,mode: UIMainMode):
        if (self.ui.mode == UIMainMode.MODE_ANNOTATE_POLYGON) and not (mode == UIMainMode.MODE_ANNOTATE_POLYGON ) and (self.ui.annotationMode>0):
            reply = QtWidgets.QMessageBox.question(self, 'Question',
                                          'Do you want to stop your polygon annotation? Hint: If you want to move the image during annotation, hold shift while dragging the image.', QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

            if reply == QtWidgets.QMessageBox.No:
                return
            
            if (self.ui.annotationMode==2): #replace polygon object
                self.db.annotations[self.ui.annotationUID].deleted=False # make visible again
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
        self.ui.iconWand.setChecked(False)

        if (self.ui.mode == UIMainMode.MODE_VIEW):
            self.menuItemView.setChecked(True)
            self.ui.iconView.setChecked(True)
        elif (self.ui.mode == UIMainMode.MODE_ANNOTATE_SPOT):
            self.menuItemAnnotateCenter.setChecked(True)
            self.ui.iconCircle.setChecked(True)
        elif (self.ui.mode == UIMainMode.MODE_ANNOTATE_WAND):
            self.menuItemAnnotateWand.setChecked(True)
            self.ui.iconWand.setChecked(True)
        elif (self.ui.mode == UIMainMode.MODE_ANNOTATE_AREA):
            self.menuItemAnnotateArea.setChecked(True)
            self.ui.iconRect.setChecked(True)
        elif (self.ui.mode == UIMainMode.MODE_ANNOTATE_POLYGON):
            self.menuItemAnnotateOutline.setChecked(True)
            self.ui.iconPolygon.setChecked(True)
        elif (self.ui.mode == UIMainMode.MODE_ANNOTATE_FLAG):
            self.menuItemAnnotateFlag.setChecked(True)
            self.ui.iconFlag.setChecked(True)
        elif (self.ui.mode == UIMainMode.MODE_ANNOTATE_WAND):
            self.menuItemAnnotateWand.setChecked(True)
            self.ui.iconWand.setChecked(True)

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
            image_dims=self.slide.level_dimensions[0]
            self.ui.statusbar.showMessage(self.slidename+': '+str(self.slide.dimensions)+' Position: (%d,%d)' % (int((self.relativeCoords[0]+0.5)*image_dims[0]), int((self.relativeCoords[1]+0.5)*image_dims[1])))
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
        markersize = 4
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
        markersize = 6
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

        getdesc = entry.getDescription(self.db,micronsPerPixel=self.slideMicronsPerPixel)
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

    def setAgreedAnno(self, classId, event, annoId):
        self.db.setAgreedClass(classId, annoId)
        self.writeDebug('changed agreed class for object with class %d, slide %d, person %d, ID %d' % ( classId, self.slideUID,self.retrieveAnnotator(event), annoId))
        self.showImage()

    def changeAnnotation(self, classId, event, labelIdx, annoId):
        self.db.setAnnotationLabel(classId, self.retrieveAnnotator(event), labelIdx, annoId)
        self.writeDebug('changed label for object with class %d, slide %d, person %d, ID %d' % ( classId, self.slideUID,self.retrieveAnnotator(event), annoId))
        self.showImage()

    def addAnnotationLabel(self, classId, event, annoId ):
        self.writeDebug('new label for object with class %d, slide %d, person %d, ID %d' % ( classId, self.slideUID,self.retrieveAnnotator(event), annoId))
        self.db.addAnnotationLabel(classId, self.retrieveAnnotator(event), annoId)
        self.saveLastViewport()
        self.showImage()

    def changeAnnoID(self, annoId):
        """
            Callback if the user wants to change an annotation ID
        """
        num,ok = QInputDialog.getInt(self, "Change annotation UID",  "Please give new UID of annotation")

        if (ok):
            if (self.db.changeAnnotationID(annoId, num)):
                self.showImage()
            else:
                self.popupmessage(f'Error: ID already used. ')
                

    def extendPolygonPoint(self, point_idx:int, anno_uid:int):
        # retrieve complete annotation from DB
        annocoords = self.db.annotations[anno_uid].coordinates
        self.db.annotations[anno_uid].deleted=True
        
        annocoords = np.vstack((annocoords[point_idx+1:,:],annocoords[0:point_idx,:]))


        # switch to polygon annoation mode
        self.setUIMode(UIMainMode.MODE_ANNOTATE_POLYGON)
        self.ui.annotationsList = annocoords.tolist()
        self.ui.annotationUID = anno_uid
        self.ui.annotationMode=2
        self.showImage()


    def removePolygonPoint(self, point_idx:int, anno_uid:int):
        self.db.removePolygonPoint(annoId=anno_uid, coord_idx=point_idx)
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

    def simplifyPolygon(self, annoId):
        val, okpressed = QtWidgets.QInputDialog.getDouble(self, "Threshold",  "Set the threshold (higher = more simplification)", 0.0001, 0, 0.02, 5)
        if (okpressed):
            oldC = self.db.annotations[annoId].coordinates
            epsilon = val*cv2.arcLength(self.db.annotations[annoId].coordinates,True)

            cont = cv2.approxPolyDP(self.db.annotations[annoId].coordinates,epsilon,True)
            cont = cont.squeeze()
            self.db.annotations[annoId].coordinates = cont
            self.showImage()

            reply = QtWidgets.QMessageBox.question(self, 'Question', 'Simplification done. Accept?',QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.Yes:
                ## simplify path in DB
                self.db.setPolygonCoordinates(annoId, cont, self.slideUID, zLevel=self.zPosition)
                pass
            else:
                self.db.annotations[annoId].coordinates = oldC
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



    def addAnnotator(self):
        """
            Add new annotator (person) to database.
        """
        attr = 'first' if (len(self.db.getAllPersons())==0) else 'new'

        name, ok = QInputDialog.getText(self, f"Please give a name for the {attr} expert",
                                        f"{attr} expert name:                               ")

        if (ok):
            id = self.db.insertAnnotator(name)
            if (attr=='first'):
                self.db.setExactPerson(id) # if only one expert defined, set this to be the EXACT person
            # show DB overview
            self.showDatabaseUIelements()

    def addCellClass(self):
        """
            Add new cell class to database.
        """
        attr = 'first' if len(self.db.getAllClasses())==0 else 'new'
        name, ok = QInputDialog.getText(self, f"Please give a name for the {attr} category",
                                          f"{attr} class name:                             ")
        if (ok):
            self.db.insertClass(name)
            # show DB overview
            self.showDatabaseUIelements()


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
            
            if hasattr(self.slide, 'seriesInstanceUID'):
                uid = self.slide.seriesInstanceUID
            else:
                uid = None
            
            slideUID = self.db.findSlideWithFilename(self.slidename,self.slidepathname, uuid=uid)

            if (slideUID is None):
                msg = "Slide is not in database. Do you wish to add it?"
                reply = YesNoAbortDialog('Question',msg,'Yes, add it.','No, open other slide', 'No, open other DB')
                if reply == QtWidgets.QMessageBox.Yes:
                    self.db.insertNewSlide(self.slidename,self.slidepathname, uid)
                    self.findSlideUID(dimensions)
                    self.db.setSlideDimensions(slideUID, dimensions)
                    return
                elif reply== QtWidgets.QMessageBox.No:
                    slname = self.openSlideDialog()
                    self.findSlideUID()
#                    if (len(slname) == 0):
#                        self.imageOpened=False
#                        self.showImage()
                elif reply == QtWidgets.QMessageBox.Abort:
                    self.openCustomDB()
                    self.findSlideUID(dimensions)
                else:
                    print('Reply was: ',reply)

                
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
        self.mainImageSize = np.asarray([self.ui.MainImage.frameGeometry().width(),self.ui.MainImage.frameGeometry().height()])

        if (event.oldSize() == event.size()):
            return
        

        self.overlayMap=None
        if (self.activePlugin is not None) and (self.activePlugin.plugin.getAnnotationUpdatePolicy() == SlideRunnerPlugin.AnnotationUpdatePolicy.UPDATE_ON_SCROLL_CHANGE):
            self.pluginAnnos = list()
        if (self.imageOpened):
            self.showImage()
            self.updateScrollbars()
        if (event is not None):
            event.accept()

        


    def sliderToZoomValue(self):
        """
            Convert slider position to zoom value
        """
        return np.power(2,self.ui.zoomSlider.getValue()/100*(np.log2(0.5/ self.getMaxZoom())))*self.getMaxZoom()



    def getMaxZoom(self):
        """
            Returns the maximum zoom available for this image.
        """
        return max(self.slide.level_dimensions[0][0] / self.mainImageSize[0],self.slide.level_dimensions[0][1] / self.mainImageSize[1]) * 1.2

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
        if 32 in self.slide.level_downsamples:
            level_overview = np.where(np.array(self.slide.level_downsamples)==32)[0][0] # pick overview at 32x
        else:
            level_overview = self.slide.level_count-1

        locationInOverview = ( int(location[0]/self.slide.level_downsamples[level_overview]),
                               int(location[1]/self.slide.level_downsamples[level_overview]))
        scale = self.slide.level_downsamples[level_overview]/self.slide.level_downsamples[level]
        M = np.array([[scale,0,-locationInOverview[0]*scale],
             [0, scale, -locationInOverview[1]*scale]])
        sp = cv2.warpAffine(self.slideOverview[:,:,0:3], M, dsize=size)
        subpix_a = np.expand_dims(cv2.warpAffine(self.slideOverview[:,:,3], M, dsize=size),axis=2)
        return np.concatenate((sp, subpix_a), axis=2)

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
        self.overviewimage = self.thumbnail.annotateCurrentRegion(npi, imgarea_p1, imgarea_w)

        # annotate on screening map
        self.screeningMap.annotate(imgarea_p1, imgarea_w)

        if (self.overviewOverlayHeatmap):
            self.overviewimage = self.screeningMap.overlayHeatmap(self.overviewimage)


        # Set pixmap of overview image (display overview image)
        self.ui.OverviewLabel.setPixmap(self.vidImageToQImage(self.overviewimage))

        # Now for the main image

        # Find the closest available downsampling factor
        closest_ds = self.slide.level_downsamples[np.argmin(np.abs(np.asarray(self.slide.level_downsamples)-self.getZoomValue()))]

        act_level = np.argmin(np.abs(np.asarray(self.slide.level_downsamples)-self.getZoomValue()))

        self.region = [imgarea_p1, imgarea_w]

        # Calculate size of the image
        size_im = (int(imgarea_w[0]/closest_ds), int(imgarea_w[1]/closest_ds))
        location_im = (int(imgarea_p1[0]), int(imgarea_p1[1]))

        # Read from Whole Slide Image Overview
#        npi = self.prepare_region_from_overview(location_im, act_level, size_im)

        self.processingStep += 1
#        outOfCache,_ = self.image_in_cache(location_im, act_level, size_im)

        if 32 in self.slide.level_downsamples:
            level_overview = np.where(np.array(self.slide.level_downsamples)==32)[0][0] # pick overview at 32x
        else:
            level_overview = self.slide.level_count-1

        self.slideReaderThread.queue.put((self.slidepathname, location_im, act_level, size_im, self.processingStep, self.rotateImage, self.zPosition))

    def closeEvent(self, event):
        self.slideReaderThread.queue.put((-1,0,0,0,0,0,0))
        self.slideReaderThread.join(0)
        event.accept()

    def showImage_part2(self, npi, id):

        self.mainImageSize = np.asarray([self.ui.MainImage.frameGeometry().width(),self.ui.MainImage.frameGeometry().height()])


        aspectRatio_image = float(self.slide.level_dimensions[-1][0]) / self.slide.level_dimensions[-1][1]

        # Calculate real image size on screen
        if (self.ui.MainImage.frameGeometry().width()/aspectRatio_image<self.ui.MainImage.frameGeometry().height()):
            im_size=(self.ui.MainImage.frameGeometry().width(),int(self.ui.MainImage.frameGeometry().width()/aspectRatio_image))
        else:
            im_size=(int(self.ui.MainImage.frameGeometry().height()*aspectRatio_image),self.ui.MainImage.frameGeometry().height())

        # Resize to real image size
        npi=cv2.resize(npi, dsize=(self.mainImageSize[0],self.mainImageSize[1]))
        self.rawImage = np.copy(npi)
        if ((id<self.processingStep) and 
            ((self.activePlugin is None) or (self.activePlugin.instance.pluginType != SlideRunnerPlugin.PluginTypes.IMAGE_PLUGIN))):
            self.ui.MainImage.setPixmap(QPixmap.fromImage(self.toQImage(self.rawImage)))
            return

        if ((self.activePlugin is not None) and (self.overlayMap is None) and 
           ((self.activePlugin.plugin.getAnnotationUpdatePolicy() == SlideRunnerPlugin.AnnotationUpdatePolicy.UPDATE_ON_SLIDE_CHANGE ) or 
            self.activePlugin.instance.pluginType == SlideRunnerPlugin.PluginTypes.IMAGE_PLUGIN)):
            from threading import Timer
            if (self.updateTimer is not None):
                self.updateTimer.cancel()
            self.updateTimer = Timer(self.activePlugin.plugin.updateTimer, partial(self.triggerPlugin,np.copy(npi)))                
            self.updateTimer.start()
        
        self.cachedLastImage = np.copy(npi)
        self.showImage_part3(npi, id)

    def showImage_part3(self, npi, id):
        if (len(npi.shape)==1): # empty was given as parameter - i.e. trigger comes from plugin
            npi = np.copy(self.cachedLastImage)

        if (self.activePlugin is not None) and (self.overlayMap is None) and ((self.activePlugin.plugin.outputType == SlideRunnerPlugin.PluginOutputType.RGB_IMAGE)):
            return

        if (self.overlayMap is not None) and (self.activePlugin is not None):
                if (self.activePlugin.plugin.outputType == SlideRunnerPlugin.PluginOutputType.BINARY_MASK):
                    olm = self.overlayMap
                    if ((len(olm.shape)==2) or ((len(olm.shape)==3) and (olm.shape[2]==1))) and np.all(npi.shape[0:2] == olm.shape[0:2]): 
                        self.overlayExtremes = [np.min(olm), np.max(olm)+np.finfo(np.float32).eps]
                        # Normalize overlay
                        if (self.overlayMap is not None):
                            olm = cv2.resize(self.overlayMap, dsize=(npi.shape[1],npi.shape[0]))
                            olm = (olm - self.overlayExtremes[0]) / (np.diff(np.array(self.overlayExtremes)))
                            
                            cm = matplotlib.cm.get_cmap(self.settings.value('OverlayColorMap'))

                            colorMap = cm(olm)
                            # alpha blend
                            npi = np.uint8(npi * (1-self.opacity) + colorMap * 255 * (self.opacity))

                    else:
                        print('Overlay map shape not proper')
                        print('OLM shape: ', olm.shape, 'NPI shape: ', npi.shape)
                elif ((self.activePlugin.plugin.outputType == SlideRunnerPlugin.PluginOutputType.RGB_IMAGE) or
                     (self.activePlugin.plugin.outputType == SlideRunnerPlugin.PluginOutputType.RGB_OVERLAY)):
                    olm = self.overlayMap
                    self.overlayExtremes = None
                    if (len(olm.shape)==3) and (olm.shape[2]==3) and np.all(npi.shape[0:2] == olm.shape[0:2]): 
                        if (self.activePlugin.plugin.outputType == SlideRunnerPlugin.PluginOutputType.RGB_IMAGE):
                            for c in range(3):
                                npi[:,:,c] = olm[:,:,c] 
                        else:
                            for c in range(3):
                                npi[:,:,c] = np.uint8(np.clip(np.float32(npi[:,:,c])* (1-self.opacity) + self.opacity * (olm[:,:,c] ),0,255))
                    
        if(self.activePlugin is not None and hasattr(self.activePlugin.instance, 'overlayHeatmap')):
            try:
                heatmap = self.activePlugin.instance.overlayHeatmap(self.overviewimage)
                # Set pixmap of overview image (display overview image)
                self.ui.OverviewLabel.setPixmap(self.vidImageToQImage(heatmap))
            except Exception as e:
                self.popupmessage(f'Plugin returned exception: '+str(e))
        else:
            self.ui.OverviewLabel.setPixmap(self.vidImageToQImage(self.overviewimage))


        # Draw annotations by the plugin
        if (self.activePlugin is not None):
            labels = self.activePlugin.instance.getAnnotationLabels()
            if (len(self.pluginAnnos)>0):
                annoKeys=np.array([x.uid for x in labels])[np.where(self.pluginItemsSelected)[0]].tolist()
                for anno in SlideRunnerPlugin.getVisibleAnnotations(leftUpper=self.region[0], rightLower=self.region[0]+self.region[1], 
                                                                    annotations=self.pluginAnnos, minCoords=self.pluginMinCoords, maxCoords=self.pluginMaxCoords):
                    if (anno.pluginAnnotationLabel is None) or (anno.pluginAnnotationLabel.uid in annoKeys):
                        anno.draw(image=npi, leftUpper=self.region[0], 
                                zoomLevel=self.getZoomValue(), thickness=2, vp=self.currentPluginVP,
                                selected=(self.selectedPluginAnno==anno.uid))

        # Overlay Annotations by the user
        if (self.db.isOpen()):
                self.db.annotateImage(npi, self.region[0], self.region[0]+self.region[1], self.getZoomValue(), self.currentVP, self.selectedAnno)


        # Show the current polygon (if in polygon annotation mode)
        if (self.db.isOpen()) & (self.ui.mode==UIMainMode.MODE_ANNOTATE_POLYGON) & (self.ui.annotationMode>0):
            npi = self.showPolygon(npi, self.ui.annotationsList, color=[0,0,0,255])

        if (self.ui.wandAnnotation.x is not None):
            # Wand annotation is active
            mask = np.zeros( (npi.shape[0]+2, npi.shape[1]+2), dtype=np.uint8)
            seed_point = self.ui.wandAnnotation.seed_point()
            seedPoint_screen = self.slideToScreen(seed_point)
            flags = 4 | 255 << 8   # bit shift
            flags |= cv2.FLOODFILL_FIXED_RANGE | cv2.FLOODFILL_MASK_ONLY
            flood_image = self.rawImage[...,0:3].copy()
            tol = (int(self.ui.wandAnnotation.tolerance),)*3
            try:
                cv2.floodFill(image=flood_image, mask=mask, seedPoint=seedPoint_screen, newVal=(1,1,1),
                        loDiff=tol, upDiff=tol, flags=flags)
                self.ui.wandAnnotation.mask = 255-mask
                polygons = cv2.findContours(self.ui.wandAnnotation.mask, cv2.RETR_LIST,
                                            cv2.CHAIN_APPROX_SIMPLE)
#                polygons = polygons[0]
                polygons = polygons[0]

                lenpoly = [len(x) for x in polygons]
                polygon = polygons[np.argmax(lenpoly)]
                cv2.polylines(npi, [polygon], True, [255,255,255])

                npi[mask[1:-1,1:-1]!=0,0:3] = 255 - npi[mask[1:-1,1:-1]!=0,0:3]
            except Exception as e:
                print('Floodfill did not work!',str(e))

        if (self.ui.wandAnnotation.polygon is not None):
            npi = self.showPolygon(npi, self.ui.wandAnnotation.polygon, color=[0,0,0,255])


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
        
        if (legendMicrons>0):
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

    def toggleOneClass(self, row):
        if (self.db.isOpen()==False):
            return
        if (row>=len(self.modelItems)):
            return
        self.modelItems[row].stateChanged.disconnect(self.selectClasses)
        self.modelItems[row].setChecked(not(self.modelItems[row].checkState()))
    
        self.modelItems[row].stateChanged.connect(self.selectClasses)
       
        self.selectClasses(None)


    def toggleAllClasses(self):
        for item in range(len(self.modelItems)):
            self.modelItems[item].stateChanged.disconnect(self.selectClasses)
            self.modelItems[item].setChecked(not(self.modelItems[item].checkState()))
        
        for item in range(len(self.modelItems)):
            self.modelItems[item].stateChanged.connect(self.selectClasses)
       
        self.selectClasses(None)
 
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

    def selectPluginClasses(self,event):
        """
            Helper function to select classes for enabling/disabling display of plugin annotations

        """

        items=np.zeros(len(self.pluginModelItems))
        for item in range(len(self.pluginModelItems)):
            if (self.pluginModelItems[item].checkState()):
                items[item] = 1

        self.pluginItemsSelected=items
        self.currentPluginVP.activeClasses = items
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
                if (success):
                    self.addAnnotator()
                    self.addCellClass()

        if success:            
            filename = os.path.abspath(filename)
            lastdatabaseslist = self.settings.value('lastDatabases', type=list)
            if filename in (lastdatabaseslist):
                lastdatabaseslist.remove(filename)
            
            if (self.imageOpened):
                self.findSlideUID(self.slide.dimensions)
                self.db.loadIntoMemory(self.slideUID, transformer=self.slide.transformCoordinates)


            lastdatabaseslist.append(filename)
            lastdatabaseslist = lastdatabaseslist[-11:]
            self.settings.setValue('lastDatabases', lastdatabaseslist)
            self.ui.action_CloseDB.setEnabled(True)

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

    def savescreenshot(self):
        filename = QFileDialog.getSaveFileName(filter='PNG Images (*.png)')[0]
        if filename is not None and len(filename)>0:
            cv2.imwrite(filename, cv2.cvtColor(self.displayedImage, cv2.COLOR_BGRA2RGBA))

    def goToCoordinate(self):
        if (self.imageOpened == False):
            return
        retx,rety = getCoordinatesDialog(self)
        self.setCenterTo(retx,rety)
        self.showImage()

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

    def closeDatabase(self):
        self.ui.action_CloseDB.setEnabled(False)
        self.db = Database()
        self.ui.annotatorComboBox.currentIndexChanged.disconnect()
        self.ui.actionAdd_annotator.setEnabled(False)
        self.ui.actionAdd_cell_class.setEnabled(False)
        self.ui.annotatorComboBox.setVisible(False)
        self.ui.databaseLabel.setText('')
        self.showDBstatistics()
        personList=[]
        self.annotatorsModel.setStringList([])
        self.ui.annotatorComboBox.setVisible(False)
        self.ui.annotatorComboBox.setEnabled(False)
        self.ui.inspectorTableView.setVisible(False)
        self.ui.categoryView.setVisible(False)

    def setExactUser(self):
        if (self.db.isOpen() == False):
            self.popupmessage('Please open a local database first.')
            return
        exactp=self.db.getExactPerson()[0]
        allP = self.db.getAllPersons()
        plist = [f'{uid}:{name}' for name, uid in allP]
        pitem, ok = QInputDialog.getItem(self, "Select local EXACT expert", "All experts:", plist, 0, False)
        if ok:
            uid = int(pitem.split(':')[0])
            self.db.setExactPerson(uid)


    def exportToExact(self, allSlides=False, **kwargs):
        if (self.db.isOpen() == False):
            self.popupmessage('Please open a local database first.')
            return
        if (self.db.getExactPerson()[0] == 0):
            self.popupmessage('Please mark a local expert as EXACT user first.')
            return
        if (self.imageOpened == False) and (allSlides==False):
            self.popupmessage('Please open a slide first.')
            return
        try:
            slidesToSync=[]
            # prepare export for all slides
            for uid, filename,exact_id,pathname in self.db.listOfSlidesWithExact():

                    if not allSlides and uid!=self.slideUID:
                        continue
            
                    if (exact_id is not None):
                        reply = QtWidgets.QMessageBox.question(self, 'Question',
                                                    f'{filename} is already linked with an image on exact. Exporting it will create another copy on the server. Really proceed to export?', [QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.Cancel], QtWidgets.QMessageBox.No)

                        if reply == QtWidgets.QMessageBox.No:
                            continue

                        if reply == QtWidgets.QMessageBox.Cancel:
                            break
                    
                    pathname = '.' if pathname is None else str(pathname)
                    if not (os.path.exists(str(pathname)+os.sep+filename)):
                        reply = QtWidgets.QMessageBox.question(self, 'Image not found',
                                                f'{filename} could not be found in {pathname}. Exclude from list and continue with export?', QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

                        if reply == QtWidgets.QMessageBox.No:
                            break

                    slidesToSync.append([uid, filename, pathname])


            exm = ExactManager(self.settings.value('exactUsername', 'Demo'), 
                                self.settings.value('exactPassword', 'demodemo'),
                                self.settings.value('exactHostname', 'https://exact.cs.fau.de'),
                                statusqueue=self.progressBarQueue, loglevel=0)
            imagesets = exm.retrieve_imagesets()
            items = ['%d: ' % iset['id']+iset['name'] for iset in imagesets]
            item, ok = QInputDialog.getItem(self, "Select image set", "Image sets", items, 0, False)

            if not (ok):
                return

            iselect = [k for k,name in enumerate(items) if name==item][0]
            products = ['%d: ' % p['id']+p['name'] for p in imagesets[iselect]['products']]

            pitem, ok = QInputDialog.getItem(self, "Select a product", "Products in image set", products, 0, False)
            if not (ok):
                return

            imageset_id = int(item.split(':')[0])
            product_id = int(pitem.split(':')[0])

            from _thread import start_new_thread
            start_new_thread(self.threadedExportAndSync, (exm,imageset_id,product_id, slidesToSync))          

        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 'Error','Unable to proceed: '+str(e), 
                                          QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)
            raise(e)
            return

    def threadedExportAndSync(self, exm, imageset_id, product_id, slidesToSync:list=[], **kwargs):
        try:
            self.setProgressBar(0)
            newDB = Database().open(self.db.dbfilename)
            for cnt, (slideid, filename, pathname) in enumerate(slidesToSync):
                newDB.loadIntoMemory(slideid)
                slidepathname=pathname+os.sep+filename
                exm.set_progress_properties(denominator=len(slidesToSync), offset=float(cnt)/len(slidesToSync))
                obj = exm.upload_image_to_imageset(imageset_id=imageset_id, filename=slidepathname)

                image_id = obj['files'][0]['id']
                exact_id = f'{image_id}/{product_id}/{imageset_id}'
                newDB.execute(f'UPDATE Slides set exactImageID="{exact_id}" where uid=={slideid}')
                exm.sync(dataset_id=image_id, imageset_id=imageset_id, product_id=product_id, slideuid=slideid, database=newDB)
            self.progressBarQueue.put((SlideRunnerPlugin.StatusInformation.POPUP_MESSAGEBOX,'Slide(s) exported successfully.'))
            self.progressBarQueue.put((SlideRunnerPlugin.StatusInformation.REFRESH_VIEW,None))
            self.progressBarQueue.put((SlideRunnerPlugin.StatusInformation.REFRESH_DATABASE,None))
        except Exception as e:
                self.progressBarQueue.put((SlideRunnerPlugin.StatusInformation.POPUP_MESSAGEBOX,'Unable to proceed: '+str(e)))
    #            raise(e)
                return
        exm.terminate()
        
    def threadedSync(self, exm, allSlides,  **kwargs):
        try:
            for cnt, (slideid, exact_id) in enumerate(allSlides):
                print('Syncing ',slideid,exact_id)
                image_id,product_id,imageset_id = [int(x) for x in exact_id.split('/')]
                newDB = Database().open(self.db.dbfilename)
                newDB.loadIntoMemory(slideid)
                exm.set_progress_properties(denominator=len(allSlides), offset=float(cnt)/len(allSlides))
                exm.sync(dataset_id=image_id, imageset_id=imageset_id, product_id=product_id, slideuid=slideid, database=newDB)
            self.progressBarQueue.put((SlideRunnerPlugin.StatusInformation.REFRESH_VIEW,None))
            self.progressBarQueue.put((SlideRunnerPlugin.StatusInformation.POPUP_MESSAGEBOX,'Sync completed.'))
            self.progressBarQueue.put((SlideRunnerPlugin.StatusInformation.REFRESH_DATABASE,None))

        except Exception as e:
            self.progressBarQueue.put((SlideRunnerPlugin.StatusInformation.POPUP_MESSAGEBOX,'Unable to proceed: '+str(e)))
#            raise(e)
            return

        exm.terminate()
        

    def syncWithExact(self, allSlides:bool=False):
        if (self.db.isOpen() == False):
            self.popupmessage('Please open a local database first.')
            return
        if (self.db.getExactPerson()[0] == 0):
            self.popupmessage('Please mark a local expert as EXACT user first.')
            return
        exact_id=self.db.getExactIDforSlide(self.slideUID)

        if (allSlides==False) and ((exact_id is None) or (len(exact_id) == 0)):
            self.popupmessage('Slide is not linked to any EXACT image.')
            return
                

        try:
            exm = ExactManager(self.settings.value('exactUsername', 'Demo'), 
                                self.settings.value('exactPassword', 'demodemo'),
                                self.settings.value('exactHostname', 'https://exact.cs.fau.de'),
                                statusqueue=self.progressBarQueue, loglevel=0)

            imagesets = exm.retrieve_imagesets()
            imagesets_dict = {iset['id']:iset for iset in imagesets}
            listOfSlides=[]

            print('Current UID is: ',self.slideUID)

            for uid, filename,exact_id,pathname in self.db.listOfSlidesWithExact():
                print('uid:',uid,'filename:',filename)
                if (uid!=self.slideUID) and not allSlides:
                    continue
                
                if (exact_id is None) or (len(exact_id)==0): # not linked to exact
                    continue
                # check if slide still exists on server
                (image_id, product_id, imageset_id) = [int(x) for x in exact_id.split('/')]

                found=False
                if imageset_id in imagesets_dict:
                    productids = [p['id'] for p in imagesets_dict[imageset_id]['products']]
                    if product_id in productids:
                        found=True 
                
                invalids = self.db.execute('SELECT uid FROM Annotations where guid is Null').fetchall()
                for (invalidid,) in invalids:
                    reply = QtWidgets.QMessageBox.question(self, 'Question',
                                                f'Annotation with id {invalidid} in {filename} has invalid UUID. This can be a sign of a corrupt database. Randomly assign new UUID?', QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.Cancel)

                    if reply == QtWidgets.QMessageBox.Cancel:
                        return

                    self.db.execute(f'UPDATE Annotations SET guid=generate_uuid() where uid=={invalidid}')

                if not found:
                    print('Cleaning exact id field of ',uid,exact_id)
                else:
                    listOfSlides.append([uid, exact_id])

            from _thread import start_new_thread
            self.db.commit()
            print('ListOfSlides is:',listOfSlides)
            start_new_thread(self.threadedSync, (exm,listOfSlides))#))          
#             exm.sync(dataset_id=image_id, imageset_id=imageset_id, product_id=product_id, slideuid=self.slideUID, database=self.db)

#             self.showDatabaseUIelements()
#             self.showDBstatistics()
#             self.db.loadIntoMemory(self.slideUID)
#             self.showImage()     
#             self.popupmessage('Sync completed.')
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 'Error','Unable to proceed: '+str(e), 
                                          QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)
            return
        

    def downloadSlideFromExact(self):
        if (self.db.isOpen() == False):
            self.popupmessage('Please open a local database first.')
            return
        if (self.db.getExactPerson()[0] == 0):
            self.popupmessage('Please mark a local expert as EXACT user first.')
            return

        try:
            ELD = ExactDownloadDialog(self.db, self.settings)

            ELD.exec_()


        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 'Error','Unable to proceed: '+str(e), 
                                          QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)
            return

        self.findSlideUID()
        # reload current slide annotations (in case they were deleted)
        if (self.slideUID is not None):
            self.db.loadIntoMemory(self.slideUID, transformer=self.slide.transformCoordinates)
        self.reopenDatabase()

    def linkSlideToExact(self):
        if (self.db.isOpen() == False):
            self.popupmessage('Please open a local database first.')
            return
        if (self.imageOpened == False):
            self.popupmessage('Please open a slide first.')
            return
        try:
            ELD = ExactLinkDialog(self.db, self.settings)

            ELD.exec_()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 'Error','Unable to proceed: '+str(e), 
                                          QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)
            return

        self.findSlideUID()
        # reload current slide annotations (in case they were deleted)
        if (self.slideUID is not None):
            self.db.loadIntoMemory(self.slideUID, transformer=self.slide.transformCoordinates)


    def manageDB(self):
        if (self.db.isOpen() == False):
            self.popupmessage('Please open a local database first.')
            return

        DBM = DatabaseManager(self.db)

        DBM.exec_()
        if (len(DBM.loadSlide)>0):
            self.openSlide(DBM.loadSlide)
        else:
            self.findSlideUID()
            # reload current slide annotations (in case they were deleted)
            if (self.slideUID is not None):
                self.db.loadIntoMemory(self.slideUID, transformer=self.slide.transformCoordinates)

    def showDBstatistics(self):
        """
            Show class-based statistics of current database
        """
        if (self.db.isOpen() == False):
            self.ui.statisticView.setVisible(False)
            return
        table_model = QtGui.QStandardItemModel()
        table_model.setColumnCount(3)
        table_model.setHorizontalHeaderLabels("Name;# on slide;# total".split(";"))

        statistics = self.db.countEntryPerClass(self.slideUID)

        names = list(statistics.keys())
        for idx in range(len(names)):
            txt = QStandardItem(names[idx])
            col1 = QStandardItem('%d' % statistics[names[idx]]['count_slide'])
            col2 = QStandardItem('%d' % statistics[names[idx]]['count_total'])
            table_model.appendRow([txt,col1,col2])

        self.ui.statisticView.setModel(table_model)
        self.ui.statisticView.setVisible(True)
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

    def deleteCurrentSelection(self):
        if (self.selectedAnno is not None):
            self.removeAnnotation(self.selectedAnno)

    def showDatabaseUIelements(self):
        """
            Show and update UI controls related to the database
        """
        if (self.db.isOpen()):
            self.ui.actionAdd_annotator.setEnabled(True)
            self.ui.actionAdd_cell_class.setEnabled(True)
            self.ui.annotatorComboBox.setVisible(True)

            self.showDBentryCount()
            persons = self.db.getAllPersons()
            personList=[]
            for person in persons:
                personList.append(person[0])
            self.annotatorsModel.setStringList(personList)
            self.ui.annotatorComboBox.setVisible(True)
            self.ui.annotatorComboBox.setEnabled(True)
            self.ui.annotatorComboBox.currentIndexChanged.connect(self.changeAnnotator)

            self.db.updateViewingProfile(self.currentVP)
            self.db.updateViewingProfile(self.currentPluginVP)

        if (self.db.isOpen() or (self.activePlugin is not None)):
            self.ui.inspectorTableView.setVisible(True)
            self.ui.categoryView.setVisible(True)


            tableRows = dict()
            model = QStandardItemModel()
            
            self.modelItems = list()
            self.pluginModelItems = list()
            classes =   self.db.getAllClasses() if self.db.isOpen() else []
            self.classButtons = list()
            if (self.activePlugin is None):
                self.ui.categoryView.setRowCount(len(classes)+1)
            else:
                self.ui.categoryView.setRowCount(len(classes)+1+len(self.activePlugin.instance.getAnnotationLabels()))

            self.ui.categoryView.setColumnCount(4)
            item = QTableWidgetItem('unknown')
            pixmap = QPixmap(10,10)
            pixmap.fill(QColor.fromRgb(self.get_color(0)[0],self.get_color(0)[1],self.get_color(0)[2]))
            itemcol = QTableWidgetItem('')
            itemcol.setBackground(QColor.fromRgb(self.get_color(0)[0],self.get_color(0)[1],self.get_color(0)[2]))
            checkbx = QCheckBox()
            checkbx.setChecked(True)
            tableRows[0] = ClassRowItem(ClassRowItemId.ITEM_DATABASE, 0, uid=0, color='#000000')
            checkbx.stateChanged.connect(self.selectClasses)
            self.ui.categoryView.setItem(0,2, item)
            self.ui.categoryView.setItem(0,1, itemcol)
            self.ui.categoryView.setCellWidget(0,0, checkbx)
            if (self.db.isOpen()):
                self.modelItems.append(checkbx)

            # For all classes in the database, make an entry in the table with
            # a class button and respective correct color
            
            for clsid in range(len(classes)):
                clsname = classes[clsid]
                item = QTableWidgetItem(clsname[0])
                item.setFlags(Qt.ItemIsSelectable)
                pixmap = QPixmap(10,10)
                pixmap.fill(QColor.fromRgb(*hex_to_rgb(clsname[2])))
                btn = QPushButton('')

                btn.clicked.connect(partial(self.clickAnnoclass, clsid+1))
                self.classButtons.append(btn)
                itemcol = QTableWidgetItem('')
                itemcol.setFlags(Qt.NoItemFlags)
                checkbx = QCheckBox()
                checkbx.setChecked(True)
                itemcol.setBackground(QColor.fromRgb(*hex_to_rgb(clsname[2])))
                self.modelItems.append(checkbx)
                self.ui.categoryView.setItem(clsid+1,2, item)
                self.ui.categoryView.setItem(clsid+1,1, itemcol)
                self.ui.categoryView.setCellWidget(clsid+1,0, checkbx)
                self.ui.categoryView.setCellWidget(clsid+1,3, btn)
                checkbx.stateChanged.connect(self.selectClasses)

                tableRows[clsid+1] = ClassRowItem(ClassRowItemId.ITEM_DATABASE, clsid, clsname[1], clsname[2])
            
            rowIdx =   len(self.db.getAllClasses())+1 if self.db.isOpen() else 0
            self.itemsSelected = np.ones(rowIdx+1)

            if (self.activePlugin is not None):
                annoLabels = self.activePlugin.instance.getAnnotationLabels()

                for label in annoLabels:
                    item = QTableWidgetItem('plugin:'+label.name)
                    pixmap = QPixmap(10,10)
                    pixmap.fill(QColor.fromRgb(label.color[0], label.color[1], label.color[2]))
                    
                    itemcol = QTableWidgetItem('')
                    checkbx = QCheckBox()
                    checkbx.setChecked(True)
                    itemcol.setBackground(QColor.fromRgb(label.color[0], label.color[1], label.color[2]))
                    self.pluginModelItems.append(checkbx)
                    self.ui.categoryView.setItem(rowIdx,2, item)
                    self.ui.categoryView.setItem(rowIdx,1, itemcol)
                    self.ui.categoryView.setCellWidget(rowIdx,0, checkbx)
                    checkbx.stateChanged.connect(self.selectPluginClasses)

                    tableRows[rowIdx] = ClassRowItem(ClassRowItemId.ITEM_PLUGIN, label,color=label.color)

                    rowIdx+=1

                    

                self.pluginItemsSelected = np.ones(len(annoLabels))

            self.classList = tableRows

            model.itemChanged.connect(self.selectClasses)

            self.currentVP.activeClasses = self.itemsSelected
            if (self.activePlugin is not None):
                self.currentPluginVP.activeClasses = self.pluginItemsSelected
            self.ui.categoryView.verticalHeader().setVisible(False)
            vheader = self.ui.categoryView.verticalHeader()
            vheader.setDefaultSectionSize(vheader.fontMetrics().height()+2)
            self.ui.categoryView.horizontalHeader().setVisible(False)
            self.ui.categoryView.setColumnWidth(0, 20)
            self.ui.categoryView.setColumnWidth(1, 20)
            self.ui.categoryView.setColumnWidth(2, 120)
            self.ui.categoryView.setColumnWidth(3, 50)
            self.ui.categoryView.setShowGrid(False)

            if (self.imageOpened) and (self.db.isOpen()):
                self.findSlideUID(self.slide.dimensions)
            elif (self.db.isOpen()):
                self.findSlideUID()

            self.ui.annotatorComboBox.setModel(self.annotatorsModel)

            #if (self.imageOpened):
            #    self.showImage()


    def toggleAnnoclass(self, id):
        if (id<len(self.classList)):
            if (self.pluginModelItems[item].checkState()):
                self.pluginModelItems[item].setChecked(False)       
            else: 
                self.pluginModelItems[item].setChecked(True)       

    def sliderChanged(self):
        """
            Callback function for when a slider was changed.
        """
        print('Slider changed')
        self.setZoomValue(self.sliderToZoomValue())
        self.showImage()
        self.updateScrollbars()

    def nextFrame(self):
        self.ui.frameSlider.setValue(self.ui.frameSlider.getValue()+1)
        self.zPosition = self.ui.frameSlider.getValue()
        self.db.loadIntoMemory(self.slideUID, transformer=self.slide.transformCoordinates, zLevel=self.zPosition)
        self.showImage()

    def previousFrame(self):
        self.ui.frameSlider.setValue(self.ui.frameSlider.getValue()-1)
        self.zPosition = self.ui.frameSlider.getValue()
        self.db.loadIntoMemory(self.slideUID, transformer=self.slide.transformCoordinates, zLevel=self.zPosition)
        self.showImage()


    def frameChanged(self):
        self.zPosition = self.ui.frameSlider.getValue()
        if (self.db.isOpen()):
            self.findSlideUID(self.slide.dimensions)
            t = time.time()
            self.db.loadIntoMemory(self.slideUID, transformer=self.slide.transformCoordinates, zLevel=self.zPosition)
        self.showImage()

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

        self.addAnnotator()
        self.addCellClass()

        
        lastdatabaseslist = self.settings.value('lastDatabases', type=list)
        if dbfilename in (lastdatabaseslist):
            lastdatabaseslist.remove(dbfilename)
        lastdatabaseslist.append(dbfilename)
        lastdatabaseslist = lastdatabaseslist[-11:]
        self.settings.setValue('lastDatabases', lastdatabaseslist)

        self.showDatabaseUIelements()


    def openSlideDialog(self):
        """
            Callback function to select a slide
        """
        filename = QFileDialog.getOpenFileName(filter='WSI files (*.svs *.tif *.png *.bif *.svslide *.mrxs *.scn *.vms *.vmu *.ndpi *.tiff *.bmp *.dcm);;Aperio SVS format (*.svs);;DICOM format (*.dcm);;CellVizio MKT format (*.mkt);;All files (*.*)')[0]
        if (len(filename)==0):
            return ''
        self.openSlide(filename)
        return filename
    
    def initZoomSlider(self):
        """
            Initialize the scrollbar slider.
        """
        self.ui.zoomSlider.valueChanged.connect(self.sliderChanged)

    def setMPP(self):
        mppval, ok = QInputDialog.getDouble(self, "Value for 'microns per pixel'",
                                          "Image MPP:", value=self.slideMicronsPerPixel, decimals=3 )
        if (ok):
            self.slideMicronsPerPixel = mppval if mppval>0 else 1e-6

    def saveDBto(self):
        filename = QFileDialog.getSaveFileName(filter='*.sqlite')[0]
        if filename is not None and len(filename)>0:
            self.db.saveTo(filename)

    def settingsDialog(self):
        settingsDialog(self.settings)
        self.refreshMenu()
        self.currentVP.spotCircleRadius = self.settings.value('SpotCircleRadius')
        self.showImage()
    
    def updateOverview(self):
        self.thumbnail = thumbnail.thumbnail(self.slide)

        # Read overview thumbnail from slide
        if 32 in self.slide.level_downsamples:
            level_overview = np.where(np.array(self.slide.level_downsamples)==32)[0][0] # pick overview at 32x
        else:
            level_overview = self.slide.level_count-1
        overview = self.slide.read_region(location=(0,0), level=level_overview, size=self.slide.level_dimensions[level_overview], zLevel=self.zPosition)
        self.slideOverview = np.asarray(overview)
        overview = cv2.cvtColor(np.asarray(overview), cv2.COLOR_BGRA2RGB)
        self.overview = overview



    def openSlide(self, filename):
        """
            Helper function to open a whole slide image
        """
        if not (os.path.exists(filename)):
            reply = QtWidgets.QMessageBox.information(self, 'Error',
                           'File not found: %s' % filename, QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)
            return

        try:
            print('Opening ',filename)
            self.slide = RotatableOpenSlide(filename, rotate=self.rotateImage)
        except Exception as e:
            self.show_exception("Unable to open"+filename, *sys.exc_info())
            return

        # Clear cache
        self.cachedLocation = None
        self.cachedLevel = None

        self.ui.frameSlider.valueChanged.disconnect()
        self.ui.frameSlider.setNumberOfFrames(self.slide.numberOfFrames)
        self.ui.frameSlider.setFPS(self.slide.fps)
        self.ui.frameSlider.setValue(0)
        self.ui.frameSlider.valueChanged.connect(self.frameChanged)

        if (openslide.PROPERTY_NAME_OBJECTIVE_POWER in self.slide.properties):
            self.slideMagnification = self.slide.properties[openslide.PROPERTY_NAME_OBJECTIVE_POWER]
        else:
            self.slideMagnification = 1

        if (openslide.PROPERTY_NAME_MPP_X in self.slide.properties):
            self.slideMicronsPerPixel = self.slide.properties[openslide.PROPERTY_NAME_MPP_X]
        elif (hasattr(self.slide,'mpp_x')):
            self.slideMicronsPerPixel = self.slide.mpp_x
        else:
            self.slideMicronsPerPixel = 1E-6
        self.slidename = os.path.basename(filename)
        self.zPosition=0

        # unhide label and show filename
        self.ui.filenameLabel.setText(self.slidename)
        self.ui.filenameLabel.setHidden(False)
        self.slidepathname = filename
        self.imageOpened=True
        self.ui.statusbar.showMessage(filename+': '+str(self.slide.dimensions))

        if (self.db.isOpen()):
            self.findSlideUID(self.slide.dimensions)
            t = time.time()
            self.db.loadIntoMemory(self.slideUID, transformer=self.slide.transformCoordinates)

            self.db.setPathForSlide(self.slideUID, self.slidepathname)
        self.relativeCoords = np.asarray([0,0], np.float32)
        self.lastScreeningLeftUpper = np.zeros(2)
        self.screeningHistory = list()
        self.screeningIndex = 0

        self.updateOverview()

        # Initialize a new screening map
        self.screeningMap = screening.screeningMap(self.overview, self.mainImageSize, self.slide.level_dimensions, self.thumbnail.size, self.settings.value('GuidedScreeningThreshold'))

        self.initZoomSlider()
        self.imageCenter=[0,0]
        self.setZoomValue(self.getMaxZoom())

        self.showAnnotationsInOverview()
        self.showImage()

        self.updateScrollbars()
        self.screeningMode=False
        self.ui.iconScreening.setChecked(False)
        self.ui.iconNextScreen.setEnabled(self.screeningMode)
        self.ui.iconPreviousScreen.setEnabled(False)
        self.ui.iconNextScreen.setEnabled(False)

        self.showDBstatistics()

        filename = os.path.abspath(filename)
        lastslideslist = self.settings.value('LastSlides', type=list)
        if filename in (lastslideslist):
            lastslideslist.remove(filename)

        lastslideslist.append(filename)
        lastslideslist = lastslideslist[-11:]
        self.settings.setValue('LastSlides', lastslideslist)
        menu.updateOpenRecentSlide(self)


import sys

def main(slideReaderThread,app,splash,version,pluginList):
    style.setStyle(app)    

    
    myapp = SlideRunnerUI(slideReaderThread=slideReaderThread, app=app, version=version, pluginList=pluginList)

    myapp.show()
    myapp.raise_()
    sys.excepthook = myapp.exceptionHook
    threading.excepthook = myapp.exceptionHook_threading
    splash.finish(myapp)

    if (myapp.activePlugin is not None):
        myapp.activePlugin.inQueue.put(None)
        myapp.activePlugin.inQueue.put(SlideRunnerPlugin.jobToQueueTuple(description=SlideRunnerPlugin.JobDescription.QUIT_PLUGIN_THREAD))
    app.exec_()
