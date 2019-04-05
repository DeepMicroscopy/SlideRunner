from SlideRunner.general.dependencies import *
from functools import partial
import PyQt5.QtCore as QtCore
cmaps = ['viridis', 'plasma', 'inferno', 'magma', 'cividis', 'Greys', 'Purples', 'Blues', 'Greens', 'Oranges', 'Reds',
            'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 'BuPu',
            'GnBu', 'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn', 'binary', 'gist_yarg', 'gist_gray', 'gray', 'bone', 'pink',
            'spring', 'summer', 'autumn', 'winter', 'cool', 'Wistia',
            'hot', 'afmhot', 'gist_heat', 'copper', 'PiYG', 'PRGn', 'BrBG', 'PuOr', 'RdGy', 'RdBu',
            'RdYlBu', 'RdYlGn', 'Spectral', 'coolwarm', 'bwr', 'seismic', 'twilight', 'twilight_shifted', 'hsv',
            'Pastel1', 'Pastel2', 'Paired', 'Accent',
            'Dark2', 'Set1', 'Set2', 'Set3',
            'tab10', 'tab20', 'tab20b', 'tab20c', 'flag', 'prism', 'ocean', 'gist_earth', 'terrain', 'gist_stern',
            'gnuplot', 'gnuplot2', 'CMRmap', 'cubehelix', 'brg',
            'gist_rainbow', 'rainbow', 'jet', 'nipy_spectral', 'gist_ncar']


def saveAndClose(ev, d: QDialog, elem:dict, settingsObject):
    cmap = cmaps[elem['combo_colorbar'].currentIndex()]
    settingsObject.setValue('OverlayColorMap', cmap)

    settingsObject.setValue('SpotCircleRadius', elem['radiusSlider'].value())


    d.close()


def chooseFile(ev, d: QDialog, elem:dict, settingsObject):

    ret,err = QFileDialog.getOpenFileName(None,"Please choose default database.", "",'*.sqlite')
    if (ret is not None):
        settingsObject.setValue('DefaultDatabase', ret)
        elem['dbfile'].setText(ret)


def changePxSlider(ev, sliderObj:QtWidgets.QSlider, labelObj:QtWidgets.QLabel):
    labelObj.setText('%d px' % sliderObj.value())

def settingsDialog(settingsObject):
    d = QDialog()
    layout = QtWidgets.QGridLayout()
    d.setLayout(layout)
    elem = dict()
    
    l1 = QtWidgets.QLabel("Overlay color scheme")
    layout.addWidget(l1, 0,0)
    c1 = QtWidgets.QComboBox()
    ci = 0
    for key,item in enumerate(cmaps):
        c1.addItem(item)
        if (item == settingsObject.value('OverlayColorMap')):
            ci = key
    elem['combo_colorbar'] = c1 
    c1.setCurrentIndex(ci)

    l2 = QtWidgets.QLabel("Radius of spot annotations")
    l3 = QtWidgets.QLabel("%d px" %settingsObject.value('SpotCircleRadius') )
    layout.addWidget(l2, 1,0)
    layout.addWidget(l3, 1,2)
    newSlider = QtWidgets.QSlider()
    newSlider.setMinimum(1)
    newSlider.setMaximum(100)
    newSlider.setValue(settingsObject.value('SpotCircleRadius'))
    newSlider.setOrientation(QtCore.Qt.Horizontal)
    layout.addWidget(newSlider, 1,1)
    elem['radiusSlider'] = newSlider

    newSlider.valueChanged.connect(partial(changePxSlider, sliderObj=newSlider, labelObj=l3))

    l4 = QtWidgets.QLabel("Default database")
    l5 = QtWidgets.QLabel(settingsObject.value('DefaultDatabase'))
    layout.addWidget(l4, 2,0)
    layout.addWidget(l5, 2,1)
    b2 = QPushButton("choose",d)
    layout.addWidget(b2, 2,2)
    elem['dbfile'] = l5
    b2.clicked.connect(partial(chooseFile, d=d, elem=elem, settingsObject=settingsObject))

    newSlider.valueChanged.connect(partial(changePxSlider, sliderObj=newSlider, labelObj=l3))



    layout.addWidget(c1, 0,1)
    b1 = QPushButton("ok",d)
    layout.addWidget(b1, 3,1)
    b1.clicked.connect(partial(saveAndClose, d=d, elem=elem, settingsObject=settingsObject))

#    b1.move(50,50)
    d.setWindowTitle("Settings")
    d.setWindowModality(Qt.ApplicationModal)
    d.exec_()

