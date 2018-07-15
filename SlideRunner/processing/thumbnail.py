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
"""

import cv2
import numpy as np


class thumbnail():
    """
        Thumbnail object for SlideRunner
    """

    thumbnail = None
    workingCopy = None
    downsampled = None
    thumbnail_numpy = None
    size = None
    slide = None

    def __init__(self, sl ):
        thumbNail = sl.get_thumbnail(size=(200, 200))
        self.thumbnail = thumbNail
        self.thumbnail_numpy = np.array(self.thumbnail, dtype=np.uint8)
        if (self.thumbnail_numpy.shape[0]>self.thumbnail_numpy.shape[1]):
            thumbnail_numpy_new = np.ones((200,200,3), np.uint8)*52
            thumbnail_numpy_new[0:self.thumbnail_numpy.shape[0],0:self.thumbnail_numpy.shape[1],:] = self.thumbnail_numpy
            self.thumbnail_numpy = thumbnail_numpy_new
        else:
            self.thumbnail_numpy = cv2.resize(self.thumbnail_numpy, dsize=(200,thumbNail.size[1]))
        self.downsamplingFactor = np.float32(sl.dimensions[1]/thumbNail.size[1])
        self.size = self.thumbnail.size
        self.slide = sl
        self.shape = self.thumbnail_numpy.shape
    
    def getCopy(self):
        return np.copy(self.thumbnail_numpy)

    def annotateCurrentRegion(self, npimage, imgarea_p1, imgarea_w):

        image_dims = self.slide.level_dimensions[0]
        overview_p1 = (int(imgarea_p1[0] / image_dims[0] * self.thumbnail.size[0]),int(imgarea_p1[1] / image_dims[1] * self.thumbnail.size[1]))
        overview_p2 = (int((imgarea_p1[0]+imgarea_w[0]) / image_dims[0] * self.thumbnail.size[0]),int((imgarea_w[1]+imgarea_p1[1]) / image_dims[1] * self.thumbnail.size[1]))
        cv2.rectangle(npimage, pt1=overview_p1, pt2=overview_p2, color=[255,0,0,127],thickness=2)

        return npimage