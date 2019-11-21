
from SlideRunner.processing.screening import *
import numpy as np
def test_screening():
    overview = np.zeros((100,100,3),np.uint8)
    overview[:,:,:] = 255
    overview[:,5:15,:] = 0
    overview[0,0,:] = 254 # removed by otsu
    overview[99,99,:] = 254 # removed by otsu

    overview[50:52,5:15,:] = 255 # removed by closing operator
    
    map = screeningMap(overview=overview,mainImageSize=(500,500), slideLevelDimensions=[[500,500],[100,100]], thumbNailSize=(20,20), thresholding='OTSU')    

    # in mean, exactly 10 lines in the map
    assert(np.sum(map.mapWorkingCopy)/255/100)

    map.annotate(imgarea_p1=(200,200), imgarea_w=(250,250))

    # rectangle with (in total) 121 pixels was created
    assert((np.sum(map.mapHeatmap)/255)==121.0)

