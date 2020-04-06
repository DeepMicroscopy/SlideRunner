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
	   Visualize bounding boxes (object detection results)

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


class Plugin(SlideRunnerPlugin.SlideRunnerPlugin):
    version = 0.1
    shortName = 'Object Detection Results'
    inQueue = Queue()
    outQueue = Queue()
    initialOpacity=1.0
    updateTimer=0.1
    outputType = SlideRunnerPlugin.PluginOutputType.NO_OVERLAY
    description = 'Show unpickled object detection results'
    pluginType = SlideRunnerPlugin.PluginTypes.WHOLESLIDE_PLUGIN
    configurationList = list((
                            SlideRunnerPlugin.FilePickerConfigurationEntry(uid='file', name='Result file', mask='*.p;;*.txt'),
                            SlideRunnerPlugin.PluginConfigurationEntry(uid='threshold', name='Detection threshold', initValue=0.75, minValue=0.0, maxValue=1.0),
                            ))
    
    COLORS = [[0,128,0,255],
              [128,0,0,255],
              [0,0,128,255],
              [128,128,0,255],
              [0,128,128,255],
              [128,128,128,255]]

    def __init__(self, statusQueue:Queue):
        self.statusQueue = statusQueue
        self.annotationLabels = {'Detection' : SlideRunnerPlugin.PluginAnnotationLabel(0,'Detection', [0,180,0,255]),}
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
            print(job.configuration)

            if (job.jobDescription == SlideRunnerPlugin.JobDescription.QUIT_PLUGIN_THREAD):
                # signal to exit this thread
                quitSignal=True
                continue
            
            if (job.configuration['file'] == oldArchive) and (job.configuration['threshold'] == oldThres) and (job.slideFilename == oldSlide):
                continue
            
            if not (os.path.exists(job.configuration['file'])):
                continue

            print('Performing label update')
            self.sendAnnotationLabelUpdate()

            oldArchive = job.configuration['file']
            oldThres = job.configuration['threshold']
            oldSlide = job.slideFilename
            [foo,self.ext] = os.path.splitext(oldArchive)
            self.ext = self.ext.upper()

            self.annos = list()

            if (self.ext=='.P'): # Pickled format - results for many slides
                self.resultsArchive = pickle.load(open(oldArchive,'rb'))

                pname,fname = os.path.split(job.slideFilename)
                fnamewithfolder = pname.split(os.sep)[-1] + os.sep + fname
                if (oldFilename is not fname):
                    # process slide
                    if (fname not in self.resultsArchive) and (fnamewithfolder not in self.resultsArchive):
                        self.setMessage('Slide '+str(fname)+' not found in results file.')
                        print('List is:',self.resultsArchive.keys())
                        continue
                    
                    if (fnamewithfolder in self.resultsArchive):
                        fname=fnamewithfolder
                    oldFilename=fname


                uniqueLabels = np.unique(np.array(self.resultsArchive[fname])[:,4])

                self.annotationLabels = dict()
                for key,label in enumerate(uniqueLabels):
                     self.annotationLabels[label] =  SlideRunnerPlugin.PluginAnnotationLabel(key, 'Class %d' % label, self.COLORS[key % len(self.COLORS)])

                for idx in range(len(self.resultsArchive[fname])):
                        row = self.resultsArchive[fname][idx]
                        if (row[5]>job.configuration['threshold']):
                            myanno = annotations.rectangularAnnotation(uid=idx, x1=row[0], x2=row[2], y1=row[1], y2=row[3], text='%.2f' % row[5], pluginAnnotationLabel=self.annotationLabels[row[4]])                
                            self.annos.append(myanno)

                self.sendAnnotationLabelUpdate()


            elif (self.ext=='.TXT'): # Assume MS Coco format
                self.resultsArchive = np.loadtxt(oldArchive, dtype={'names': ('label', 'confidence', 'x','y','w','h'), 'formats': ('U30', 'f4', 'i4','i4','i4','i4')}, skiprows=0, delimiter=' ')
                uniqueLabels = np.unique(self.resultsArchive['label'])

                self.annotationLabels = dict()
                for key,label in enumerate(uniqueLabels):
                     self.annotationLabels[label] =  SlideRunnerPlugin.PluginAnnotationLabel(key, label, self.COLORS[key % len(self.COLORS)])

                self.sendAnnotationLabelUpdate()

                for idx in range(len(self.resultsArchive)):
                        row = self.resultsArchive[idx]
                        if (row[5]>job.configuration['threshold']):
                            myanno = annotations.rectangularAnnotation(uid=idx, x1=row['x'], y1=row['y'], x2=row['x']+row['w'], y2=row['y']+row['h'], text='%.2f' % row['confidence'], pluginAnnotationLabel=self.annotationLabels[row['label']])                
                            self.annos.append(myanno)



            self.updateAnnotations()
            self.setProgressBar(-1)
            self.setMessage('found %d annotations.' % len(self.annos))



    def getAnnotations(self):
        return self.annos


    def getAnnotationLabels(self):
            # sending default annotation labels
            return [self.annotationLabels[k] for k in self.annotationLabels.keys()]

        
