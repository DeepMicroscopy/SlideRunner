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

      def __init__(self, x1, y1, x2, y2):
            self.x1 = x1
            self.y1 = y1
            self.x2 = x2
            self.y2 = y2
      
      def draw(self, image: np.ndarray, leftUpper: tuple, zoomLevel: float, thickness: int, color:tuple):
            xpos1=max(0,int((self.x1-leftUpper[0])/zoomLevel))
            ypos1=max(0,int((self.y1-leftUpper[1])/zoomLevel))
            xpos2=min(image.shape[1],int((self.x2-leftUpper[0])/zoomLevel))
            ypos2=min(image.shape[0],int((self.y2-leftUpper[1])/zoomLevel))
            image = cv2.rectangle(image, thickness=thickness, pt1=(xpos1,ypos1), pt2=(xpos2,ypos2),color=color, lineType=cv2.LINE_AA)

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
      configuration = list()
      
      def __init__(self, queueTuple):
            self.jobDescription, self.currentImage, self.slideFilename, self.coordinates, self.configuration, self.annotations = queueTuple

def jobToQueueTuple(description=JobDescription.PROCESS, currentImage=None, coordinates=None, configuration=list(), slideFilename=None, annotations=None):
      return (description, currentImage, slideFilename, coordinates, configuration, annotations)


class PluginConfigurationEntry():
      uid = 0
      name = ''
      minValue = 0
      initValue = 0.5
      maxValue = 1
      def __init__(self,uid:int=0,name:str='' ,initValue:float=0.5, minValue:float=0.0, maxValue:float=1.0):
            self.uid=uid
            self.name=name
            self.minValue=minValue
            self.maxValue=maxValue
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
      
      def __str__(self):
            return self.shortName
      def setProgressBar(self, value : int):
            self.statusQueue.put((StatusInformation.PROGRESSBAR,value))

      def setMessage(self, msg:str):
            self.statusQueue.put((StatusInformation.TEXT,msg))
      
      def updateAnnotations(self):
            self.statusQueue.put((StatusInformation.ANNOTATIONS, self.getAnnotations()))

      def getAnnotations(self):
            print('Sent empty annotation list.')
            return list()            