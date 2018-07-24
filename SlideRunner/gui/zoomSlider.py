from PyQt5 import QtCore, QtGui, QtWidgets
import numpy as np
from PyQt5.QtCore import Qt


class zoomSlider(QtWidgets.QWidget):

    maxZoom = 0.3
    minZoom = 80
    sliderPos = 0
    zoomLevel = 0
    valueChanged = QtCore.pyqtSignal()
    text = '8.0 x'
  
    def __init__(self):      
        super(zoomSlider, self).__init__()
        
        self.initUI()
    
    def sliderToZoomValue(self, value):
        return    np.power(2,value/100*(np.log2(0.5/ self.getMaxZoom())))*self.getMaxZoom()
    
    def zoomValueToSlider(self, value : float) -> float:
        maxZoom = self.getMaxZoom()
        retval = 100*np.log2(value/(maxZoom))/(np.log2(0.5/maxZoom))
        return 100*np.log2(value/(maxZoom))/(np.log2(0.5/maxZoom))

    def setMaxZoom(self, maxZoom : float):
        self.maxZoom = maxZoom
        self.setSteps()
        self.repaint()

    def getMaxZoom(self) -> float:
        return self.maxZoom
    
    def setText(self, text:str):
        self.text = text
        self.repaint()

    def getValue(self) -> float:
        return self.sliderPos
    
    def setValue(self, value:float):
        self.sliderPos = value
        self.zoomLevel = self.sliderToZoomValue(self.sliderPos)
        self.repaint()


    def setMinZoom(self, value : float):
        self.minZoom = value
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
        if ((event.button() == Qt.LeftButton)) or dragging:
            pntr_x = float(event.localPos().x())
            w = self.size().width() - 40

            zoomPos = (pntr_x-20)/w
            self.sliderPos = 100*zoomPos

            self.sliderPos = np.clip(self.sliderPos,0,100)
            self.zoomLevel = self.sliderToZoomValue(self.sliderPos)

            self.repaint()
            


    def setSteps(self):
        zoomList = 1 / np.float_power(2,np.asarray([-7,-6,-5,-4,-3,-2,-1,0]))
        self.steps = []
        self.num = []
        for step in zoomList:
                self.steps.append(self.minZoom / step / 2)
                self.num.append(self.zoomValueToSlider(step))
        self.steps.append(self.minZoom)
        self.num.append(self.zoomValueToSlider(0.5))



    def paintEvent(self, e):
      
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawWidget(qp)
        qp.end()
    
    
      
    def drawWidget(self, qp):
      

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
            labelstr = str(self.steps[j])+' x'
            fw = metrics.width(labelstr)
            qp.setPen(QtGui.QColor(255, 255, 255))
            qp.drawText(self.num[j]*w_net/100-fw/2+20, h, labelstr)


        font = QtGui.QFont('Serif', 12, QtGui.QFont.Light)
        qp.setFont(font)


        tw = metrics.width(self.text)
        qp.setPen(QtGui.QColor(38, 38, 38))
        qp.setBrush(QtGui.QColor(71, 71, 71))


        qp.drawRect(w_net*self.sliderPos*0.01+20-5, 13, 10, 20)
        qp.setPen(QtGui.QColor(99, 99, 99))
        qp.drawRect(w_net*self.sliderPos*0.01+20-4, 14, 8, 20-2)

        qp.setBrush(QtGui.QColor(70, 70, 70))
        qp.setPen(QtGui.QColor(255, 255, 255))
        qp.drawText(self.sliderPos*w_net/100-tw/2+20, 10,self.text)


