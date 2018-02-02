# SlideRunner
<img align="right" height="100" src="SlideRunner/doc/logoline.png">

*SlideRunner* is a tool for massive cell annotations in whole slide images.

It has been created in close cooperation between the Pattern Recognition Lab, Friedrich-Alexander-Universität Erlangen-Nürnberg and the Institute of Veterenary Pathology, Freie Universität Berlin.

If you use the software for research purposes, please cite our paper:

> M. Aubreville, C. Bertram, R. Klopfleisch and A. Maier (2018): SlideRunner - A Tool for Massive Cell Annotations in Whole Slide Images, In: Bildverarbeitung für die Medizin 2018 

Link to the paper will be available after BVM 2018.

Please find the authors webpage at: https://www5.cs.fau.de/~aubreville/


## Installation

SlideRunner is written in Python 3, so you will need a Python 3 distribution like e.g. Anaconda (https://www.anaconda.com/download/) to run it.

To install, please make sure that you have the following python packages and their dependencies installed:

Library           | version           |  link             
------------------|-------------------|-------------------
PyQT5             | >= 5.6.0         | https://pyqt.sourceforge.net/
numpy             | >= 1.13           | https://www.numpy.org
cv2 (OpenCV3)     | >= 3.1.0          | https://opencv.org
sqlite3           | >= 2.6.0          | https://www.sqlite.org
openslide         | >= 1.1.1          | https://www.openslide.org

### OpenCV3
OpenCV3 can be most conveniently installed with anaconda:

> conda install -c conda-forge opencv

### Other dependencies
All other dependencies can be installed most easily using pip:

> pip install --upgrade pyqt5 numpy openslide-python

## Screenshots

![SlideRunner Screenshot](SlideRunner/doc/gui.png)

## Database structure

The major entity of our database model is the annotation. Each annotation can have multiple coordinates, with their respective x and y coordinates, and the order they were drawn (for polygons). Further, each annotation has a multitude of labels that were given by one person each and are belonging to one class, respectively. 

![DB Structure](SlideRunner/doc/SlideRunner_UML.png)
