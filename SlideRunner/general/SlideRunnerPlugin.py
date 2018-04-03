class PluginTypes(enumerate):
      IMAGE_PLUGIN = 0
      WHOLESLIDE_PLUGIN = 1

class SlideRunnerPlugin:
      description = 'This is a sample plugin'
      shortName = 'SamplePlugin'
      enabled = False
      inQueue = None
      version = '0.0'
      outQueue = None
      pluginType = PluginTypes.IMAGE_PLUGIN
      
      def __init__(self,foo,bar):
            self.description = 'This is a sample plugin'
      
      def __str__(self):
            return self.shortName