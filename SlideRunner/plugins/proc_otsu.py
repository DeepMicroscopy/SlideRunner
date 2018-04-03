import SlideRunner.general.SlideRunnerPlugin as SlideRunnerPlugin
import queue
from threading import Thread
from queue import Queue
import cv2
import numpy as np


class Plugin(SlideRunnerPlugin.SlideRunnerPlugin):
    version = 0.1
    shortName = 'OTSU threshold'
    inQueue = Queue()
    outQueue = Queue()
    description = 'Apply simple OTSU threshold on the current image'
    pluginType = SlideRunnerPlugin.PluginTypes.IMAGE_PLUGIN
    
    def __init__(self, statusQueue:Queue):
        self.statusQueue = statusQueue
        self.p = Thread(target=self.queueWorker, daemon=True)
        self.p.start()
        
        pass

    def queueWorker(self):
        while True:
            (image) = self.inQueue.get()
            print('OTSU plugin: received 1 image from queue')

            print(image.shape)
            rgb = np.copy(image[:,:,0:3])
            print(rgb.shape)
            # Convert to grayscale
#            rgb = np.float32(cv2.cvtColor(np.array(image), cv2.COLOR_BGRA2RGB))[:,:,::-1]
#            print(rgb.shape)

            gray = cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
            # OTSU thresholding
            ret, thresh = cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)

            self.outQueue.put(np.float32(thresh/255.0))
            print('OTSU plugin: done')



        