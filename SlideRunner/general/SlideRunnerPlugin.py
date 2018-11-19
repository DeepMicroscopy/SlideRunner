"""
      Definition of the class SlideRunnerPlugin, used to derive plugins
"""
from queue import Queue
import numpy as np 
import cv2

class StatusInformation(enumerate):
      PROGRESSBAR = 0
      TEXT = 1
      ANNOTATIONS = 2
      SET_CENTER = 3
      SET_ZOOM = 4

class AnnotationUpdatePolicy(enumerate):
      UPDATE_ON_SCROLL_CHANGE = 0,
      UPDATE_ON_SLIDE_CHANGE = 1

class PluginTypes(enumerate):
      IMAGE_PLUGIN = 0
      WHOLESLIDE_PLUGIN = 1

class PluginOutputType(enumerate):
      BINARY_MASK = 0
      RGB_IMAGE = 1

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

      def __init__(self, x1, y1, r):
            self.x1 = x1
            self.y1 = y1
            self.r = r
      
      def draw(self, image: np.ndarray, leftUpper: tuple, zoomLevel: float, thickness: int, color:tuple):
            xpos1=((self.x1-leftUpper[0])/zoomLevel)
            ypos1=((self.y1-leftUpper[1])/zoomLevel)
            radius = self.r
            if (radius>=0):
                  image = cv2.circle(image, thickness=thickness, center=(xpos1,ypos1), radius=radius,color=color, lineType=cv2.LINE_AA)

class pluginJob():
      jobDescription = None
      slideFilename = None
      coordinates = None
      currentImage = None
      annotations = None
      procId = None
      configuration = list()
      actionUID = None
      
      def __init__(self, queueTuple):
            self.jobDescription, self.currentImage, self.slideFilename, self.coordinates, self.configuration, self.annotations, self.procId, self.trigger, self.actionUID = queueTuple

      def __str__(self):
            return """<SlideRunner.general.SlideRunnerPlugin.pluginJob object>
            slideFilename = %s
            coordinates = %s
            actionUID = %s
            annotations = %s""" % (self.slideFilename, str(self.coordinates),str(self.actionUID), str(self.annotations))
                   
      

def jobToQueueTuple(description=JobDescription.PROCESS, currentImage=None, coordinates=None, configuration=list(), slideFilename=None, annotations=None, procId=None, trigger=None, actionUID=None):
      return (description, currentImage, slideFilename, coordinates, configuration, annotations, procId, trigger, actionUID)

class PluginConfigurationType(enumerate):
      SLIDER_WITH_FLOAT_VALUE = 0
      PUSHBUTTON = 1
      ANNOTATIONACTION = 2

class PluginConfigurationEntry():
      uid = 0
      name = ''
      minValue = 0
      initValue = 0.5
      maxValue = 1
      def __init__(self,uid:int=0,name:str='' ,initValue:float=0.5, minValue:float=0.0, maxValue:float=1.0, ctype=PluginConfigurationType.SLIDER_WITH_FLOAT_VALUE):
            self.uid=uid
            self.name=name
            self.minValue=minValue
            self.maxValue=maxValue
            self.type=ctype
            self.initValue = initValue



class SlideRunnerPlugin:
      description = 'This is a sample plugin'
      shortName = 'SamplePlugin'
      enabled = False
      inQueue = None
      version = '0.0'
      outQueue = None
      updateTimer = 5
      initialOpacity = 0.3
      statusQueue = None
      configurationList = list()
      outputType = PluginOutputType.BINARY_MASK
      pluginType = PluginTypes.IMAGE_PLUGIN
      
      def __init__(self,statusQueue:Queue):
            self.description = 'This is a sample plugin'
            self.statusQueue = statusQueue
      
      def getAnnotationUpdatePolicy():
            return AnnotationUpdatePolicy.UPDATE_ON_SLIDE_CHANGE

      def __str__(self):
            return self.shortName

      def setProgressBar(self, value : int):
            self.statusQueue.put((StatusInformation.PROGRESSBAR,value))

      def setMessage(self, msg:str):
            self.statusQueue.put((StatusInformation.TEXT,msg))

      def setCenter(self, tup:str):
            self.statusQueue.put((StatusInformation.SET_CENTER,tup))

      def setZoomLevel(self, zoom:float):
            self.statusQueue.put((StatusInformation.SET_ZOOM,zoom))

      def returnImage(self, img : np.ndarray, procId = None):
            self.outQueue.put((img, procId))

      def updateAnnotations(self):
            self.statusQueue.put((StatusInformation.ANNOTATIONS, self.getAnnotations()))

      def getAnnotations(self):
            print('Sent empty annotation list.')
            return list()