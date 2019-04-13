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

        This file:
         Positive Pixel Count Algorithm  (Aperio)
         
         see:
         Olson, Allen H. "Image analysis using the Aperio ScanScope." Technical manual. Aperio Technologies Inc (2006).



"""

import SlideRunner.general.SlideRunnerPlugin as SlideRunnerPlugin
import queue
from threading import Thread
from queue import Queue
import cv2
import os
import numpy as np
import matplotlib.pyplot as plt 
import sklearn.cluster
import matplotlib.colors
import staintools
import scipy
import pickle
import SlideRunner.dataAccess.annotations as annotations 
import matplotlib.path as path
from skimage.feature import blob_dog
from staintools.miscellaneous.get_concentrations import get_concentrations

def BlobDetection(I):
    # removes salt and pepper noise
    image_gray = scipy.ndimage.filters.median_filter(I, size=(2, 2))

    # Difference of Gaussian
    blobs_dog = blob_dog(image_gray, max_sigma=20, threshold=.1)

    #small detected blobs, because of the size (cannot be CD3-positive cells) were deleted,
    blob2 = np.extract(blobs_dog[:,2] > 6, blobs_dog[:,2])
    blob1 = np.extract(blobs_dog[:,2] > 6, blobs_dog[:,1])
    blob0 = np.extract(blobs_dog[:,2] > 6, blobs_dog[:,0])
    blobs_dog = np.c_[blob0, blob1]
    blobs_dog = np.c_[blobs_dog, blob2]

    return blobs_dog

def colorDeconv(img):
    normalizer = staintools.StainNormalizer(method='macenko')
    stain_matrix = normalizer.extractor.get_stain_matrix(img)
    conc = get_concentrations(img, stain_matrix)
    conc = np.reshape(conc,img.shape[0:2]+(2,))

    return conc



class Plugin(SlideRunnerPlugin.SlideRunnerPlugin):
    version = 0.1
    shortName = 'Object Detection Results'
    inQueue = Queue()
    outQueue = Queue()
    initialOpacity=1.0
    updateTimer=0.1
    outputType = SlideRunnerPlugin.PluginOutputType.RGB_IMAGE
    description = 'Show unpickled object detection results'
    pluginType = SlideRunnerPlugin.PluginTypes.WHOLESLIDE_PLUGIN
    configurationList = list((
                            SlideRunnerPlugin.FilePickerConfigurationEntry(uid='file', name='Result file', mask='*.p'),
                            SlideRunnerPlugin.PluginConfigurationEntry(uid='threshold', name='Detection threshold', initValue=0.5, minValue=0.0, maxValue=1.0),
                            ))
    
    annotationLabels = {'Detection' : SlideRunnerPlugin.PluginAnnotationLabel(0,'Detection', [0,255,0,255]),}

    def __init__(self, statusQueue:Queue):
        self.statusQueue = statusQueue
        self.p = Thread(target=self.queueWorker, daemon=True)
        self.p.start()
        
        pass

    def getAnnotationUpdatePolicy():
          # This is important to tell SlideRunner that he needs to update for every change in position.
          return SlideRunnerPlugin.AnnotationUpdatePolicy.UPDATE_ON_SLIDE_CHANGE


    def queueWorker(self):
        debugModule= False
        quitSignal = False
        oldFilename = ''
        oldArchive = ''
        while not quitSignal:
            job = SlideRunnerPlugin.pluginJob(self.inQueue.get())

            if (job.jobDescription == SlideRunnerPlugin.JobDescription.QUIT_PLUGIN_THREAD):
                # signal to exit this thread
                quitSignal=True
                continue
            
            if (job.configuration['file'] == oldArchive):
                continue
            
            if not (os.path.exists(job.configuration['file'])):
                continue
            
            oldArchive = job.configuration['file']
            self.resultsArchive = pickle.load(open(oldArchive,'rb'))

            pname,fname = os.path.split(job.slideFilename)
            if (oldFilename is not fname):
                # process slide
                if (fname not in self.resultsArchive):
                    self.setMessage('Slide '+str(fname)+' not found in results file.')
                    continue
                
                oldFilename=fname

            self.annos = list()
            for idx in range(len(self.resultsArchive[fname])):
                    row = self.resultsArchive[fname][idx]
                    if (row[5]>job.configuration['threshold']):
                        myanno = annotations.rectangularAnnotation(uid=idx, x1=row[0], x2=row[2], y1=row[1], y2=row[3], text='%.2f' % row[5], pluginAnnotationLabel=self.annotationLabels['Detection'])                
                        self.annos.append(myanno)


            self.updateAnnotations()
            self.setProgressBar(-1)
            self.setMessage('found %d annotations.' % len(self.annos))



    def getAnnotations(self):
        return self.annos


    def getAnnotationLabels(self):
            # sending default annotation labels
            return [self.annotationLabels[k] for k in self.annotationLabels.keys()]

        