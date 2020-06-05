"""

        This is SlideRunner - An Open Source Annotation Tool 
        for Digital Histology Slides.

         Marc Aubreville, Pattern Recognition Lab, 
         Friedrich-Alexander University Erlangen-Nuremberg 
         marc.aubreville@fau.de

        If you use this software in research, please citer our paper:
        M. Aubreville, C. Bertram, R. Klopfleisch and A. Maier:
        SlideRunner - A Tool for Massive Cell Annotations in Whole Slide Images. 
        In: Bildverarbeitung für die Medizin 2018. 
        Springer Vieweg, Berlin, Heidelberg, 2018. pp. 309-314.


   This file: Support for CellVizio MKT files. 


"""

import numpy as np
import pydicom
from pydicom.encaps import decode_data_sequence
from PIL import Image
import io
import os
import struct
from os import stat


class fileinfo:
    offset = 16 # fixed: 16 byte header
    gapBetweenImages = 32 # fixed: 32 byte gap between images
    size = 0 # size of file
    width = 0 # width of images
    height = 0 # height of images
    nImages = 0 # number of images
    circMask = 0; # circular mask (round shape)

class circularMask:
    mask = 0
    def __init__(self,w,h,r):
        self.x,self.y = np.ogrid[-int(h/2):np.ceil(h/2), -int(w/2):np.ceil(w/2)]
        self.mask = self.x*self.x + self.y*self.y <= int(r/2)*int(r/2)


class ReadableCellVizioMKTDataset():

    fi = fileinfo()

    def __init__(self, filename):

       self.fileName = filename
       self.isOpenSlide = False
       self.fileHandle = open(filename, 'rb')
       self.fileHandle.seek(5) # we find the FPS at position 05
       fFPSByte = self.fileHandle.read(4)
       self.fps = struct.unpack('>f', fFPSByte)[0]


       self.fileHandle.seek(10) # we find the image size at position 10
       fSizeByte = self.fileHandle.read(4)
       self.fi.size = int.from_bytes(fSizeByte, byteorder='big', signed=True)
       self.fi.nImages=1000

       self.fi.width = 576
       if ((self.fi.size/(2*self.fi.width))%2!=0):
            self.fi.width=512
            self.fi.height=int(self.fi.size/(2*self.fi.width))
       else:
            self.fi.height=int(self.fi.size/(2*self.fi.width))

       self.filestats = stat(self.fileName)
       self.fi.nImages = int((self.filestats.st_size-self.fi.offset) / (self.fi.size+self.fi.gapBetweenImages))


       self.numberOfFrames = self.fi.nImages

       self.geometry_imsize = [self.fi.height, self.fi.width]
       self.imsize = [self.fi.height, self.fi.width]
       self.geometry_tilesize = [(self.fi.height, self.fi.width)]
       self.geometry_rows = [1]
       self.geometry_columns = [1]
       self.levels = [1]
       self.channels = 1
       self.mpp_x = 1e-6
       self.mpp_y  = 1e-6

       self.circMask = circularMask(self.fi.width,self.fi.height, self.fi.width-2).mask

    

    @property
    def seriesInstanceUID(self) -> str:
        return ''

    @property
    def level_downsamples(self):
        return [1]

    @property 
    def level_dimensions(self):
        return [self.geometry_imsize]

    def readImage(self, position=0):

       self.fileHandle.seek(self.fi.offset + self.fi.size*position + self.fi.gapBetweenImages*position)

       image = np.fromfile(self.fileHandle, dtype=np.int16, count=int(self.fi.size/2))

       image=np.reshape(image, newshape=(self.fi.height, self.fi.width))

       image = np.ma.masked_array(image, 1-self.circMask) # apply mask to image
       return image

    def scaleImageUINT8(self, image, mask = None):
       # read image and scale to uint8 [0;255] format

       if (mask is None):
           mask = self.circMask

       maskedImage = image[mask]

       cmin,cmax = np.percentile(maskedImage,0.5), np.percentile(maskedImage,99.5)
       if (cmax>5000):
           cmax=5000
       dyn=cmax-cmin

       # compress
       compr=255/dyn
       image = image-cmin
       image = image*compr

       # limit to 0
       image = np.clip(np.round(image),0,255)
       image=np.uint8(image)

       return image
    def readImageUINT8(self, position=0):
       # read image and scale to uint8 [0;255] format
       image=self.readImage(position)

       image = self.scaleImageUINT8(image)
       return image

    def read_region(self, location: tuple, level:int, size:tuple, zLevel:int):
        img = np.zeros((size[1],size[0],4), np.uint8)
        img[:,:,3]=255
        offset=[0,0]
        if (location[1]<0):
            offset[0] = -location[1]
            location = (location[0],0)
        if (location[0]<0):
            offset[1] = -location[0]
            location = (0,location[1])

        pixel_array = self.readImageUINT8(position=zLevel)
        imgcut = pixel_array[location[1]:location[1]+size[1]-offset[0],location[0]:location[0]+size[0]-offset[1]]
        imgcut = np.uint8(np.clip(np.float32(imgcut),0,255))

        for k in range(3):
            img[offset[0]:imgcut.shape[0]+offset[0],offset[1]:offset[1]+imgcut.shape[1],k] = imgcut
        return Image.fromarray(img)


    @property
    def dimensions(self):
        return self.level_dimensions[0]

    def get_best_level_for_downsample(self,downsample):
        return np.argmin(np.abs(np.asarray(self.level_downsamples)-downsample))

    @property
    def level_count(self):
        return len(self.levels)

    def imagePos_to_id(self, imagePos:tuple, level:int):
        id_x, id_y = imagePos
        if (id_y>=self.geometry_rows[level]):
            id_x=self.geometry_columns[level] # out of range

        if (id_x>=self.geometry_columns[level]):
            id_y=self.geometry_rows[level] # out of range
        return (id_x+(id_y*self.geometry_columns[level]))
    

    def get_id(self, pixelX:int, pixelY:int, level:int) -> (int, int, int):

        id_x = round(-0.5+(pixelX/self.geometry_tilesize[level][1]))
        id_y = round(-0.5+(pixelY/self.geometry_tilesize[level][0]))
        
        return (id_x,id_y), pixelX-(id_x*self.geometry_tilesize[level][0]), pixelY-(id_y*self.geometry_tilesize[level][1]),

    