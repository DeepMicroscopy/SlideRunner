import SlideRunner.general.SlideRunnerPlugin as SlideRunnerPlugin
import SlideRunner.dataAccess.annotations as annotations
import queue
from threading import Thread
from queue import Queue
import cv2
import numpy as np


import math
import cv2
import numpy as np


'''

MacenkoNorm: Normalize a RGB image by mapping the appearance to that of a target

 Inputs:
 image    - Original Image.

 Output:
 Inorm    - Normalised RGB image.

 References:
 [1] M Macenko, M Niethammer, JS Marron, D Borland, JT Woosley, X Guan, C
     Schmitt, NE Thomas. "A method for normalizing histology slides for
     quantitative analysis". IEEE International Symposium on Biomedical
     Imaging: From Nano to Macro, 2009 vol.9, pp.1107-1110, 2009.

 Acknowledgements:
     This function is inspired by the Stain normalization toolbox by WARWICK
     ,which is available for download at:
     http://www2.warwick.ac.uk/fac/sci/dcs/research/tia/software/sntoolbox/

 Info: provided by Max Krappmann
'''


def quantile(x, q):
    n = len(x)
    y = np.sort(x)
    return (np.interp(q, np.linspace(1 / (2 * n), (2 * n - 1) / (2 * n), n), y))

def mypercentile(x, p):
    return (quantile(x, np.array(p) / 100))


#
def normalize(I, Iselection = None):
    """
    Macenko Normalization (includes, mypercentile, quantile):

    parameters:
        I: the image to normalize
        Iselection: subpart (N,3) of image used for normalization

    """
    I0 = 240
    beta = 0.15
    alpha = 1
    # reference matrix for stain
    HRef = np.array(((0.5626, 0.2159), (0.7201, 0.8012), (0.4062, 0.5581)))
    maxCRef = np.array((1.9705, 1.0308))

    h = I.shape[0]
    w = I.shape[1]

    I = np.float32(I.T)
    I = np.reshape(I, (h, w, 3))
    I = I.flatten()
    I = np.reshape(I, (3, h * w))

    I = I.T
    if (Iselection is None):
        Iselection = I

    print(Iselection.shape)
    OD = -np.log((Iselection + 1) / I0)
    ODHat = OD.copy()

    ODHat[ODHat <= beta] = 0
    ODHat = ODHat.reshape(-1, 3)
    ODflat = OD.reshape(-1, 3)
    ODcomplete = -np.log((I + 1) / I0)
    print('ODC shape',ODcomplete.shape)
    ODsmall = list()
    for i in ODHat:
        if np.count_nonzero(i) == 3:
            ODsmall.append(i)
    ODHat = np.asarray(ODsmall)
    ODHat = np.asarray(ODHat)

    # Compute CovarianceMatrix Unterscheidet sich von Matlab implementation
    Cov = np.asarray((np.cov(ODHat.T)))
    # Berechne ev von Cov
    # V ist nicht auf unitlength normiert
    ev, V = np.linalg.eigh(Cov)
    evSort = [0, 0, 0]
    VSort = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]

    for i in range(len(Cov)):
        evSort[2 - i] = ev[i]
        for k in Cov:
            for j in range(len(k)):
                VSort[j][i] = V[j][i]

    for i in range(len(Cov)):
        evSort[2 - i] = ev[i]

    ev = evSort
    ev = np.asarray(ev)
    idx = ev.argsort()[::-1]
    V = V[:, idx]
    # V mit den ersten 3 Hauptkompnenten unsicher ob wirklich die ersten 3 komponenten
    # 3x3 Matrix
    # Nimm spalten von V
    V = np.array([V[:, 1], V[:, 2]])
    V = V.T

    # _________________________________________________________________
    That = -np.dot(ODHat, V)
    # _________________________________________________________________
    phi = np.arctan2(That.T[1], That.T[0])
    # _________________________________________________________________

    minPhi = mypercentile(phi, alpha)
    maxPhi = mypercentile(phi, (100 - alpha))

    # _______________________________________________

    RotMin = np.array([[math.cos(minPhi)], [math.sin(minPhi)]])
    RotMax = np.array([[math.cos(maxPhi)], [math.sin(maxPhi)]])
    # _________________________________________________________________
    vMin = -np.dot(V, RotMin)
    vMax = -np.dot(V, RotMax)
    # _________________________________________________________________________________
    if vMin[0] > vMax[0]:
        # if np.sum(vMin,0)*np.sum(vMin,0) > np.sum(vMax,0)*np.sum(vMax,0):
        HE = np.concatenate((vMin, vMax), axis=1)
        HE = np.array(HE)
    else:
        HE = np.concatenate((vMax, vMin), axis=1)
        HE = np.array(HE)

    Y = ODflat.T
    Ycompl = ODcomplete.T
    # _________________________________________________________________________________
    C = np.asarray(np.linalg.lstsq(HE, Y))
    C = C[0]
    print('C is :',C.shape)

    Ccompl = np.asarray(np.linalg.lstsq(HE, Ycompl))
    Ccompl = Ccompl[0]
    # _________________________________________________________________________________
    # Percentile von C ueber 2Dimensionen
    #
    C0 = C[0]
    C1 = C[1]
    C0 = np.asarray(C0)
    C1 = np.asarray(C1)
    C0 = C0.T
    C1 = C1.T
    maxC0 = mypercentile(C0, 99)
    maxC1 = mypercentile(C1, 99)
    maxC = np.asarray([maxC0, maxC1])
    maxC = maxC.T
    # _________________________________________________________________________________
    C_norm = list()

    C_norm.append([[(C[0] / maxC[0]) * maxCRef[0]], [(C[1] / maxC[1]) * maxCRef[1]]])
    C_norm = np.reshape(np.asarray(C_norm), (C.shape))
    print('CNorm: ',C_norm.shape)

    C_norm_compl = list()

    C_norm_compl.append([[(Ccompl[0] / maxC[0]) * maxCRef[0]], [(Ccompl[1] / maxC[1]) * maxCRef[1]]])
    C_norm_compl = np.reshape(np.asarray(C_norm_compl), (Ccompl.shape))
    print('CNormcompl: ',C_norm_compl.shape)



    # _________________________________________________________________________________
    exponent = np.dot(-HRef, C_norm_compl)
    Inorm = np.exp(exponent)
    Inorm = [i * I0 for i in Inorm]
    Inorm = np.int64(Inorm)
    Inorm = np.array(Inorm)
    print('Inorm: ',Inorm.shape)
    # _________________________________________________________________________________
    # Form wieder auf Zeilen und Spalten umrechnen
    Inorm = np.reshape(Inorm.T, (w, h, 3))
    Inorm = np.rot90(Inorm, 3)
    Inorm = cv2.flip(Inorm, 1)

    return Inorm

class Plugin(SlideRunnerPlugin.SlideRunnerPlugin):
    version = 0.1
    shortName = 'Normalize (Macenko)'
    inQueue = Queue()
    outQueue = Queue()
    initialOpacity=1.0
    updateTimer=0.5
    outputType = SlideRunnerPlugin.PluginOutputType.RGB_IMAGE
    description = 'H&E Image normalization (Method by Macenko)'
    pluginType = SlideRunnerPlugin.PluginTypes.IMAGE_PLUGIN
    configurationList = list((SlideRunnerPlugin.PluginConfigurationEntry(uid=0, name='Normalize on annotation', ctype=SlideRunnerPlugin.PluginConfigurationType.ANNOTATIONACTION),))

    def __init__(self, statusQueue:Queue):
        self.statusQueue = statusQueue
        self.p = Thread(target=self.queueWorker, daemon=True)
        self.p.start()
        
        pass

    def queueWorker(self):
        quitSignal = False
        while not quitSignal:
            job = SlideRunnerPlugin.pluginJob(self.inQueue.get())
            image = job.currentImage

            if (job.jobDescription == SlideRunnerPlugin.JobDescription.QUIT_PLUGIN_THREAD):
                # signal to exit this thread
                quitSignal=True
                continue

            print('Macenko norm plugin: received 1 image from queue')
            self.setProgressBar(0)

            print(job)
            if (job.annotations is not None) and len(job.annotations)>0:
                if (job.annotations[0].annotationType == annotations.AnnotationType.AREA):
                    print('Found an area annotation - great!')
                    minC = job.annotations[0].minCoordinates()
                    maxC = job.annotations[0].maxCoordinates()

                    scaleX = (job.coordinates[2])/job.currentImage.shape[1]
                    scaleY = (job.coordinates[3])/job.currentImage.shape[0]

                    minC = np.array((max(0,int((minC.x-job.coordinates[0])/scaleX)), max(0,int((minC.y-job.coordinates[1])/scaleY))))
                    maxC = np.array((min(job.currentImage.shape[1],int((maxC.x-job.coordinates[0])/scaleX)), min(job.currentImage.shape[0],int((maxC.y-job.coordinates[1])/scaleY))))

                    rgb = np.copy(image[:,:,0:3])
                    rgb = normalize(rgb, np.reshape(rgb[minC[1]:maxC[1],minC[0]:maxC[0],:], (-1,3)))


            else:

                rgb = np.copy(image[:,:,0:3])
                rgb = normalize(rgb)

            self.returnImage(np.float32(rgb), job.procId)
            self.setMessage('Macenko normalization: done.')
            self.setProgressBar(-1)



        