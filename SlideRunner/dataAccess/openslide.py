import openslide
import multiprocessing
import queue
import time
import numpy as np

class SlideReader(multiprocessing.Process):
    def __init__(self):
        multiprocessing.Process.__init__(self)
        self.sl = None
        self.slidename = None
        self.slide = None
        self.daemon=True
        self.queue = multiprocessing.Queue(50)
        self.outputQueue = multiprocessing.Queue()

    def run(self):
        img=None
        while (True):
            (slidename, location, level, size, id) = self.queue.get()

            try:
                while(True):
                    (slidename, location, level, size, id) = self.queue.get(True,0.01)
            except queue.Empty:
                pass


            if (slidename==-1):
                print('Exiting SlideReader thread')
                return

            if (slidename!=self.slidename):
                self.slide = openslide.open_slide(slidename)
                self.slidename = slidename

            img = self.slide.read_region(location, level, size)

            self.outputQueue.put((np.array(img),id))

