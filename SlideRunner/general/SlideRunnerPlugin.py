"""
      Definition of the class SlideRunnerPlugin, used to derive plugins
"""


class PluginTypes(enumerate):
      IMAGE_PLUGIN = 0
      WHOLESLIDE_PLUGIN = 1

class PluginOutputType(enumerate):
      BINARY_MASK = 0
      RGB_IMAGE = 1

class JobDescription(enumerate):
      PROCESS = 0
      QUIT_PLUGIN_THREAD = 99

class pluginJob():
      jobDescription = None
      slideFilename = None
      coordinates = None
      currentImage = None
      configuration = list()
      
      def __init__(self, queueTuple):
            self.jobDescription, self.currentImage, self.slideFilename, self.coordinates, self.configuration = queueTuple

def jobToQueueTuple(description=JobDescription.PROCESS, currentImage=None, coordinates=None, configuration=list(), slideFilename=None):
      return (description, currentImage, slideFilename, coordinates, configuration)

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
      initialOpacity = 0.3
      configurationList = list()
      outputType = PluginOutputType.BINARY_MASK
      pluginType = PluginTypes.IMAGE_PLUGIN
      
      def __init__(self,foo,bar):
            self.description = 'This is a sample plugin'
      
      def __str__(self):
            return self.shortName