"""
      Definition of the class SlideRunnerPlugin, used to derive plugins
"""
from queue import Queue
import numpy as np 
import cv2
from typing import List, Tuple
from SlideRunner_dataAccess.annotations import PluginAnnotationLabel



class StatusInformation(enumerate):
      PROGRESSBAR = 0
      TEXT = 1
      ANNOTATIONS = 2
      SET_CENTER = 3
      SET_ZOOM = 4
      POPUP_MESSAGEBOX = 5
      UPDATE_CONFIG = 6
      UPDATE_LABELS = 7
      UPDATE_INFORMATION = 8
      REFRESH_VIEW = 9
      REFRESH_DATABASE = 10
      SHOW_EXCEPTION = 11

class AnnotationUpdatePolicy(enumerate):
      UPDATE_ON_SCROLL_CHANGE = 0,
      UPDATE_ON_SLIDE_CHANGE = 1

class PluginTypes(enumerate):
      IMAGE_PLUGIN = 0
      WHOLESLIDE_PLUGIN = 1
      NONE_PLUGIN = 2

class PluginOutputType(enumerate):
      HEATMAP = 0
      RGB_IMAGE = 1
      RGB_OVERLAY = 2
      NO_OVERLAY = 3

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
      TABLE = 5

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
      def __init__(self,uid:int,name:str, options:list, selected_value:int=0 ):
            self.uid=uid
            self.name=name
            self.type=PluginConfigurationType.COMBOBOX
            self.options = options
            self.selected_value = selected_value


class TablePluginConfigurationEntry(PluginConfigurationEntry):
      def __init__(self, uid: int, name: str):
            self.uid = uid
            self.name = name
            self.type = PluginConfigurationType.TABLE


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
      outputType = PluginOutputType.HEATMAP
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
            self.statusQueue.put((self.shortName, StatusInformation.PROGRESSBAR,value))

      def setMessage(self, msg:str):
            self.statusQueue.put((self.shortName, StatusInformation.TEXT,msg))

      def setCenter(self, tup:str):
            self.statusQueue.put((self.shortName, StatusInformation.SET_CENTER,tup))

      def setZoomLevel(self, zoom:float):
            self.statusQueue.put((self.shortName, StatusInformation.SET_ZOOM,zoom))

      def sendAnnotationLabelUpdate(self):
            self.statusQueue.put((self.shortName, StatusInformation.UPDATE_LABELS, None))

      def triggerRefreshView(self):
            self.statusQueue.put((self.shortName, StatusInformation.REFRESH_VIEW, None))
      # Show a simple message box with a string message      
      def showMessageBox(self, msg:str):
            self.statusQueue.put((self.shortName, StatusInformation.POPUP_MESSAGEBOX,msg))

      # Update configuration from plugin (e.g. as reaction to slide change, etc..)
      # example:
      # self.updateConfiguration(PluginConfigUpdate([PluginConfigUpdateFloatSlider(uid=0, value=0.5),]))
      def updateConfiguration(self, update: PluginConfigUpdate):
            self.statusQueue.put((self.shortName, StatusInformation.UPDATE_CONFIG,update))

      # Return an image to SlideRunner UI
      def returnImage(self, img : np.ndarray, procId = None):
            self.outQueue.put((img, procId))
      
      def resetImage(self):
            self.outQueue.put((None, -1))


      def exceptionHandlerOnExit(self):
            return

      def updateAnnotations(self):
            self.statusQueue.put((self.shortName, StatusInformation.ANNOTATIONS, self.getAnnotations()))

      def updateInformation(self, pluginInformation):
            self.statusQueue.put((self.shortName, StatusInformation.UPDATE_INFORMATION, pluginInformation))


      def findClickAnnotation(self, clickPosition, pluginVP, zoom:float):
            labels = self.getAnnotationLabels()
            annoKeys=np.array([x.uid for x in labels])[np.where(pluginVP.activeClasses)[0]].tolist()
            for idx,anno in enumerate(self.getAnnotations()):
                  if (anno.pluginAnnotationLabel is None) or (anno.pluginAnnotationLabel.uid in annoKeys):
                        if (anno.positionInAnnotation(clickPosition,zoom=zoom )) and (anno.clickable):
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

class NonePlugin(SlideRunnerPlugin):
      outputType = PluginOutputType.NO_OVERLAY
      pluginType = PluginTypes.NONE_PLUGIN

def generateMinMaxCoordsList( annoList) -> Tuple[np.ndarray, np.ndarray]:
      # MinMaxCoords lists shows extreme coordinates from object, to decide if an object shall be shown
      minCoords = np.zeros(shape=(len(annoList),2))
      maxCoords = np.zeros(shape=(len(annoList),2))
      for annokey in range(len(annoList)):
            annotation = annoList[annokey]
            minCoords[annokey] = np.asarray(annotation.minCoordinates().tolist())
            maxCoords[annokey] = np.asarray(annotation.maxCoordinates().tolist())

      return minCoords, maxCoords

def getVisibleAnnotations(leftUpper:list, rightLower:list, annotations:np.ndarray, minCoords:np.ndarray, maxCoords:np.ndarray) -> list:
#      print('Getting visible annotations from: ',annotations, minCoords, maxCoords)
      if len(minCoords)==0:
            return np.array([])
      potentiallyVisible =  ( (maxCoords[:,0] > leftUpper[0]) & (minCoords[:,0] < rightLower[0]) & 
                              (maxCoords[:,1] > leftUpper[1]) & (minCoords[:,1] < rightLower[1]) )
      return np.array(annotations)[np.where(potentiallyVisible)[0]].tolist()

class activePlugins:
      """
          List of active SlideRunner plugins, and the capabilities to manage them
      """
      _list = []      
      def __init__(self):
          self._list = []
          self.recalculatePlugins()
          self.__activeOverlay = None
      
      def setActiveOverlay(self, plugin:SlideRunnerPlugin):
            if (isinstance(plugin,str)):
                  for k in self._list:
                        if k.shortName==plugin:
                              self.__activeOverlay = k
            else:
                  self.__activeOverlay = plugin
            
            print('Active overlay is now',self.__activeOverlay)
      
      @property
      def activeOverlayPluginType(self):
            if self.__activeOverlay is None:
                  return PluginTypes.NONE_PLUGIN
            else:
                  return self.activeOverlay.pluginType

      def activatePlugin(self, plugin:SlideRunnerPlugin):
            
            for k in self._list:
                  if (plugin.shortName==k.shortName):
                        # plugin already active
                        return

            print('Activated plugin: ',plugin.shortName)
            self._list.append(plugin)
            self.recalculatePlugins()

            # only one overlay available ==> this is the active overlay
            if len(self.pluginsWithOverlays)==1:
                  self.setActiveOverlay(self.pluginsWithOverlays[0])
                  
      
      def deactivatePlugin(self, plugin: SlideRunnerPlugin):
            for k,v in enumerate(self._list):
                  if (plugin.shortName==self._list[k].shortName):
                        # plugin already active
                        del self._list[k]
                        print('Deactivated plugin: ',plugin.shortName)
            # not found, don't throw error
            self.recalculatePlugins()
            if len(self.pluginsWithOverlays)==0:
                  self.setActiveOverlay(NonePlugin)
            
            return

      @property
      def numberActive(self):
            return len(self._list)
      
      @property
      def activePlugins(self):
            return {x.shortName:x for x in self._list}
      
      @property
      def activeOverlay(self) -> SlideRunnerPlugin:
            return self.__activeOverlay

      def recalculatePlugins(self):
            self.recalculatePluginsWithOverlays()
            self.recalculateImagePlugins()
            self.recalculateAnnotationPolicys()

      def recalculatePluginsWithOverlays(self):
          self.__pluginsWithOverlays=[]
          self.__RGBimagePlugins=[]
          for k in self._list:
                if k.outputType in [PluginOutputType.HEATMAP, PluginOutputType.RGB_OVERLAY, PluginOutputType.RGB_IMAGE]:
                      self.__pluginsWithOverlays.append(k)
                if k.outputType == PluginOutputType.RGB_IMAGE:
                      self.__RGBimagePlugins.append(k)

      def recalculateAnnotationPolicys(self):
          self.__annotation_policy_slideupdate=[]
          self.__annotation_policy_scrollupdate=[]
          for k in self._list:
                if k.getAnnotationUpdatePolicy() in [AnnotationUpdatePolicy.UPDATE_ON_SLIDE_CHANGE]:
                      self.__annotation_policy_slideupdate.append(k)
                if k.getAnnotationUpdatePolicy() in [AnnotationUpdatePolicy.UPDATE_ON_SCROLL_CHANGE]:
                      self.__annotation_policy_scrollupdate.append(k)
                if k.pluginType in [PluginTypes.IMAGE_PLUGIN]: # image plugins are also update_on_scroll_change
                      self.__annotation_policy_scrollupdate.append(k)

      def recalculateImagePlugins(self):
          self.__image_plugins=[]
          for k in self._list:
                if k.pluginType in [PluginTypes.IMAGE_PLUGIN]:
                      self.__image_plugins.append(k)
      
      @property
      def RGBimagePlugins(self):
            return self.__RGBimagePlugins

      @property
      def pluginsWithOverlays(self):
            return self.__pluginsWithOverlays
      
      @property
      def imagePlugins(self):
            return self.__image_plugins
      
      @property
      def pluginsWithScrollUpdatePolicy(self):
            return self.__annotation_policy_scrollupdate
      
      
      