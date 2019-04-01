import SlideRunner.general.SlideRunnerPlugin as SlideRunnerPlugin
import queue
from threading import Thread
from queue import Queue
import cv2
import numpy as np

class Plugin(SlideRunnerPlugin.SlideRunnerPlugin):
    version = 0.1
    shortName = 'Countdown'
    inQueue = Queue()
    outQueue = Queue()
    updateTimer=0.5
    description = 'Count database objects down to zero'
    outputType = SlideRunnerPlugin.PluginOutputType.NO_OVERLAY
    pluginType = SlideRunnerPlugin.PluginTypes.WHOLESLIDE_PLUGIN
    configurationList = list((SlideRunnerPlugin.PluginConfigurationEntry(uid=0, name='Count down from', initValue=300., minValue=0.0, maxValue=1200.0),))
    
    def __init__(self, statusQueue:Queue):
        self.statusQueue = statusQueue
        self.p = Thread(target=self.queueWorker, daemon=True)
        self.p.start()
        self.total_number = 300
        self.last_count = None
        
        pass

    def queueWorker(self):
        quitSignal=False
        while not quitSignal:
            job = SlideRunnerPlugin.pluginJob(self.inQueue.get())
            self.total_number = int(job.configuration[0])
            
            if (job.jobDescription == SlideRunnerPlugin.JobDescription.QUIT_PLUGIN_THREAD):
                # signal to exit this thread
                quitSignal=True
                continue

            database = job.openedDatabase    

            annotations_count = len(database.annotations)
            if annotations_count != self.last_count:
                self.last_count = annotations_count
                if self.total_number - annotations_count == 0:
                    self.setMessage('Done. Thanks for your help :)')
                    self.showMessageBox('Done. Thanks for your help :)')
                elif self.total_number - annotations_count < 0:
                    self.setMessage('You are ambitious, thats gread, thank you')
                else:
                    self.setMessage('{0} anotations to go'.format(self.total_number - annotations_count))
                