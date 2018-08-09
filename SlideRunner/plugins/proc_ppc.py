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
import numpy as np
import matplotlib.pyplot as plt 



class Plugin(SlideRunnerPlugin.SlideRunnerPlugin):
    version = 0.1
    shortName = 'Positive Pixel Count (Aperio)'
    inQueue = Queue()
    outQueue = Queue()
    initialOpacity=1.0
    outputType = SlideRunnerPlugin.PluginOutputType.RGB_IMAGE
    description = 'H&E Image normalization (Method by Macenko)'
    pluginType = SlideRunnerPlugin.PluginTypes.IMAGE_PLUGIN
    configurationList = list((SlideRunnerPlugin.PluginConfigurationEntry(uid=0, name='Hue value', initValue=0.04, minValue=0.0, maxValue=1.0),
                            SlideRunnerPlugin.PluginConfigurationEntry(uid=1, name='Hue width', initValue=0.08, minValue=0.0, maxValue=1.0),
                            SlideRunnerPlugin.PluginConfigurationEntry(uid=2, name='Saturation threshold', initValue=0.2, minValue=0.0, maxValue=1.0),
                            SlideRunnerPlugin.PluginConfigurationEntry(uid=3, name='Weak Upper', initValue=220, minValue=0.0, maxValue=255.0),
                            SlideRunnerPlugin.PluginConfigurationEntry(uid=4, name='Medium Upper = Weak Lower', initValue=175, minValue=0.0, maxValue=255.0),
                            SlideRunnerPlugin.PluginConfigurationEntry(uid=5, name='Strong Upper = Medium Lower', initValue=100, minValue=0.0, maxValue=255.0),
                            SlideRunnerPlugin.PluginConfigurationEntry(uid=6, name='Strong Lower', initValue=0, minValue=0.0, maxValue=255.0)))
    
    def __init__(self, statusQueue:Queue):
        self.statusQueue = statusQueue
        self.p = Thread(target=self.queueWorker, daemon=True)
        self.p.start()
        
        pass

    def queueWorker(self):
        debugModule= False
        quitSignal = False
        while not quitSignal:
            job = SlideRunnerPlugin.pluginJob(self.inQueue.get())
            image = job.currentImage

            if (job.jobDescription == SlideRunnerPlugin.JobDescription.QUIT_PLUGIN_THREAD):
                # signal to exit this thread
                quitSignal=True
                continue

            rgb = np.copy(image[:,:,0:3])

            # Convert to HSV
            hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)

            img_hsv = np.reshape(hsv, [-1,3])

            if (debugModule):
                plt.clf()
                plt.hist(img_hsv[:,0]/255.0,255)
                plt.savefig('histo.pdf')

            HUE_VALUE = job.configuration[0]
            HUE_RANGE = job.configuration[1]
            SAT_THRESHOLD = job.configuration[2]
            hsv = np.float32(hsv)/255.0
            hue = hsv[:,:,0]
            sat = hsv[:,:,1]
            val = hsv[:,:,2]*255.0
            hue_masked = (hue > (HUE_VALUE-HUE_RANGE)) & (hue < (HUE_VALUE+HUE_RANGE) ) 

            if (HUE_VALUE-HUE_RANGE) < 0.0:
                hue_masked += (hue > (HUE_VALUE-HUE_RANGE)+1.0)
            if (HUE_VALUE+HUE_RANGE) > 1.0:
                hue_masked += (hue < (HUE_VALUE-HUE_RANGE)-1.0)
            sat_masked = (hsv[:,:,1]>SAT_THRESHOLD)

            if (debugModule):
                plt.clf()
                plt.hist(val[sat_masked & hue_masked],255)
                plt.savefig('histo_val.pdf')

            strong = (val>job.configuration[6]) & (val<=job.configuration[5]) & sat_masked & hue_masked
            medium = (val>job.configuration[5]) & (val<=job.configuration[4])  & sat_masked & hue_masked
            weak = (val>job.configuration[4]) & (val<=job.configuration[3])  & sat_masked & hue_masked

            # strong: Red
            rgb[strong,0] = 255.0
            rgb[strong,1] = 0.0
            rgb[strong,2] = 0.0

            # medium: Orange
            rgb[medium,0] = 255.0
            rgb[medium,1] = 84.0
            rgb[medium,2] = 33.0

            # weak: Yellow
            rgb[weak,0] = 255.0
            rgb[weak,1] = 255.0
            rgb[weak,2] = 0.0
            
            img_hsv = np.reshape(hsv[hue_masked&sat_masked], [-1,3])

            if (debugModule):
                plt.clf()
                plt.hist(img_hsv[:,0],255)
                plt.savefig('histo_limited.pdf')

            self.returnImage(np.float32(rgb))
            self.statusQueue.put((1, 'PPC: Total: %d    Weak: %d   Medium: %d   Strong: %d ' % (np.prod(rgb.shape[0:2]),np.sum(weak),np.sum(medium),np.sum(strong)) ))



        