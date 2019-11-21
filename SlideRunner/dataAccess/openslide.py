import openslide
import multiprocessing
import numpy as np
class SlideReader(multiprocessing.Process):
    def __init__(self):
        multiprocessing.Process.__init__(self)
        self.sl = None
        self.slidename = None
        self.slide = None
        self.daemon=True
        self.queue = multiprocessing.Queue()
        self.outputQueue = multiprocessing.Queue()
        print('initializing SlideReader')

    def run(self):
        print('running slidereader')
        while (True):
            (slidename, location, level, size, id) = self.queue.get()
            print('Got new request')

            if (slidename==-1):
                print('Exiting SlideReader thread')
                return

            if (slidename!=self.slidename):
                self.slide = openslide.open_slide(slidename)
                self.slidename = slidename
            
            if not (self.queue.empty()):
                # New request pending
                continue

            img = self.slide.read_region(location, level, size)

            self.outputQueue.put((np.array(img),id))

