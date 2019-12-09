from SlideRunner.general.dependencies import *
from functools import partial
import PyQt5.QtCore as QtCore

def hitClose(ev, d: QDialog, elem:dict):
    if (elem['editx'].text().isdigit()) and (elem['edity'].text().isdigit()):
        d.close()

def getCoordinatesDialog(self):
    d = QDialog()
    layout = QtWidgets.QGridLayout()
    d.setLayout(layout)
    elem = dict()
    image_dims=self.slide.level_dimensions[0]
    cx = int((self.relativeCoords[0]+0.5)*image_dims[0])
    cy = int((self.relativeCoords[1]+0.5)*image_dims[1])

    l1 = QtWidgets.QLabel("Please enter coordinates")
    layout.addWidget(l1, 0,0)
    l2 = QtWidgets.QLabel("x")
    layout.addWidget(l2, 1,0)
    editx = QtWidgets.QLineEdit()
    layout.addWidget(editx,1,1)
    editx.setText(str(cx))

    l2 = QtWidgets.QLabel("y")
    layout.addWidget(l2, 1, 2)
    edity = QtWidgets.QLineEdit()
    layout.addWidget(edity,1,3)
    edity.setText(str(cy))

    b1 = QPushButton("ok",d)
    layout.addWidget(b1, 1,5)
    elem['editx'] = editx
    elem['edity'] = edity

    b1.clicked.connect(partial(hitClose, d=d, elem=elem))

    d.setWindowTitle("Enter Coordinates")
    d.setWindowModality(Qt.ApplicationModal)
    d.exec_()

    return int(editx.text()), int(edity.text())

