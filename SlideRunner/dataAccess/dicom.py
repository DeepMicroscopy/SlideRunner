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


   This file: Support for DICOM WSI files. 

   To create a DICOM WSI file out of an openslide-supported WSI file, use wsi2dcm, available from:

   https://github.com/GoogleCloudPlatform/wsi-to-dicom-converter


"""

import numpy as np
import pydicom
from pydicom.encaps import decode_data_sequence
from PIL import Image
import io
import os

class sequencedTiles(object):
  #
  def __init__(self, dsstore):
      self._dsstore = dsstore
      self._dsequence = dict()

  def __getitem__(self, key):
    if (key) in self._dsequence:
        return self._dsequence[key]
    elif key not in self._dsstore:
        raise ValueError('Entry does not exist')
    else:
        self._dsequence[key] = decode_data_sequence(self._dsstore[key].PixelData)
        return self._dsequence[key]
  #
  def __setitem__(self, key, value):
    raise NotImplementedError()

class ReadableDicomDataset():
    def __init__(self, filename):

        self._ds = pydicom.dcmread(filename)
        self._sequenceInstanceUID = self._ds.SeriesInstanceUID
        
        self._path, _ = os.path.split(filename)
        if (self._path==""):
            self._path='.'+os.sep

        self._dsstore = dict()

        # look for all other levels
        for dcmfile in os.listdir(self._path):
            if os.path.splitext(dcmfile)[-1].upper()=='.DCM':
                try:
                    tmpdcm = pydicom.dcmread(self._path+os.sep+dcmfile)
                    if (tmpdcm.InstanceNumber) is None:
                        self._dsstore[0] = tmpdcm      
                    elif (tmpdcm.SeriesInstanceUID==self._sequenceInstanceUID):
                        self._dsstore[tmpdcm.InstanceNumber-1] = tmpdcm            
                except Exception as e:
                    print(f'Warning: Unable to open {dcmfile}:',e)
        
        # some DICOM files have no instance 0 (as DICOM WSIs)
        if 0 not in self._dsstore:
            self._dsstore = {0: list(self._dsstore.values())[0]}

        # check if all instances have same resolution --> this is a stack
        dims_instances = [[self._dsstore[x].Columns,self._dsstore[x].Rows ] for x in self._dsstore]
        stack = all([dims_instances[x][0]==dims_instances[0][0] for x in range(len(dims_instances))]) and \
                all([dims_instances[x][1]==dims_instances[0][1] for x in range(len(dims_instances))]) and len(dims_instances)>1    
        self.multiInstanceStack = stack

        self._dsequence = sequencedTiles(self._dsstore)
        
        try:
            self.levels = sorted(list(self._dsstore.keys()))
            self.geometry_imsize = [(self._dsstore[k][0x48,0x6].value,self._dsstore[k][0x48,0x7].value) for k in self.levels]
            self.geometry_tilesize = [(self._dsstore[k].Columns, self._dsstore[k].Rows) for k in self.levels]
            self.geometry_columns = [round(0.5+(self.geometry_imsize[k][0]/self.geometry_tilesize[k][0])) for k in self.levels]
            self.geometry_rows = [round(0.5 + (self.geometry_imsize[k][1] / self.geometry_tilesize[k][1] )) for k in self.levels]
            self.channels = self._ds[0x0028, 0x0002].value
            self.mpp_x = float(self._dsstore[0].SharedFunctionalGroupsSequence[0][0x028,0x9110][0][0x028,0x030][0])*1000
            self.mpp_y = float(self._dsstore[0].SharedFunctionalGroupsSequence[0][0x028,0x9110][0][0x028,0x030][1])*1000
            self.numberOfFrames = 1
        except Exception as e:
            # Fall back to simple reader
            self.levels = sorted(list(self._dsstore.keys())) if not stack else [0]
            self.read_region = self.read_region_simple
            self.extremes = np.min(self._dsstore[0].pixel_array), np.max(self._dsstore[0].pixel_array)
            self.geometry_imsize = [self._dsstore[0].Columns, self._dsstore[0].Rows]
            self.geometry_tilesize = [(self._dsstore[0].Columns, self._dsstore[0].Rows)]
            self.geometry_rows = [1]
            self.geometry_columns = [1]
            self.channels = 1
            self.mpp_x = 1e-6
            self.mpp_y  = 1e-6

            if not stack:
                self.numberOfFrames = self._dsstore[0].NumberOfFrames if ('NumberOfFrames' in self._dsstore[0]) else 1
            else:
                self.numberOfFrames = len(dims_instances)
            self.fps = 1000/self._dsstore[0].FrameTime if ('FrameTime' in self._dsstore[0]) else 1.0

    

    @property
    def seriesInstanceUID(self) -> str:
        return self._sequenceInstanceUID

    @property
    def level_downsamples(self):
        try:
            return [self._dsstore[0].TotalPixelMatrixColumns/self._dsstore[k].TotalPixelMatrixColumns for k in self.levels]        
        except:
            return [1]

    @property 
    def level_dimensions(self):
        try:
            return [(self._dsstore[k].TotalPixelMatrixColumns,self._dsstore[k].TotalPixelMatrixRows) for k in self.levels]    
        except:
            return [self.geometry_imsize]

    def read_region_simple(self, location: tuple, level:int, size:tuple, zLevel:int=0):
        img = np.zeros((size[1],size[0],4), np.uint8)
        img[:,:,3]=255
        offset=[0,0]
        if (location[1]<0):
            offset[0] = -location[1]
            location = (location[0],0)
        if (location[0]<0):
            offset[1] = -location[0]
            location = (0,location[1])
        if (self.numberOfFrames>1) and not (self.multiInstanceStack):
            imgcut = self._dsstore[0].pixel_array[zLevel, location[1]:location[1]+size[1]-offset[0],location[0]:location[0]+size[0]-offset[1]]
        elif (self.multiInstanceStack):
            imgcut = np.copy(self._dsstore[zLevel].pixel_array[location[1]:location[1]+size[1]-offset[0],location[0]:location[0]+size[0]-offset[1]])
        else:
            imgcut = np.copy(self._dsstore[0].pixel_array[location[1]:location[1]+size[1]-offset[0],location[0]:location[0]+size[0]-offset[1]])
        imgcut = np.uint8(np.clip(np.float32(imgcut)/(self.extremes[1])*255.0,0,255))
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
    
    def get_tile(self, pos, level:int):
        if pos < self._dsstore[level].NumberOfFrames:
            return np.array(Image.open(io.BytesIO(self._dsequence[level][pos])))
        else:
            if (self.channels>1):
                return np.zeros((*self.geometry_tilesize[level], self.channels))
            else:
                return np.zeros(self.geometry_tilesize[level])

    def get_id(self, pixelX:int, pixelY:int, level:int) -> (int, int, int):

        id_x = round(-0.5+(pixelX/self.geometry_tilesize[level][1]))
        id_y = round(-0.5+(pixelY/self.geometry_tilesize[level][0]))
        
        return (id_x,id_y), pixelX-(id_x*self.geometry_tilesize[level][0]), pixelY-(id_y*self.geometry_tilesize[level][1]),

        
    def read_region(self, location: tuple, level:int, size:tuple, zLevel:int=None):
        # convert to overall coordinates, if not in level 0
        if (self.level_downsamples[level]>1):
            location = [int(x/self.level_downsamples[level]) for x in location]

        lu, lu_xo, lu_yo = self.get_id(*list(location),level=level)
        rl, rl_xo, rl_yo = self.get_id(*[sum(x) for x in zip(location,size)], level=level)
        # generate big image
        bigimg = 0*np.ones(((rl[1]-lu[1]+1)*self.geometry_tilesize[level][0], (rl[0]-lu[0]+1)*self.geometry_tilesize[level][1],4), np.uint8)
        bigimg[:,:,3] = 255
        for xi, xgridc in enumerate(range(lu[0],rl[0]+1)):
            for yi, ygridc in enumerate(range(lu[1],rl[1]+1)):
                if (xgridc<0) or (ygridc<0):
                    continue
                if (self.channels==3):
                    bigimg[yi*self.geometry_tilesize[level][0]:(yi+1)*self.geometry_tilesize[level][0],
                        xi*self.geometry_tilesize[level][1]:(xi+1)*self.geometry_tilesize[level][1],0:-1] = \
                        self.get_tile(self.imagePos_to_id((xgridc,ygridc),level=level), level)
                elif (self.channels==1):
                    # 
                    for k in range(3):
                        bigimg[yi*self.geometry_tilesize[level][0]:(yi+1)*self.geometry_tilesize[level][0],
                            xi*self.geometry_tilesize[level][1]:(xi+1)*self.geometry_tilesize[level][1],k] = \
                            self.get_tile(self.imagePos_to_id((xgridc,ygridc),level=level), level)
        # crop big image
        return Image.fromarray(bigimg[lu_yo:lu_yo+size[1],lu_xo:lu_xo+size[0]])
    