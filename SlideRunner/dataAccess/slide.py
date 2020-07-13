import openslide
import multiprocessing
import queue
import time
import numpy as np
import os
from . import dicom
from . import cellvizio
from openslide.lowlevel import OpenSlideError, OpenSlideUnsupportedFormatError
from PIL import Image
import PIL
PIL.Image.MAX_IMAGE_PIXELS = 933120000

# This is a 3D version of openslide.ImageSlide, supporting z stacks

class ImageSlide3D(openslide.ImageSlide):

    def __init__(self, file):
        """Open an image file.

        file can be a filename or a PIL.Image."""
        openslide.ImageSlide.__init__(self, file)

        try:
            self.numberOfFrames = self._image.n_frames 
        except:
            self.numberOfFrames = 1
        


    def read_region(self, location, level, size, zStack):
        """Return a PIL.Image containing the contents of the region.

        location: (x, y) tuple giving the top left pixel in the level 0
                  reference frame.
        level:    the level number.
        size:     (width, height) tuple giving the region size."""

        if level != 0:
            raise OpenSlideError("Invalid level")
        if ['fail' for s in size if s < 0]:
            raise OpenSlideError("Size %s must be non-negative" % (size,))
        # Any corner of the requested region may be outside the bounds of
        # the image.  Create a transparent tile of the correct size and
        # paste the valid part of the region into the correct location.
        image_topleft = [max(0, min(l, limit - 1))
                    for l, limit in zip(location, self._image.size)]
        image_bottomright = [max(0, min(l + s - 1, limit - 1))
                    for l, s, limit in zip(location, size, self._image.size)]
        tile = Image.new("RGBA", size, (0,) * 4)
        #print(self._image)
        if not ['fail' for tl, br in zip(image_topleft, image_bottomright)
                if br - tl < 0]:  # "< 0" not a typo
            # Crop size is greater than zero in both dimensions.
            # PIL thinks the bottom right is the first *excluded* pixel
            self._image.seek(zStack)
            crop = self._image.crop(image_topleft +
                    [d + 1 for d in image_bottomright])
            tile_offset = tuple(il - l for il, l in
                    zip(image_topleft, location))
            tile.paste(crop, tile_offset)
        return tile    

class RotatableOpenSlide(object):

    def __new__(cls, filename, rotate):
        if cls is RotatableOpenSlide:
            bname, ext = os.path.splitext(filename)
            if ext.upper() == '.DCM': return type("RotatableOpenSlide", (RotatableOpenSlide, dicom.ReadableDicomDataset,openslide.ImageSlide), {})(filename, rotate)
            if ext.upper() == '.MKT': return type("ReadableCellVizioMKTDataset", (RotatableOpenSlide, cellvizio.ReadableCellVizioMKTDataset, openslide.ImageSlide), {})(filename,rotate)
#            if ext.upper() == '.TIF': return type("RotatableOpenSlide", (RotatableOpenSlide, ImageSlide3D,openslide.ImageSlide), {})(filename, rotate)
            try:
                slideobj = type("OpenSlide", (RotatableOpenSlide,openslide.OpenSlide), {})(filename, rotate)
                slideobj.isOpenSlide = True
                return slideobj
            except:
                print('Opened IMAGESLIDE object')
                slideobj = type("ImageSlide", (RotatableOpenSlide,ImageSlide3D), {})(filename, rotate)
                slideobj.isOpenSlide = False
                return slideobj
        else:
            return object.__new__(cls)

    def __init__(self, filename, rotate=False):
        if ('rotate' in self.__dict__): # speed up - somehow init is called twice. Let's skip that.
            return
        self.rotate=rotate
        self.type=0
        self.numberOfFrames = 1
        self.fps = 1.0
        return super().__init__(filename)




    # Implements 180 degree rotated version of read_region
    def read_region(self, location, level, size, zLevel=0):
        # zlevel is ignored for SVS files
        if (self.rotate):
            location = [int(x-y-(w*self.level_downsamples[level])) for x,y,w in zip(self.dimensions, location, size)]
            return super().read_region(location, level, size, zLevel).rotate(180)
        else:
            if (self.isOpenSlide):
                return super().read_region(location, level, size)
            else:
                return super().read_region(location, level, size, zLevel)

    def transformCoordinates(self, location, level=0, size=None, inverse=False):
        if (self.rotate):
            retarr = np.copy(location)
            retarr[:,0] = self.dimensions[0]-retarr[:,0]
            retarr[:,1] = self.dimensions[1]-retarr[:,1]
            return retarr
        else:
            return location

    def slide_center(self):
        return [int(x/2) for x in self.dimensions]
    
    def read_centerregion(self, location, level, size, center=None, zLevel=0):
        center = self.slide_center() if center is None else center
    #    print('Offset to center location:', [self.level_downsamples[level]*s for s in size], self.level_downsamples[level])
        return self.read_region([int(x-s*self.level_downsamples[level]/2-d) for x,d,s in zip(center,location, size)], level, size, zLevel)
    

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
        lastReq = [(-1,-1),-1,(512,512)]
        while (True):
            (slidename, location, level, size, id, rotated, zlevel) = self.queue.get()

            try:
                while(True):
                    (slidename, location, level, size, id, rotated, zlevel) = self.queue.get(True,0.01)
            except queue.Empty:
                pass


            if (slidename==-1):
                print('Exiting SlideReader thread')
                return

            if (slidename!=self.slidename):
                print('Opening new slide, name differs')
                self.slide = RotatableOpenSlide(slidename, rotate=rotated)
                self.slidename = slidename
                newSlide=True
            else:
                newSlide=False

            self.slide.rotate = rotated

            if not all([a==b for a,b in zip([location,level,size,zlevel],lastReq)]) or newSlide:
                img = self.slide.read_region(location, level, size, zLevel=zlevel)
                lastReq = [location, level, size,zlevel]

            self.outputQueue.put((np.array(img),id))

