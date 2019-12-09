import openslide
import multiprocessing
import queue
import time
import numpy as np

class RotatableOpenSlide(openslide.OpenSlide):
    def __init__(self, filename, rotate=False):
        self.rotate=rotate
        return super().__init__(filename)
    
    # Implements 180 degree rotated version of read_region
    def read_region(self, location, level, size):
    #    print('reading from: ',location)
    #    print('rescaling image:', self.level_downsamples[level])
        if (self.rotate):
            location = [int(x-y-(w*self.level_downsamples[level])) for x,y,w in zip(self.dimensions, location, size)]
            return super().read_region(location, level, size).rotate(180)
        else:
            return super().read_region(location, level, size)

    def slide_center(self):
        return [int(x/2) for x in self.dimensions]
    
    def read_centerregion(self, location, level, size, center=None):
        center = self.slide_center() if center is None else center
    #    print('Offset to center location:', [self.level_downsamples[level]*s for s in size], self.level_downsamples[level])
        return self.read_region([int(x-s*self.level_downsamples[level]/2-d) for x,d,s in zip(center,location, size)], level, size)
    

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
            (slidename, location, level, size, id, rotated) = self.queue.get()

            try:
                while(True):
                    (slidename, location, level, size, id, rotated) = self.queue.get(True,0.01)
            except queue.Empty:
                pass


            if (slidename==-1):
                print('Exiting SlideReader thread')
                return

            if (slidename!=self.slidename):
                self.slide = RotatableOpenSlide(slidename, rotate=rotated)
                self.slidename = slidename
            self.slide.rotate = rotated

            img = self.slide.read_region(location, level, size)

            self.outputQueue.put((np.array(img),id))

