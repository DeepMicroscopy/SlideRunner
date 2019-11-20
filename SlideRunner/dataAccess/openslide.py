import openslide
import multiprocessing
import numpy as np
class SlideReader(multiprocessing.Process):
    queue = multiprocessing.Queue()
    outputQueue = multiprocessing.Queue()
    def __init__(self):
        multiprocessing.Process.__init__(self)
        self.sl = None
        self.slidename = None
        self.slide = None

    def run(self):
        while (True):
            (slidename, location, level, size, id) = self.queue.get()

            if (slidename==-1):
                return

            if (slidename!=self.slidename):
                self.slide = openslide.open_slide(slidename)
                self.slidename = slidename
            
            if not (self.queue.empty()):
                # New request pending
                continue

            img = self.slide.read_region(location, level, size)

            self.outputQueue.put((np.array(img),id))

