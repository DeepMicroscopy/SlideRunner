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
    updateTimer=0.5
    outputType = SlideRunnerPlugin.PluginOutputType.BINARY_MASK
    description = 'Apply simple OTSU threshold on the current image'
    pluginType = SlideRunnerPlugin.PluginTypes.IMAGE_PLUGIN
    
    def __init__(self, statusQueue:Queue):
        self.statusQueue = statusQueue
        self.p = Thread(target=self.queueWorker, daemon=True)
        self.p.start()
        
        pass

    def queueWorker(self):
        quitSignal=False
        while not quitSignal:
            job = SlideRunnerPlugin.pluginJob(self.inQueue.get())
            image = job.currentImage

            if (job.jobDescription == SlideRunnerPlugin.JobDescription.QUIT_PLUGIN_THREAD):
                # signal to exit this thread
                quitSignal=True
                continue
            print('OTSU plugin: received 1 image from queue')
            self.setProgressBar(0)

            rgb = np.copy(image[:,:,0:3])

            gray = cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
            # OTSU thresholding
            ret, thresh = cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)

            self.returnImage(np.float32(thresh/255.0), job.procId)
            self.setMessage('OTSU calculation done.')
            print('OTSU plugin: done')
            self.setProgressBar(-1)



        