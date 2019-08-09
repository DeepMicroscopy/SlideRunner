import SlideRunner.general.SlideRunnerPlugin as SlideRunnerPlugin
import queue
from threading import Thread
from queue import Queue
import cv2
import numpy as np
import time
import pickle
from fastai import *
from fastai.vision import *
import SlideRunner.dataAccess.annotations as annotations
import torchvision.transforms as transforms

class Plugin(SlideRunnerPlugin.SlideRunnerPlugin):
    version = 0.1
    shortName = 'FastAi CAM Vessel segmentation'
    inQueue = Queue()
    outQueue = Queue()
    updateTimer = 0.5
    outputType = SlideRunnerPlugin.PluginOutputType.RGB_IMAGE
    description = 'Load a FastAi segmentation model and performe inference'
    pluginType = SlideRunnerPlugin.PluginTypes.IMAGE_PLUGIN
    configurationList = list((SlideRunnerPlugin.FilePickerConfigurationEntry(uid='file', name='Model file', mask='*.pth'), #, mask='*.p;*.txt'
                              SlideRunnerPlugin.PluginConfigurationEntry(uid='threshold', name='Detection threshold',
                                                                         initValue=0.5, minValue=0.0, maxValue=1.0),
    ))

    def __init__(self, statusQueue: Queue):
        self.statusQueue = statusQueue
        self.p = Thread(target=self.queueWorker, daemon=True)
        self.p.start()

        valid = SegmentationItemList([])
        train = SegmentationItemList([])
        item_list = ItemLists(Path('.'), train, valid)
        item_list = item_list.label_from_func(lambda x:x, classes=['Bg', 'Vessel'], label_cls=SegmentationLabelList)
        data = item_list.transform([], size=512, tfm_y=True)
        data = data.databunch(bs=6, num_workers=6)

        self.learn = unet_learner(data, models.resnet18)

        self.mean = [0.7946, 0.7417, 0.6971] #mean
        self.std = [0.2619, 0.3365, 0.3751] #std
        self.shape = (512, 512)

        self.annos = []


        COLORS = [[0, 128, 0, 255],
                  [128, 0, 0, 255],
                  [0, 0, 128, 255],
                  [128, 128, 0, 255],
                  [0, 128, 128, 255],
                  [128, 128, 128, 255]]

        self.annotationLabels = {
            'Vessel': SlideRunnerPlugin.PluginAnnotationLabel(0, 'Vessel', [255, 0, 0, 255]), }

        self.sendAnnotationLabelUpdate()

        pass


    def getAnnotationUpdatePolicy():
          # This is important to tell SlideRunner that he needs to update for every change in position.
          return SlideRunnerPlugin.AnnotationUpdatePolicy.UPDATE_ON_SLIDE_CHANGE


    def queueWorker(self):
        quitSignal = False
        oldModelName = ''
        oldSlide = ''
        lastPosition = None
        id = 0

        while not quitSignal:
            job = SlideRunnerPlugin.pluginJob(self.inQueue.get())
            image = job.currentImage

            if (job.jobDescription == SlideRunnerPlugin.JobDescription.QUIT_PLUGIN_THREAD):
                # signal to exit this thread
                quitSignal = True
                continue

            if job.configuration['file'] is "" or lastPosition == job.coordinates:
                continue

            if (job.configuration['file'] != oldModelName):
                self.learn = self.learn.load(job.configuration['file'].replace(".pth",""))
                oldModelName = job.configuration['file']

            lastPosition = job.coordinates
            self.annos = list()
            image = image[:, :, :3]
            input_shape = image.shape[:2]

            image = cv2.resize(image, self.shape)
            patch = pil2tensor(image / 255., np.float32)
            patch = transforms.Normalize(self.mean, self.std)(patch)
            image = Image(patch)
            with torch.no_grad():
                start = time.time()
                segment, t2, pred = self.learn.predict(image)
                end = time.time()

            threshold = job.configuration['threshold']

            # set pixels < threshold to zero
            #pred[:, 1][pred[:, 1] < threshold] = 0

            pred = pred.argmax(dim=0)[None]
            pred = cv2.resize(to_np(pred).astype(np.uint8).reshape(self.shape), input_shape[:: -1])

            _, contours, _ = cv2.findContours(pred.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            scaleX = (job.coordinates[2]) / job.currentImage.shape[1]
            scaleY = (job.coordinates[3]) / job.currentImage.shape[0]

            for (i, c) in enumerate(contours):
                points = np.array([((point[0][0] * scaleX) + job.coordinates[0], (point[0][1] * scaleY)  + job.coordinates[1])
                                   for point in c], dtype=np.int)
                myanno = annotations.polygonAnnotation(uid=i+id, coordinates=points, text="conf: {}".format(1),
                                                       pluginAnnotationLabel=self.annotationLabels['Vessel'])
                self.annos.append(myanno)

                id += 1


            self.updateAnnotations()
            self.setProgressBar(-1)
            self.setMessage('found %d annotations.' % len(self.annos))



    def getAnnotations(self):
        return self.annos


    def getAnnotationLabels(self):
            # sending default annotation labels
            return [self.annotationLabels[k] for k in self.annotationLabels.keys()]