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


   This file: Support for NIFTI files. Requires nibabel to work.


"""

import numpy as np
try:
    import nibabel as nib 
    nii_fileformats = ['*.nii', '*.nii.gz']
except:
    nib = None
    print('Warning: nibabel not installed. Neuroimaging formats will not be available.')
    nii_fileformats = []

from PIL import Image
import io
import os



class ReadableNIBDataset():
    def __init__(self, filename):

        self._sequenceInstanceUID = ''
        
        self._path, _ = os.path.split(filename)
        if (self._path==""):
            self._path='.'+os.sep

        self._dsstore = dict()

        self.isOpenSlide = False
        self.nib = nib.load(filename)
        self.imdata = self.nib.dataobj.reshape((*self.nib.shape[0:2],-1)) # flatten 
        
        self.levels = [0]
        self.channels = 1
        self.numberOfFrames = self.imdata.shape[2] # last dimension is number of frames

        self.mpp_x = 1000/self.nib.header.get_zooms()[1] # 1000 microns/mm / (vx/mm) = microns/vx 
        self.geometry_imsize = self.imdata.shape[0:2]
        self.geometry_rows = [1]
        self.geometry_columns = [1]
        self.extremes = np.min(self.imdata), np.max(self.imdata)

    

    @property
    def level_downsamples(self):
        return [1]

    @property 
    def level_dimensions(self):
        return [self.geometry_imsize]

    def read_region(self, location: tuple, level:int, size:tuple, zLevel:int=0, rotate:bool=True):
        img = np.zeros((size[1],size[0],4), np.uint8)
        img[:,:,3]=255
        offset=[0,0]
        if (location[1]<0):
            offset[0] = -location[1]
            location = (location[0],0)
        if (location[0]<0):
            offset[1] = -location[0]
            location = (0,location[1])
        imgcut = self.imdata[location[1]:location[1]+size[1]-offset[0],location[0]:location[0]+size[0]-offset[1],zLevel]
        ext = np.percentile(self.imdata[:,:,zLevel],5),np.percentile(self.imdata[:,:,zLevel],95)
#        print('Extremes:',ext,'rotate:',rotate,'zLevel',zLevel)
        imgcut = np.uint8(np.clip(np.float32(imgcut)/(ext[1])*255.0,0,255))
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
    

        
    