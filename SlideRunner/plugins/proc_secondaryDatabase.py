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
	    Visualize secondary database 

"""

import SlideRunner.general.SlideRunnerPlugin as SlideRunnerPlugin
import queue
from threading import Thread
from queue import Queue
import cv2
import os
import numpy as np
import matplotlib.pyplot as plt 
import matplotlib.colors
import pickle
import SlideRunner.dataAccess.annotations as annotations 
import matplotlib.path as path
from SlideRunner.dataAccess.database import Database


class Plugin(SlideRunnerPlugin.SlideRunnerPlugin):
    version = 0.1
    shortName = 'Secondary database visualization'
    inQueue = Queue()
    outQueue = Queue()
    initialOpacity=1.0
    updateTimer=0.1
    outputType = SlideRunnerPlugin.PluginOutputType.RGB_IMAGE
    description = 'Visualize secondary SlideRunner database'
    pluginType = SlideRunnerPlugin.PluginTypes.WHOLESLIDE_PLUGIN
    configurationList = list((
                            SlideRunnerPlugin.FilePickerConfigurationEntry(uid='file', name='Database file', mask='*.sqlite'),
                            ))
    
    COLORS = [[0,128,0,255],
              [128,0,0,255],
              [0,0,128,255],
              [128,128,0,255],
              [0,128,128,255],
              [128,128,128,255]]

    def __init__(self, statusQueue:Queue):
        self.statusQueue = statusQueue
        self.annotationLabels = {}
        self.secondaryDB = Database()
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
        oldSlide = ''
        oldThres=-1
        while not quitSignal:
            job = SlideRunnerPlugin.pluginJob(self.inQueue.get())
            print(job)

            if (job.jobDescription == SlideRunnerPlugin.JobDescription.QUIT_PLUGIN_THREAD):
                # signal to exit this thread
                quitSignal=True
                continue
            
            if (job.configuration['file'] == oldArchive) and (job.slideFilename == oldSlide):
                continue
            
            if not (os.path.exists(job.configuration['file'])):
                continue
            self.sendAnnotationLabelUpdate()

            oldArchive = job.configuration['file']
            oldSlide = job.slideFilename

            self.secondaryDB.open(oldArchive)

            self.annos = list()
            self.annotationLabels = dict()

            for key, (label, annoId) in enumerate(self.secondaryDB.getAllClasses()):
                self.annotationLabels[annoId] = SlideRunnerPlugin.PluginAnnotationLabel(0,'%s' % label, self.COLORS[key % len(self.COLORS)])
            
            pname,fname = os.path.split(job.slideFilename)
            self.slideUID = self.secondaryDB.findSlideWithFilename(fname,pname)
            self.secondaryDB.loadIntoMemory(self.slideUID)
            self.annos = list()

            for annoId in self.secondaryDB.annotations.keys():
                anno = self.secondaryDB.annotations[annoId]
                anno.pluginAnnotationLabel = self.annotationLabels[anno.agreedClass]
                self.annos.append(anno)
            self.sendAnnotationLabelUpdate()

            self.updateAnnotations()
            self.setProgressBar(-1)
            self.setMessage('found %d annotations.' % len(self.annos))



    def getAnnotations(self):
        return self.annos


    def getAnnotationLabels(self):
            # sending default annotation labels
            return [self.annotationLabels[k] for k in self.annotationLabels.keys()]

        
