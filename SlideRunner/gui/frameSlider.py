from PyQt5 import QtCore, QtGui, QtWidgets
import numpy as np
from PyQt5.QtCore import Qt


class frameSlider(QtWidgets.QWidget):

    sliderPos = 0
    fps = 1.0
    numberOfFrames = 1
    valueChanged = QtCore.pyqtSignal()
    text = '1'
  
    def __init__(self):      
        super(frameSlider, self).__init__()
        
        self.initUI()

    def setFPS(self, fps:float):
        self.fps = fps
        self.setSteps()
        self.repaint()
    
    def setNumberOfFrames(self, numberOfFrames):
        self.numberOfFrames = numberOfFrames
        self.setSteps()
        self.setHidden(numberOfFrames==1)
        self.repaint()

    def getMaxZoom(self) -> float:
        return self.maxZoom
    
    def setText(self, text:str):
        self.text = text
        self.repaint()

    def getValue(self) -> float:
        return self.sliderPos
    
    def setValue(self, value:float):
        self.sliderPos = min(max(int(value),0),self.numberOfFrames-1)
        if (self.fps != 1.0):
            self.text = '%.2f' % (self.sliderPos/self.fps)
        else:
            self.text = '%d' % (self.sliderPos+1)
        self.repaint()


    def setMinZoom(self, value : float):
        self.setSteps()
        self.repaint()

    def initUI(self):
        
        self.setMinimumSize(1, 40)
        self.value = 700
        self.num = list()
        self.setSteps()

    def mouseMoveEvent(self, event):
        self.mousePressEvent(event, dragging=True)
    
    def mouseReleaseEvent(self, event):
        self.mousePressEvent(event, dragging=True)
        self.valueChanged.emit()

    def mousePressEvent(self, event, dragging=False):
        if (self.numberOfFrames==1):
            return
        if ((event.button() == Qt.LeftButton)) or dragging:
            pntr_x = float(event.localPos().x())
            w = self.size().width() - 40

            zoomPos = (pntr_x-20)/w
            self.sliderPos = 100*zoomPos

            # quantize according to frames
            self.sliderPos = np.round(self.sliderPos/100*(self.numberOfFrames-1))

            self.sliderPos = np.clip(self.sliderPos,0,self.numberOfFrames-1)
            self.setValue(self.sliderPos)

            self.repaint()
            


    def setSteps(self):
        zoomList = np.linspace(0,100,10)
        self.steps = []
        self.num = []
        if (self.numberOfFrames==1):
            return
        for step in zoomList:
                if (self.fps!= 1.0):
                    self.steps.append( np.round((self.numberOfFrames) / self.fps * step/100,2))
                    self.num.append(step)
                else:
                    self.steps.append( 1+int(np.round(np.round((self.numberOfFrames-1)  * step/100))))
                    self.num.append(step)



    def paintEvent(self, e):
      
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawWidget(qp)
        qp.end()
    
    
      
    def drawWidget(self, qp):
      
        if (self.numberOfFrames==1):
            return
        metrics = qp.fontMetrics()

        size = self.size()
        w = size.width()
        h = size.height()



        step = int(round(w / 10.0))

        till = int(((w / 750.0) * self.value))
        full = int(((w / 750.0) * 700))

        w_net = w - 40
        
        qp.setBrush(QtGui.QColor(93, 93, 93))
        qp.setPen(QtGui.QColor(39, 39, 39))
        qp.drawRect(20-1, 20, w_net+2, 5)

        qp.setBrush(QtGui.QColor(70, 70, 70))
        font = QtGui.QFont('Serif', 7, QtGui.QFont.Light)
        qp.setFont(font)

        for j in range(len(self.steps)):
            qp.setPen(QtGui.QColor(93, 93, 93))
            qp.drawLine(self.num[j]*w_net/100+20, 25, self.num[j]*w_net/100+20, 32)
            labelstr = str(self.steps[j])
            fw = metrics.width(labelstr)
            qp.setPen(QtGui.QColor(255, 255, 255))
            qp.drawText(self.num[j]*w_net/100-fw/2+20, h, labelstr)


        font = QtGui.QFont('Serif', 12, QtGui.QFont.Light)
        qp.setFont(font)


        tw = metrics.width(self.text)
        qp.setPen(QtGui.QColor(38, 38, 38))
        qp.setBrush(QtGui.QColor(71, 71, 71))


        qp.drawRect(w_net*self.sliderPos/(self.numberOfFrames-1)*100*0.01+20-5, 13, 10, 20)
        qp.setPen(QtGui.QColor(99, 99, 99))
        qp.drawRect(w_net*self.sliderPos/(self.numberOfFrames-1)*100*0.01+20-4, 14, 8, 20-2)

        qp.setBrush(QtGui.QColor(70, 70, 70))
        qp.setPen(QtGui.QColor(255, 255, 255))
        qp.drawText(self.sliderPos/(self.numberOfFrames-1)*100*w_net/100-tw/2+20, 10,self.text)


