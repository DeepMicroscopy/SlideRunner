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

class screeningMap(object):

    map = None
    mapWorkingCopy = None
    dims_screeningmap = None
    slideLevelDimensions = None
    thumbNailSize = None
    mapHeatmap = None
    mainImageSize = None

    # Reset screening - create new copy of screening map
    def reset(self):
        self.mapWorkingCopy = np.copy(self.map)

    def checkIsNew(self,coordinates):
        check_x = np.int16(np.floor((coordinates[0])*self.map.shape[1]))
        check_y = np.int16(np.floor((coordinates[1])*self.map.shape[0]))

        sumMap = np.sum(self.mapWorkingCopy[check_y:check_y+self.dims_screeningmap[1], check_x:check_x+self.dims_screeningmap[0]])
        if (sumMap>0.01*self.dims_screeningmap[0]*self.dims_screeningmap[1]):
            return True
        
        return False

    def __init__(self,overview, mainImageSize, slideLevelDimensions, thumbNailSize):
            super(screeningMap, self).__init__()        
            # Convert to grayscale
            gray = cv2.cvtColor(overview,cv2.COLOR_BGR2GRAY)

            # OTSU thresholding
            ret, thresh = cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)

            # dilate
            dil = cv2.dilate(thresh, kernel = np.ones((7,7),np.uint8))

            # erode
            er = cv2.erode(dil, kernel = np.ones((7,7),np.uint8))

            self.map = er
            self.mapWorkingCopy = np.copy(er)

            w_screeningmap = np.int16(np.floor(mainImageSize[0]/slideLevelDimensions[0][0]*self.map.shape[1])*0.9)
            h_screeningmap = np.int16(np.floor(mainImageSize[1]/slideLevelDimensions[0][1]*self.map.shape[0])*0.9)
            self.dims_screeningmap = (w_screeningmap, h_screeningmap)

            self.slideLevelDimensions = slideLevelDimensions

            self.mapHeatmap = np.zeros((thumbNailSize[1],thumbNailSize[0]))
            self.thumbNailSize=thumbNailSize
            self.mainImageSize=mainImageSize


    """
        Display screening map as an overlay to the overview image
    """

    def overlayHeatmap(self, numpyImage) -> np.ndarray:
        numpyImage[:,:,0] = np.uint8(np.clip((np.float32(numpyImage[:,:,0]) * (1-self.mapHeatmap[:,:]/255)),0,255))
        numpyImage[:,:,1] = np.uint8(np.clip((np.float32(numpyImage[:,:,1]) * (1+self.mapHeatmap[:,:]/255)),0,255))
        numpyImage[:,:,2] = np.uint8(np.clip((np.float32(numpyImage[:,:,2]) * (1-self.mapHeatmap[:,:]/255)),0,255))
        return numpyImage

    """
         Annotate currently viewed screen on screening map.
    """
    
    
    def annotate(self, imgarea_p1, imgarea_w):
        x_screeningmap = np.int16(np.floor(imgarea_p1[0]/self.slideLevelDimensions[0][0]*self.mapWorkingCopy.shape[1]))
        y_screeningmap = np.int16(np.floor(imgarea_p1[1]/self.slideLevelDimensions[0][1]*self.mapWorkingCopy.shape[0]))

        self.mapWorkingCopy[y_screeningmap:y_screeningmap+self.dims_screeningmap[1],x_screeningmap:x_screeningmap+self.dims_screeningmap[0]] = 0

        image_dims=self.slideLevelDimensions[0]

        # annotate on heatmap
        overview_p1 = (int(imgarea_p1[0] / image_dims[0] * self.thumbNailSize[0]),int(imgarea_p1[1] / image_dims[1] * self.thumbNailSize[1]))
        overview_p2 = (int((imgarea_p1[0]+imgarea_w[0]) / image_dims[0] * self.thumbNailSize[0]),int((imgarea_w[1]+imgarea_p1[1]) / image_dims[1] * self.thumbNailSize[1]))

        col = int(20*np.square(12*self.mainImageSize[0]/imgarea_w[0]))
        if (col>255):
            col=255
        ohBackup = np.copy(self.mapHeatmap)
        cv2.rectangle(self.mapHeatmap, pt1=overview_p1, pt2=overview_p2,  color=col, thickness=-1)

        self.mapHeatmap = np.maximum(self.mapHeatmap, ohBackup)
        
