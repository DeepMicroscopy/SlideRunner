"""

        This is SlideRunner - An Open Source Annotation Tool 
        for Digital Histology Slides.

         Marc Aubreville, Pattern Recognition Lab, 
         Friedrich-Alexander University Erlangen-Nuremberg 
         marc.aubreville@fau.de

        If you use this software in research, please citer our paper:
        M. Aubreville, C. Bertram, R. Klopfleisch and A. Maier:
        SlideRunner - A Tool for Massive Cell Annotations in Whole Slide Images
        Bildverarbeitung fuer die Medizin 2018, Springer Verlag, Berlin-Heidelberg

"""

__all__ = []




import SlideRunner_dataAccess.annotations as annotations
import SlideRunner_dataAccess.database as database
import SlideRunner_dataAccess.nifty as nifty
import SlideRunner_dataAccess.slide as slide

from SlideRunner_dataAccess.slide import os_fileformats
from SlideRunner_dataAccess.nifty import nii_fileformats
from SlideRunner_dataAccess.dicomimage import dic_fileformats
fileformats = os_fileformats + nii_fileformats + dic_fileformats
