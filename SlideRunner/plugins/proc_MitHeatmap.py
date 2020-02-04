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
	   Visualize Mitotic figure density (mitotic count) (object detection results)

"""

import SlideRunner.general.SlideRunnerPlugin as SlideRunnerPlugin
import queue
from threading import Thread
from queue import Queue
import cv2
import bz2
import os
import numpy as np
import matplotlib.pyplot as plt 
import matplotlib.colors
import pickle
import SlideRunner.dataAccess.annotations as annotations 
from SlideRunner.dataAccess.database import Database
import matplotlib.path as path
import openslide

class Plugin(SlideRunnerPlugin.SlideRunnerPlugin):
    version = 0.1
    shortName = 'Mitosis Heatmap'
    inQueue = Queue()
    outQueue = Queue()
    initialOpacity=0.6
    updateTimer=0.1
    outputType = SlideRunnerPlugin.PluginOutputType.BINARY_MASK
    description = 'Show heatmap of mitotic figures in WSI'
    pluginType = SlideRunnerPlugin.PluginTypes.WHOLESLIDE_PLUGIN
    configurationList = list((
                            SlideRunnerPlugin.FilePickerConfigurationEntry(uid='file', name='Result file', mask='*.p;;*.txt;;*.p.bz2'),
                            SlideRunnerPlugin.FilePickerConfigurationEntry(uid='dbfile', name='Database file', mask='*.sqlite'),
                            SlideRunnerPlugin.PluginConfigurationEntry(uid='threshold', name='Detection threshold', initValue=0.75, minValue=0.0, maxValue=1.0),
                            SlideRunnerPlugin.ComboboxPluginConfigurationEntry(uid='source', name='Heatmap shows',options=['Primary Database', 'Results','SecondaryDatabase'])
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
        self.annos = []
        self.downsampledMap = np.zeros((10,10))


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
        oldDBfile = ''
        oldCoordinates = [-1,-1,-1,-1]
        oldThres=-1
        oldSource=-1
        self.ds=32
        while not quitSignal:
            job = SlideRunnerPlugin.pluginJob(self.inQueue.get())
            print(job)
            print(job.configuration)

            if (job.jobDescription == SlideRunnerPlugin.JobDescription.QUIT_PLUGIN_THREAD):
                # signal to exit this thread
                quitSignal=True
                continue
            
            sourceChanged = job.configuration['source'] != oldSource
            if (job.configuration['source']==0):
                if not hasattr(job.openedDatabase, 'dbfilename'):
                    # DB not open yet
                    continue
                job.configuration['dbfile'] = job.openedDatabase.dbfilename
            
            dbfilechanged = job.configuration['dbfile'] != oldDBfile

            if not(sourceChanged) and (job.configuration['file'] == oldArchive) and (job.configuration['threshold'] == oldThres) and (job.slideFilename == oldSlide) and np.all(job.coordinates == oldCoordinates) and not(dbfilechanged):
                continue
            
            if not (os.path.exists(job.configuration['file'])) and (job.configuration['source']==1):
                continue
            self.sendAnnotationLabelUpdate()

            fileChanged = job.configuration['file'] != oldArchive
            oldDBfile = job.configuration['dbfile']
            slideChanged = job.slideFilename != oldSlide
            thresChanged = job.configuration['threshold'] != oldThres

            oldArchive = job.configuration['file']
            oldThres = job.configuration['threshold']
            oldSlide = job.slideFilename
            oldSource = job.configuration['source']
            oldCoordinates = job.coordinates
            [foo,self.ext] = os.path.splitext(oldArchive)
            self.ext = self.ext.upper()
            self.slideObj = openslide.open_slide(job.slideFilename)

            if (fileChanged):
                if (self.ext=='.P') or (self.ext=='.BZ2'): # Pickled format - results for many slides
                    if (self.ext=='.BZ2'):
                        self.resultsArchive = pickle.load(bz2.BZ2File(oldArchive, 'rb'))
                        print('Opened bz2-compressed results container.')
                    else:
                        self.resultsArchive = pickle.load(open(oldArchive,'rb'))

            print('Sourcechanged:',sourceChanged,'dbfilechanged:',dbfilechanged,(len(job.configuration['dbfile'])>0))
            if (sourceChanged or dbfilechanged or slideChanged) and ((job.configuration['source']==2) or (job.configuration['source']==0) ) and (len(job.configuration['dbfile'])>0):
                    self.slideObj = openslide.open_slide(job.slideFilename)
                    self.downsampledMap = np.zeros((int(self.slideObj.dimensions[1]/self.ds), int(self.slideObj.dimensions[0]/self.ds)))
                    self.newDB = Database()

                    self.newDB.open(job.configuration['dbfile'])
                    allClasses = self.newDB.getAllClasses()
                    mitosisClass=-1
                    for clsname,clsuid,col in allClasses:
                        if (mitosisClass==-1) and ('MITO' in clsname.upper()) and ('LOOK' not in clsname.upper()):
                            mitosisClass=clsuid

                    pname,fname = os.path.split(job.slideFilename)
                    uid = self.newDB.findSlideWithFilename(fname,pname)
                    self.newDB.loadIntoMemory(uid)
                    for anno in self.newDB.annotations:
                        if (self.newDB.annotations[anno].agreedClass==mitosisClass):
                            annodet = self.newDB.annotations[anno]
                            self.downsampledMap[int(annodet.y1/self.ds),int(annodet.x1/self.ds)] += 1
                            
                    else:
                        self.setMessage('No DB open.') 

            if ((sourceChanged and job.configuration['source']==1) or (slideChanged) or (thresChanged)) and len(job.configuration['file'])>0:
                pname,fname = os.path.split(job.slideFilename)
                print('Stage 6')
                if (oldFilename is not fname) or (slideChanged):
                    # process slide
                    self.annos = list()

                    if (fname not in self.resultsArchive):
                        self.setMessage('Slide '+str(fname)+' not found in results file.')
                        print('List of files is: ',self.resultsArchive.keys())
                        continue
                        
                        oldFilename=fname


                    uniqueLabels = np.unique(np.array(self.resultsArchive[fname])[:,4])

                    self.annotationLabels = dict()
                    for key,label in enumerate(uniqueLabels):
                        self.annotationLabels[label] =  SlideRunnerPlugin.PluginAnnotationLabel(0,'Class %d' % label, self.COLORS[key % len(self.COLORS)])

                    if (job.configuration['source']==1):
                        self.downsampledMap = np.zeros((int(self.slideObj.dimensions[1]/self.ds), int(self.slideObj.dimensions[0]/self.ds)))
                    print('Downsampled image: ',self.downsampledMap.shape)

                    for idx in range(len(self.resultsArchive[fname])):
                            row = self.resultsArchive[fname][idx]
                            if (row[5]>job.configuration['threshold']):
                                myanno = annotations.rectangularAnnotation(uid=idx, x1=row[0], x2=row[2], y1=row[1], y2=row[3], text='%.2f' % row[5], pluginAnnotationLabel=self.annotationLabels[row[4]])                
                                if (job.configuration['source']==1):
                                    self.downsampledMap[int((row[1]+row[3])/2/self.ds),int((row[0]+row[2])/2/self.ds)] += 1
                                self.annos.append(myanno)

                    self.sendAnnotationLabelUpdate()


                elif (self.ext=='.TXT'): # Assume MS Coco format
                    self.annos = list()

                    self.resultsArchive = np.loadtxt(oldArchive, dtype={'names': ('label', 'confidence', 'x','y','w','h'), 'formats': ('U30', 'f4', 'i4','i4','i4','i4')}, skiprows=0, delimiter=' ')
                    uniqueLabels = np.unique(self.resultsArchive['label'])

                    self.annotationLabels = dict()
                    for key,label in enumerate(uniqueLabels):
                        self.annotationLabels[label] =  SlideRunnerPlugin.PluginAnnotationLabel(0,label, self.COLORS[key % len(self.COLORS)])

                    self.sendAnnotationLabelUpdate()

                    self.slideObj = openslide.open_slide(job.slideFilename)
                    self.ds = 32
                    if (job.configuration['source']==1):
                        self.downsampledMap = np.zeros((int(self.slideObj.dimensions[1]/self.ds), int(self.slideObj.dimensions[0]/self.ds)))
                    print('Downsampled image: ',self.downsampledMap.shape)


                    for idx in range(len(self.resultsArchive)):
                            row = self.resultsArchive[idx]
                            if (row[5]>job.configuration['threshold']):
                                if (job.configuration['source']==1):
                                    self.downsampledMap[int((row['y']-row['h']/2)/self.ds),int((row['x']-row['w']/2)/self.ds)] += 1

                                myanno = annotations.rectangularAnnotation(uid=idx, x1=row['x'], x2=row['y'], y1=row['x']+row['w'], y2=row['y']+row['h'], text='%.2f' % row['confidence'], pluginAnnotationLabel=self.annotationLabels[row['label']])                
                                self.annos.append(myanno)

            print('returning overlay...')
            A = 2.37 # mm^2
            W_hpf_microns = np.sqrt(A*4/3) * 1000 # in microns
            H_hpf_microns = np.sqrt(A*3/4) * 1000 # in microns

            micronsPerPixel = self.slideObj.properties[openslide.PROPERTY_NAME_MPP_X]

            W_hpf = int(W_hpf_microns / float(micronsPerPixel))
            H_hpf = int(H_hpf_microns / float(micronsPerPixel))

            W_x = int(W_hpf / self.ds)
            W_y = int(H_hpf / self.ds)
            kernel = np.ones((W_y,W_x),np.float32)
            mitoticCount = cv2.filter2D(self.downsampledMap, -1, kernel )

            coords_ds = np.int16(np.array(job.coordinates)/self.ds)

            centerImg = cv2.getRectSubPix(np.float32(mitoticCount[:,:,None]), patchSize=(coords_ds[2], coords_ds[3]), center=(coords_ds[0]+coords_ds[2]*0.5,coords_ds[1]+coords_ds[3]*0.5))
            
            resized = cv2.resize(centerImg, dsize=(job.currentImage.shape[1], job.currentImage.shape[0]))

            self.returnImage(resized)


            self.updateAnnotations()
            self.setProgressBar(-1)
            self.setMessage('found %d annotations.' % len(self.annos))



    def getAnnotations(self):
        return self.annos


    def getAnnotationLabels(self):
            # sending default annotation labels
            return [self.annotationLabels[k] for k in self.annotationLabels.keys()]

        
