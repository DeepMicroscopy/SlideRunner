"""
      Definition of the class SlideRunnerPlugin, used to derive plugins
"""
from queue import Queue
import numpy as np 
import cv2
from typing import List

class StatusInformation(enumerate):
      PROGRESSBAR = 0
      TEXT = 1
      ANNOTATIONS = 2
      SET_CENTER = 3
      SET_ZOOM = 4
      POPUP_MESSAGEBOX = 5
      UPDATE_CONFIG = 6
      UPDATE_LABELS = 7

class AnnotationUpdatePolicy(enumerate):
      UPDATE_ON_SCROLL_CHANGE = 0,
      UPDATE_ON_SLIDE_CHANGE = 1

class PluginTypes(enumerate):
      IMAGE_PLUGIN = 0
      WHOLESLIDE_PLUGIN = 1

class PluginOutputType(enumerate):
      BINARY_MASK = 0
      RGB_IMAGE = 1
      NO_OVERLAY = 2

class JobDescription(enumerate):
      PROCESS = 0
      QUIT_PLUGIN_THREAD = 99


class pluginJob():
      jobDescription = None
      slideFilename = None
      coordinates = None
      currentImage = None
      annotations = None
      procId = None
      openedDatabase = None
      configuration = list()
      
      actionUID = None
      
      def __init__(self, queueTuple):
            self.jobDescription, self.currentImage, self.slideFilename, self.coordinates, self.configuration, self.annotations, self.procId, self.trigger, self.actionUID, self.openedDatabase = queueTuple

      def __str__(self):
            return """<SlideRunner.general.SlideRunnerPlugin.pluginJob object>
            slideFilename = %s
            coordinates = %s
            actionUID = %s
            trigger = %s
            annotations = %s""" % (self.slideFilename, str(self.coordinates),str(self.actionUID), str(self.trigger), str(self.annotations))
      

def jobToQueueTuple(description=JobDescription.PROCESS, currentImage=None, coordinates=None, configuration=list(), slideFilename=None, annotations=None, procId=None, trigger=None, actionUID=None, openedDatabase=None):
      return (description, currentImage, slideFilename, coordinates, configuration, annotations, procId, trigger, actionUID, openedDatabase)

class PluginConfigurationType(enumerate):
      SLIDER_WITH_FLOAT_VALUE = 0
      PUSHBUTTON = 1
      COMBOBOX = 2
      ANNOTATIONACTION = 3
      FILEPICKER = 4

class FilePickerDialogType(enumerate):
      OPEN_FILE = 0
      SAVE_FILE = 1
      OPEN_DIRECTORY = 2

class PluginAnnotationLabel():

      def __set_color(self, color:tuple):
            if len(color) != 4:
                  raise ValueError('Color needs to be a tuple of four integer values.')
            elif all([isinstance(x,int) for x in color]):
                  self.__color = color
            elif all([isinstance(x,float) for x in color]):
                  self.__color = [int(x*255) for x in color]
            else:
                  raise ValueError('Color needs to be a tuple of four integer values (<255) or three float values (=<1)')
      
      def __get_color(self):
            return self.__color

      color = property(__get_color, __set_color)
                  
      def __init__(self, uid: int, name: str, color: tuple):
            self.uid = uid
            self.name = name
            self.color = color
      
      def __str__(self):
            return self.name



class PluginConfigUpdateEntry():
      def __init__(self, configType: PluginConfigurationType, uid:int, value):
            self.configType = configType
            self.uid = uid
            self.value = value
      
      def getType(self) -> PluginConfigurationType:
            return self.configType

class PluginConfigUpdateFloatSlider(PluginConfigUpdateEntry):
      def __init__(self, uid:int, value):
            super.__init(configType=PluginConfigurationType.SLIDER_WITH_FLOAT_VALUE, uid=uid, value=value)

class PluginConfigUpdateComboBox(PluginConfigUpdateEntry):
      def __init__(self, uid:int, value):
            super.__init(configType=PluginConfigurationType.COMBOBOX, uid=uid, value=value)

class PluginConfigUpdate():
      def __init__(self, update:List[PluginConfigUpdateEntry]):
            self.updateList = update

class PluginConfigurationEntry():
      def __init__(self,uid:int=0,name:str='' ,initValue:float=0.5, minValue:float=0.0, maxValue:float=1.0, ctype=PluginConfigurationType.SLIDER_WITH_FLOAT_VALUE):
            self.uid=uid
            self.name=name
            self.minValue=minValue
            self.maxValue=maxValue
            self.type=ctype
            self.initValue = initValue

class FilePickerConfigurationEntry(PluginConfigurationEntry):
      def __init__(self,uid:int=0,name:str='' ,mask='*.jpg', title='Choose a file', dialogType:FilePickerDialogType=FilePickerDialogType.OPEN_FILE ):
            self.uid=uid
            self.name=name
            self.mask = mask
            self.dialogType=dialogType
            self.title=title
            self.type=PluginConfigurationType.FILEPICKER



class SliderPluginConfigurationEntry(PluginConfigurationEntry):
      def __init__(self,uid:int=0,name:str='' ,initValue:float=0.5, minValue:float=0.0, maxValue:float=1.0):
            self.uid=uid
            self.name=name
            self.minValue=minValue
            self.maxValue=maxValue
            self.type=PluginConfigurationType.SLIDER_WITH_FLOAT_VALUE
            self.initValue = initValue


class PushbuttonPluginConfigurationEntry(PluginConfigurationEntry):
      def __init__(self,uid:int=0,name:str='' ):
            self.uid=uid
            self.name=name
            self.type=PluginConfigurationType.PUSHBUTTON

class PluginActionEntry(PluginConfigurationEntry):
      def __init__(self,uid:int=0,name:str='' ):
            self.uid=uid
            self.name=name
            self.type=PluginConfigurationType.ANNOTATIONACTION


class ComboboxPluginConfigurationEntry(PluginConfigurationEntry):
      def __init__(self,uid:int,name:str, options:list ):
            self.uid=uid
            self.name=name
            self.type=PluginConfigurationType.COMBOBOX
            self.options = options



class SlideRunnerPlugin:
      description = 'This is a sample plugin'
      shortName = 'SamplePlugin'
      enabled = False
      inQueue = None
      version = '0.0'
      outQueue = None
      updateTimer = 5
      initialOpacity = 0.5
      statusQueue = None
      outputType = PluginOutputType.BINARY_MASK
      pluginType = PluginTypes.IMAGE_PLUGIN
      configurationList = list()
      
      def __init__(self,statusQueue:Queue):
            self.description = 'This is a sample plugin'
            self.statusQueue = statusQueue
      
      def getAnnotationUpdatePolicy():
            return AnnotationUpdatePolicy.UPDATE_ON_SLIDE_CHANGE

      def __str__(self):
            return self.shortName

      # Set the progress bar in SlideRunner. 
      # value: between 0 and 100, -1 for disable
      def setProgressBar(self, value : int):
            self.statusQueue.put((StatusInformation.PROGRESSBAR,value))

      def setMessage(self, msg:str):
            self.statusQueue.put((StatusInformation.TEXT,msg))

      def setCenter(self, tup:str):
            self.statusQueue.put((StatusInformation.SET_CENTER,tup))

      def setZoomLevel(self, zoom:float):
            self.statusQueue.put((StatusInformation.SET_ZOOM,zoom))

      def sendAnnotationLabelUpdate(self):
            self.statusQueue.put((StatusInformation.UPDATE_LABELS, None))

      # Show a simple message box with a string message      
      def showMessageBox(self, msg:str):
            self.statusQueue.put((StatusInformation.POPUP_MESSAGEBOX,msg))

      # Update configuration from plugin (e.g. as reaction to slide change, etc..)
      # example:
      # self.updateConfiguration(PluginConfigUpdate([PluginConfigUpdateFloatSlider(uid=0, value=0.5),]))
      def updateConfiguration(self, update: PluginConfigUpdate):
            self.statusQueue.put((StatusInformation.UPDATE_CONFIG,update))

      # Return an image to SlideRunner UI
      def returnImage(self, img : np.ndarray, procId = None):
            self.outQueue.put((img, procId))

      def exceptionHandlerOnExit(self):
            return

      def updateAnnotations(self):
            self.statusQueue.put((StatusInformation.ANNOTATIONS, self.getAnnotations()))

      def findClickAnnotation(self, clickPosition, pluginVP):
            labels = self.getAnnotationLabels()
            annoKeys=np.array([x.uid for x in labels])[np.where(pluginVP.activeClasses)[0]].tolist()
            for idx,anno in enumerate(self.getAnnotations()):
                  if (anno.pluginAnnotationLabel is None) or (anno.pluginAnnotationLabel.uid in annoKeys):
                        if (anno.positionInAnnotation(clickPosition )):
                              return anno
            return None

      def getAnnotationsOfLabel(self, annoLabel:PluginAnnotationLabel):
            labels = self.getAnnotationLabels()
            annoList=list()
            for idx,anno in enumerate(self.getAnnotations()):
                  if (anno.pluginAnnotationLabel is not None) and (anno.pluginAnnotationLabel.uid == annoLabel.uid):
                        annoList.append(anno)
            
            return annoList


      def getAnnotationLabels(self):
            # sending default annotation labels
            return [PluginAnnotationLabel(0,'annotation', [0,0,0,0])]

      def getAnnotations(self):
            print('Sent empty annotation list.')
            return list()


def generateMinMaxCoordsList( annoList) -> (np.ndarray, np.ndarray):
      # MinMaxCoords lists shows extreme coordinates from object, to decide if an object shall be shown
      minCoords = np.zeros(shape=(len(annoList),2))
      maxCoords = np.zeros(shape=(len(annoList),2))
      for annokey in range(len(annoList)):
            annotation = annoList[annokey]
            minCoords[annokey] = np.asarray(annotation.minCoordinates().tolist())
            maxCoords[annokey] = np.asarray(annotation.maxCoordinates().tolist())

      return minCoords, maxCoords

def getVisibleAnnotations(leftUpper:list, rightLower:list, annotations:np.ndarray, minCoords:np.ndarray, maxCoords:np.ndarray) -> list:
      potentiallyVisible =  ( (maxCoords[:,0] > leftUpper[0]) & (minCoords[:,0] < rightLower[0]) & 
                              (maxCoords[:,1] > leftUpper[1]) & (minCoords[:,1] < rightLower[1]) )
      return np.array(annotations)[np.where(potentiallyVisible)[0]].tolist()

