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

class annotation():
      def draw(self, image: np.ndarray, leftUpper: tuple, zoomLevel: float, thickness: int, color:tuple):
            return

class rectangularAnnotation(annotation):

      def __init__(self, x1, y1, x2, y2, text:str=''):
            self.x1 = x1
            self.y1 = y1
            self.x2 = x2
            self.y2 = y2
            self.text = text
      
      def draw(self, image: np.ndarray, leftUpper: tuple, zoomLevel: float, thickness: int, color:tuple):
            xpos1=max(0,int((self.x1-leftUpper[0])/zoomLevel))
            ypos1=max(0,int((self.y1-leftUpper[1])/zoomLevel))
            xpos2=min(image.shape[1],int((self.x2-leftUpper[0])/zoomLevel))
            ypos2=min(image.shape[0],int((self.y2-leftUpper[1])/zoomLevel))
            image = cv2.rectangle(image, thickness=thickness, pt1=(xpos1,ypos1), pt2=(xpos2,ypos2),color=color, lineType=cv2.LINE_AA)
            if (len(self.text)>0):
                  cv2.putText(image, self.text, (xpos1+3, ypos2+10), cv2.FONT_HERSHEY_PLAIN , 0.7,(0,0,0),1,cv2.LINE_AA)

      
      def __str__(self):
            return ('Rectangular annotation object: X1:%d, X2:%d, Y1:%d, Y2: %d ' % (self.x1,self.y1,self.x2,self.y2))

class circleAnnotation(annotation):

      def __init__(self, x1, y1, r, text:str=''):
            self.x1 = int(x1)
            self.y1 = int(y1)
            self.r = int(r)
            self.text = text
      
      def __str__(self):
            return 'SlideRunner.circleAnnotation @ (%s,%s,%s): %s' % (str(self.x1),str(self.y1),str(self.r),str(self.text))
      
      def draw(self, image: np.ndarray, leftUpper: tuple, zoomLevel: float, thickness: int, color:tuple):
            xpos1=int((self.x1-leftUpper[0])/zoomLevel)
            ypos1=int((self.y1-leftUpper[1])/zoomLevel)
            radius = int(self.r/zoomLevel)
            if (radius>=0):
                  image = cv2.circle(image, thickness=thickness, center=(xpos1,ypos1), radius=radius,color=color, lineType=cv2.LINE_AA)
            if (len(self.text)>0) and (radius>5): # only show text if available and annotation not too small
                  font=cv2.FONT_HERSHEY_PLAIN 
                  fontsize=1.0
                  textsize = cv2.getTextSize(self.text, font, fontsize, 2)[0]
                  xcoord = int(xpos1-textsize[0]*0.5)
                  ycoord = int(ypos1+radius)
                  cv2.rectangle(image, pt1=(xcoord-2, ycoord-2), pt2=(xcoord+textsize[0]+2, ycoord+textsize[1]+2), color=[0,0,0], thickness=-1)
                  cv2.putText(image, self.text, (int(xcoord), int(ycoord+textsize[1])), font, fontsize,color=[255,255,255,255],thickness=2,lineType=cv2.LINE_AA)

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

      def getAnnotations(self):
            print('Sent empty annotation list.')
            return list()