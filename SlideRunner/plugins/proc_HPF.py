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

        This plugin will annotate the size of a single high-power-field (0.237mm2) [1]
        in the digital slide.

        1: Meuten et al., 2016: Mitotic Count and the Field of View Area, Vet. Path. 53(1):7-9


"""

import SlideRunner.general.SlideRunnerPlugin as SlideRunnerPlugin
from queue import Queue
import threading
import openslide
import numpy as np
from threading import Thread


class Plugin(SlideRunnerPlugin.SlideRunnerPlugin): 
    version = 0.0
    shortName = 'High Power Field Visualization'
    inQueue = Queue()
    outQueue = Queue()
    description = 'Display size of 1 HPF'
    pluginType = SlideRunnerPlugin.PluginTypes.WHOLESLIDE_PLUGIN
    outputType = SlideRunnerPlugin.PluginOutputType.NO_OVERLAY
    modelInitialized=False
    updateTimer=0.1
    slideFilename = None
    annos = list()
    configurationList = list((SlideRunnerPlugin.PluginConfigurationEntry(uid=0, name='Re-center HPF', ctype=SlideRunnerPlugin.PluginConfigurationType.PUSHBUTTON),
                              SlideRunnerPlugin.PluginConfigurationEntry(uid=1, name='Number of HPFs', initValue=1.00, minValue=1.0, maxValue=10.0),
                              SlideRunnerPlugin.PluginConfigurationEntry(uid=2, name='Size of HPF (mm2)', initValue=0.237, minValue=0.20, maxValue=0.3),)) #0.237
    
    def __init__(self, statusQueue:Queue):
        self.statusQueue = statusQueue
        self.p = Thread(target=self.queueWorker, daemon=True)
        self.p.start()
        
        
        pass

    def getAnnotationUpdatePolicy():
          # This is important to tell SlideRunner that he needs to update for every change in position.
          return SlideRunnerPlugin.AnnotationUpdatePolicy.UPDATE_ON_SLIDE_CHANGE

    def queueWorker(self):

        quitSignal=False
        while not quitSignal:
            job = SlideRunnerPlugin.pluginJob(self.inQueue.get())
            filename = job

            if (job.jobDescription == SlideRunnerPlugin.JobDescription.QUIT_PLUGIN_THREAD):
                # signal to exit this thread
                quitSignal=True
                continue


            self.processWholeSlide(job)

    def getAnnotations(self):
        return self.annos

    def processWholeSlide(self, job : SlideRunnerPlugin.pluginJob):

        filename = job.slideFilename
        self.slide = openslide.open_slide(filename)


        # 1 HPF = 0.237 mm^2 
        A = job.configuration[2] # mm^2 
        W_hpf_microns = np.sqrt(A*4/3) * 1000 # in microns
        H_hpf_microns = np.sqrt(A*3/4) * 1000 # in microns

        micronsPerPixel = self.slide.properties[openslide.PROPERTY_NAME_MPP_X]

        W_hpf = int(W_hpf_microns / float(micronsPerPixel)) * np.sqrt(float(int(job.configuration[1]))) 
        H_hpf = int(H_hpf_microns / float(micronsPerPixel)) * np.sqrt(float(int(job.configuration[1])))

        center = (int((job.coordinates[0]+0.5*job.coordinates[2])),
                  int((job.coordinates[1]+0.5*job.coordinates[3])))

        self.annos = list()
        if (int(job.configuration[1])==1):
            myanno = SlideRunnerPlugin.rectangularAnnotation(center[0]-W_hpf/2, center[1]-H_hpf/2, center[0]+W_hpf/2, center[1]+H_hpf/2, 'High-Power Field')
        else:
            myanno = SlideRunnerPlugin.rectangularAnnotation(center[0]-W_hpf/2, center[1]-H_hpf/2, center[0]+W_hpf/2, center[1]+H_hpf/2, '%d High-Power Fields' %  int(job.configuration[1]))
        self.annos.append(myanno)

        self.updateAnnotations()

 