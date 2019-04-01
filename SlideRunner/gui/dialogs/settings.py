from SlideRunner.general.dependencies import *
from functools import partial
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
    d.close()

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

    layout.addWidget(c1, 0,1)
    b1 = QPushButton("ok",d)
    layout.addWidget(b1, 1,1)
    b1.clicked.connect(partial(saveAndClose, d=d, elem=elem, settingsObject=settingsObject))

#    b1.move(50,50)
    d.setWindowTitle("Settings")
    d.setWindowModality(Qt.ApplicationModal)
    d.exec_()

