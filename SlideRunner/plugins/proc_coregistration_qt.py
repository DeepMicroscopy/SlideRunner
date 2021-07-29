try:
    import SlideRunner.general.SlideRunnerPlugin as SlideRunnerPlugin
    import queue
    from threading import Thread
    from queue import Queue
    import openslide
    import cv2
    import numpy as np
    import cv2, openslide
    import numpy as np
    import os, math
    from scipy import ndimage
    from scipy.stats import gaussian_kde
    import matplotlib.pyplot as plt
    import logging
    from pathlib import Path

    import qt_wsi_reg.registration_tree as registration

except Exception:
    print('Unable to activate QT co-registration plugin')
    raise

parameters = {
    # feature extractor parameters
    "point_extractor": "sift",  #orb , sift
    "maxFeatures": 512, 
    "crossCheck": False, 
    "flann": False,
    "ratio": 0.6, 
    "use_gray": False,

    # QTree parameter 
    "homography": True,
    "filter_outliner": False,
    "debug": False,
    "target_depth": 1,
    "run_async": True,
    "num_workers": 2,
    "thumbnail_size": (1024, 1024)
}






class Plugin(SlideRunnerPlugin.SlideRunnerPlugin):
    version = 0.1
    shortName = 'Quad-Tree-based WSI Registration (Marzahl et al.)'
    inQueue = Queue()
    outQueue = Queue()
    updateTimer=0.5
    outputType = SlideRunnerPlugin.PluginOutputType.RGB_OVERLAY
    description = 'Apply Marzahl''s method for WSI co-registration'
    pluginType = SlideRunnerPlugin.PluginTypes.IMAGE_PLUGIN

    configurationList = list((
                            SlideRunnerPlugin.FilePickerConfigurationEntry(uid='file', name='Second WSI', mask='*.*'),
                            SlideRunnerPlugin.PushbuttonPluginConfigurationEntry(uid='match',name='Match')
                            ))


    def __init__(self, statusQueue:Queue):
        self.statusQueue = statusQueue
        self.p = Thread(target=self.queueWorker, daemon=True)
        self.p.start()
        
        pass

    def queueWorker(self):
        oldwsi=None
        quitSignal=False
        sl=None
        self.qt = None
        sl_main = None
        while not quitSignal:
            job = SlideRunnerPlugin.pluginJob(self.inQueue.get())
            image = job.currentImage
            mainWSI = job.slideFilename
            
            if 'file' not in job.configuration:
                continue

            
            if (job.configuration['file'] != oldwsi) and (job.configuration['file']!='') and job.configuration['file']:
                sl = openslide.open_slide(job.configuration['file'])

            if (mainWSI):
                sl_main = openslide.open_slide(mainWSI)

            if (job.trigger is not None) and job.trigger.uid=='match':
                print('Trigger: ',job.trigger)
                self.setProgressBar(0)
                self.setMessage('Calculating registration')
                self.qt = registration.RegistrationQuadTree(source_slide_path=Path(mainWSI), target_slide_path=Path(job.configuration['file']), **parameters)
                box = np.array([0,0,0,0])
                trans_box = self.qt.transform_boxes(np.array([box]))[0]
                self.setMessage('Registration done')
                self.setProgressBar(-1)

            if (sl) and (sl_main):
                self.setProgressBar(0)
                print('Reading from: ',job)

                zoomValue=job.coordinates[3]/job.currentImage.shape[0]
                print('Zoom value: ',zoomValue)

                print('Coordinates:',job.coordinates)
                if self.qt is None:
                    self.setProgressBar(-1)
                    continue
                coordinates=[job.coordinates]
                reg_coordinates = self.qt.transform_boxes([job.coordinates])[0]
                print('registered coordinates:', reg_coordinates)
                zoomValue=(reg_coordinates[2])/job.currentImage.shape[0]

                act_level = np.argmin(np.abs(np.asarray(sl.level_downsamples)-zoomValue))
                closest_ds = sl_main.level_downsamples[np.argmin(np.abs(np.asarray(sl_main.level_downsamples)-zoomValue))]



                imgarea_w=job.coordinates[2:4]
                size_im = (int(imgarea_w[0]/closest_ds), int(imgarea_w[1]/closest_ds))
                print('Image size: ',size_im)
                location = [int(x) for x in reg_coordinates[0:2]]
                print('Location (original):',job.coordinates[0:2])
                print('Location (offset): ',location)
                img = sl.read_region(location=location, level=act_level, size=size_im)
                img = np.array(img.resize((job.currentImage.shape[1],job.currentImage.shape[0] )))

                self.returnImage(img, job.procId)
                self.setMessage('Align done.')
                self.setProgressBar(-1)


            if (job.jobDescription == SlideRunnerPlugin.JobDescription.QUIT_PLUGIN_THREAD):
                # signal to exit this thread
                quitSignal=True
                continue
            





        