import SlideRunner.general.SlideRunnerPlugin as SlideRunnerPlugin
import queue
from threading import Thread
from queue import Queue
import cv2
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors
import h5py
import openslide


class Plugin(SlideRunnerPlugin.SlideRunnerPlugin):
    version = 0.1
    shortName = 'WSI Classification Overlay'
    inQueue = Queue()
    outQueue = Queue()
    initialOpacity = 0.6
    updateTimer = 0.1
    outputType = SlideRunnerPlugin.PluginOutputType.RGB_OVERLAY
    description = 'Visualize classification results'
    pluginType = SlideRunnerPlugin.PluginTypes.WHOLESLIDE_PLUGIN
    configurationList = list((
        SlideRunnerPlugin.FilePickerConfigurationEntry(uid='file', name='Result file', mask='*.hdf5'),
    ))


    COLORS = [[255, 255, 255, 0], #[0, 0, 0, 125], # Non-Neoplastic
              [255, 128, 0, 255], # Melanoma
              [0, 96, 0, 255], # Plasmacytoma
              [0, 255, 0, 255], # Mast Cell Tumor
              [0, 0, 255, 255], # PNST
              [255, 0, 0, 255], # SCC
              [128, 0, 255, 255], # Trichoblastoma
              [0, 255, 255, 255], # Histiocytoma
              [255, 255, 255, 0]] # BG


    def __init__(self, statusQueue: Queue):
        self.statusQueue = statusQueue
        self.p = Thread(target=self.queueWorker, daemon=True)
        self.p.start()
        pass

    def getAnnotationUpdatePolicy():
          # This is important to tell SlideRunner that he needs to update for every change in position.
          return SlideRunnerPlugin.AnnotationUpdatePolicy.UPDATE_ON_SCROLL_CHANGE

    def queueWorker(self):
        quitSignal = False
        oldArchive = ''
        oldSlide = ''
        oldCoordinates = [-1, -1, -1, -1]
        while not quitSignal:
            job = SlideRunnerPlugin.pluginJob(self.inQueue.get())
            print(job)
            print(job.configuration)

            if (job.jobDescription == SlideRunnerPlugin.JobDescription.QUIT_PLUGIN_THREAD):
                # signal to exit this thread
                quitSignal = True
                continue

            if (job.configuration['file'] == oldArchive) and (job.slideFilename == oldSlide) and np.all(
                    job.coordinates == oldCoordinates):
                continue

            if not (os.path.exists(job.configuration['file'])):
                continue

            fileChanged = job.configuration['file'] != oldArchive
            slideChanged = job.slideFilename != oldSlide

            oldArchive = job.configuration['file']
            oldSlide = job.slideFilename
            oldCoordinates = job.coordinates

            self.slideObj = openslide.open_slide(job.slideFilename)
            #self.ds = 4

            if (fileChanged):
                self.resultsArchive = h5py.File(oldArchive, "r")
                self.downsampledMap = self.resultsArchive["classification"]
                self.factor = int(self.slideObj.dimensions[0] / self.downsampledMap.shape[1])
                self.scaleX = ((job.coordinates[2]) / job.currentImage.shape[1])
                self.scaleY = ((job.coordinates[3]) / job.currentImage.shape[0])
                print('Opened results container.')
                print('Downsampled image: ', self.downsampledMap.shape)


            if slideChanged:
                self.slideObj = openslide.open_slide(job.slideFilename)


            print('returning overlay...')
            current_shape = np.array(job.currentImage).shape
            coords_overlay = np.int16(np.array(job.coordinates)/self.factor)
            image = self.downsampledMap[
                    max(coords_overlay[1], 0):min(coords_overlay[1] + coords_overlay[3], self.downsampledMap.shape[0]),
                    max(coords_overlay[0], 0):min(coords_overlay[0] + coords_overlay[2],
                                                  self.downsampledMap.shape[1])]
            image = np.asarray([self.COLORS[i] for i in np.int16(image.flatten())],dtype=np.uint8).\
                reshape((image.shape[0], image.shape[1], -1))
            image = cv2.copyMakeBorder(image,np.abs(min(0, coords_overlay[1])),0,np.abs(min(0, coords_overlay[0])),0,cv2.BORDER_CONSTANT,value=(0,0,0,255))
            image = cv2.copyMakeBorder(image,0,max(0,coords_overlay[3]-image.shape[0]),0,max(0,coords_overlay[2]-image.shape[1]),cv2.BORDER_CONSTANT,value=(0,0,0,255))
            image = cv2.resize(image, dsize=(current_shape[1], current_shape[0]), interpolation=cv2.INTER_NEAREST)
            image = np.float32(image[:, :, 0:3])
            image[image == [255, 255, 255]] = np.array(job.currentImage)[:, :, :3][image == [255, 255, 255]]
            self.returnImage(image)
