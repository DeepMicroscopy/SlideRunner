"""

        This is SlideRunner - An Open Source Annotation Tool 
        for Digital Histology Slides.

         Marc Aubreville, Pattern Recognition Lab, 
         Friedrich-Alexander University Erlangen-Nuremberg 
         marc.aubreville@fau.de

        If you use this software in research, please citer our paper:
        M. Aubreville, C. Bertram, R. Klopfleisch and A. Maier:
        SlideRunner - A Tool for Massive Cell Annotations in Whole Slide Images. 
        In: Bildverarbeitung für die Medizin 2018. 
        Springer Vieweg, Berlin, Heidelberg, 2018. pp. 309-314.
"""


class UIMainMode (enumerate):
    """
        GUI main modes
    """
    MODE_VIEW = 1
    MODE_ANNOTATE_SPOT = 2
    MODE_ANNOTATE_AREA = 3
    MODE_ANNOTATE_POLYGON = 4
    MODE_ANNOTATE_FLAG = 5
    MODE_ANNOTATE_CIRCLE = 6
    MODE_ANNOTATE_WAND = 7
    
class ClassRowItemId (enumerate):
    ITEM_DATABASE = 0
    ITEM_PLUGIN = 1

class ClassRowItem(object):
    def __init__(self,  itemID: ClassRowItemId, classID, uid:int = None):
        self.itemID = itemID
        self.uid = uid
        self.classID = classID


class WandAnnotation(object):
    def __init__(self, xy:tuple=(None,None)):
        self.x, self.y = xy
        self.tolerance=2
        self.mask=None
        self.polygon=None
    
    def seed_point(self):
        return (self.x, self.y)