import SlideRunner.general.SlideRunnerPlugin as SlideRunnerPlugin
import queue
from threading import Thread
from queue import Queue
import numpy as np
import openslide
import cv2



class Plugin(SlideRunnerPlugin.SlideRunnerPlugin):
    version = 0.1
    shortName = 'EIPH'
    inQueue = Queue()
    outQueue = Queue()
    updateTimer = 0.5
    outputType = SlideRunnerPlugin.PluginOutputType.RGB_IMAGE
    description = 'EIPH Analysis'
    pluginType = SlideRunnerPlugin.PluginTypes.IMAGE_PLUGIN
    configurationList = list((SlideRunnerPlugin.TablePluginConfigurationEntry(uid=0, name='Test 123'),
                              SlideRunnerPlugin.PluginConfigurationEntry(uid=1, name='Headmap Resolution',
                                                                         initValue=1024, minValue=128,
                                                                         maxValue=8192),))



    def __init__(self, statusQueue: Queue):
        self.statusQueue = statusQueue
        self.p = Thread(target=self.queueWorker, daemon=True)
        self.p.start()

        self.last_slideFilename = None
        self.level_dimension = None
        self.slide = None


        self.headmap_resolution = 1024
        self.overlay = None
        self.classes = {3: 0, 4: 1, 5: 2, 6: 3, 7: 4}

    def queueWorker(self):
        quitSignal = False
        last_annotations_count = 0

        while not quitSignal:
            job = SlideRunnerPlugin.pluginJob(self.inQueue.get())
            #mage = job.currentImage[:, :, :3]

            if (job.jobDescription == SlideRunnerPlugin.JobDescription.QUIT_PLUGIN_THREAD):
                # signal to exit this thread
                quitSignal = True
                continue

            if job.slideFilename != self.last_slideFilename:
                self.slide = openslide.open_slide(job.slideFilename)
                self.level_dimension = self.slide.level_dimensions[0]


            #refresh overview image
            if (len(job.openedDatabase.annotations) != last_annotations_count) or int(job.configuration[1]) != self.headmap_resolution:
                self.overlay = self.create_overlay(job)

            result_dict = self.calculate_eiph_statistics(job)

            self.updateInformation(result_dict)

    def calculate_eiph_statistics(self, job):
        result_dict = {"Golde et al.": 0, "Doucet et al.": 0, "Total": 0, 0: 0, 1: 0, 2: 0, 3: 0, 4: 0, }
        golde_list = []
        total = 0
        for id, annotation in job.openedDatabase.VA.items():
            classId = annotation.labels[0].classId
            if classId in self.classes:
                total += 1
                classId = self.classes[classId]

                result_dict[classId] += 1
                golde_list.append(classId)
        result_dict["Total"] = total
        result_dict["Golde et al."] = '{:f}'.format(np.mean(golde_list))
        # Doucet
        doucet = sum([(result_dict[i] / (total / 100)) * i for i in range(5)])
        result_dict["Doucet et al."] = '{:f}'.format(doucet)
        return result_dict

    def create_overlay(self, job):
        annotations = np.array([[a[1].x1, a[1].y1, a[1].x1 + 2 * a[1].r, a[1].y1 + 2 * a[1].r,
                                 self.classes[a[1].labels[0].classId]] for a in
                                job.openedDatabase.annotations.items()
                                if a[1].labels[0].classId in self.classes])
        self.headmap_resolution = int(job.configuration[1])
        # Wir brauchen noch die original bildgröße
        x_steps = range(0, self.level_dimension[0] - 2 * self.headmap_resolution, int(self.headmap_resolution / 2))
        y_steps = range(0, self.level_dimension[1] - 2 * self.headmap_resolution, int(self.headmap_resolution / 2))
        gt_image = np.zeros(shape=(len(x_steps) + 1, len(y_steps) + 1))
        x_index = 0
        for x in x_steps:
            y_index = 0
            for y in y_steps:
                ids = ((annotations[:, 1]) > x) \
                      & ((annotations[:, 0]) > y) \
                      & ((annotations[:, 3]) < x + self.headmap_resolution) \
                      & ((annotations[:, 2]) < y + self.headmap_resolution)

                score = np.mean(annotations[ids, 4]) if np.count_nonzero(ids) > 1 else 0
                gt_image[x_index, y_index] = score

                y_index += 1
            x_index += 1
        gt_image = np.expand_dims(gt_image * (255. / 4), axis=2).astype(np.uint8)
        overlay = cv2.applyColorMap(gt_image, cv2.COLORMAP_JET)
        # Mask overlay
        overlay[np.array(gt_image == 0)[:, :, [0, 0, 0]]] = [255]

        return overlay

    def overlayHeatmap(self, numpyImage) -> np.ndarray:

        if self.overlay is not None:
            temp_overlay = cv2.resize(self.overlay, numpyImage.shape[:2])
            return cv2.addWeighted(numpyImage, 0.7, temp_overlay, 0.3, 0)
        else:
            return numpyImage
