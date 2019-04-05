import cv2
import matplotlib.path as path
import numpy as np
class AnnotationType(enumerate):
    SPOT = 1
    AREA = 2
    POLYGON = 3
    SPECIAL_SPOT = 4
    CIRCLE = 5
    UNKNOWN = 255

class ViewingProfile(object):
    blindMode = False
    annotator = None
    COLORS_CLASSES = [[0,0,0,0],
                  [0,0,255,255],
                  [0,255,0,255],
                  [255,255,0,255],
                  [255,0,255,255],
                  [0,127,0,255],
                  [255,127,0,255],
                  [127,127,0,255],
                  [255,255,255,255],
                  [10, 166, 168,255],
                  [166, 10, 168,255],
                  [166,168,10,255]]
    spotCircleRadius = 25
    majorityClassVote = True
    activeClasses = dict()



class AnnotationLabel(object):
    def __init__(self,annotatorId:int, classId:int, uid:int):
        self.annnotatorId = annotatorId
        self.classId = classId
        self.uid = uid
    

class annoCoordinate(object):
    x = None
    y = None
    def __init__(self,x,y):
        self.x = x
        self.y = y
    
    def totuple(self):
        return (self.x, self.y)
    
    def tolist(self):
        return [self.x, self.y]

class annotation():

      def __init__(self):
          self.annotationType = AnnotationType.UNKNOWN
          self.labels = list()
          self.uid = 0

      def draw(self, image: np.ndarray, leftUpper: tuple, zoomLevel: float, thickness: int = 1, vp: ViewingProfile = ViewingProfile()):
            return
    
      def positionInAnnotation(self, position: list) -> bool:
            return False

      def getAnnotationsDescription(self, db) -> list:
           retval = list()
           for idx,label in enumerate(self.labels):
               annotatorName = db.getAnnotatorByID(label.annnotatorId)
               className = db.getClassByID(label.classId)
               retval.append(['Anno %d' % (idx+1), '%s (%s)' % (className,annotatorName)])
           return retval

      def getDescription(self, db) -> list:
            return self.getAnnotationsDescription(db)

      def addLabel(self, label:AnnotationLabel):
          self.labels.append(label)
        
      def getDimensions(self) -> (int, int):
          minC = self.minCoordinates()
          maxC = self.maxCoordinates()
          return (int(maxC.x-minC.x),int(maxC.y-minC.y))
        
      def getCenter(self) -> (annoCoordinate):
          minC = self.minCoordinates()
          maxC = self.maxCoordinates()
          return annoCoordinate(int(0.5*(minC.x+maxC.x)),int(0.5*(minC.y+maxC.y)))
        
      def removeLabel(self, uid:int):
          for label in range(len(self.labels)):
              if (self.labels[label].uid == uid):
                  self.labels.pop(label)
     
      def changeLabel(self, uid:int, annotatorId:int, classId:int):
          for label in range(len(self.labels)):
              if (self.labels[label].uid == uid):
                  self.labels[label] = AnnotationLabel(annotatorId, classId, uid)
      
      def maxLabelClass(self):
          retVal=0
          for label in range(len(self.labels)):
              if (self.labels[label].classId > retVal):
                  retVal=self.labels[label].classId
          return retVal


      """
            Returns the majority label for an annotation
      """
      def majorityLabel(self):
          if len(self.labels)==0:
              return 0

          histo = np.zeros(self.maxLabelClass()+1)

          for label in np.arange(0, len(self.labels)):
               histo[self.labels[label].classId] += 1

          if np.sum(histo == np.max(histo))>1:
              # no clear maximum, return 0
              return 0
          else:   
              # a clear winner. Return it.
              return np.argmax(histo)


      """
            Returns the agreed (common) label for an annotation
      """
      def agreedLabel(self):
          if len(self.labels)==0:
              return 0

          agreed = self.labels[0].classId

          for label in np.arange(0, len(self.labels)):
         
            if not (self.labels[label].classId == agreed):
                agreed = 0
        
          return agreed
      
      def labelBy(self, annotatorId):
          for label in np.arange(0, len(self.labels)):
               if (self.labels[label].annnotatorId == annotatorId):
                    return self.labels[label].classId
          return 0
        
      def getColor(self, vp : ViewingProfile):
          if (vp.blindMode):
            return vp.COLORS_CLASSES[self.labelBy(vp.annotator) % len(vp.COLORS_CLASSES)]
          elif (vp.majorityClassVote):
            return vp.COLORS_CLASSES[self.majorityLabel() % len(vp.COLORS_CLASSES)]
          else:
            return vp.COLORS_CLASSES[self.agreedLabel() % len(vp.COLORS_CLASSES)]
      
      def minCoordinates(self) -> annoCoordinate:
            print('Whopsy... you need to overload this.')
            return annoCoordinate(None, None)

      def maxCoordinates(self) -> annoCoordinate:
            print('Whopsy... you need to overload this.')
            return annoCoordinate(None, None)


class rectangularAnnotation(annotation):
      def __init__(self, uid, x1, y1, x2, y2):
            super().__init__()
            self.uid = uid
            self.x1 = x1
            self.y1 = y1
            self.x2 = x2
            self.y2 = y2
            self.annotationType = AnnotationType.AREA
      
      def minCoordinates(self) -> annoCoordinate:
            return annoCoordinate(self.x1, self.y1)
      
      def getDescription(self,db) -> list:
          return [['Position', 'x1=%d, y1=%d, x2=%d, y2=%d' % (self.x1,self.y1,self.x2,self.y2)]] + self.getAnnotationsDescription(db)

      def maxCoordinates(self) -> annoCoordinate:
            return annoCoordinate(self.x2, self.y2)

      def positionInAnnotation(self, position: list) -> bool:
            return ((position[0]>self.x1) and (position[0]<self.x2) and 
                   (position[1]>self.y1) and (position[1]<self.y2))

      def draw(self, image: np.ndarray, leftUpper: tuple, zoomLevel: float, thickness: int, vp : ViewingProfile):
            xpos1=max(0,int((self.x1-leftUpper[0])/zoomLevel))
            ypos1=max(0,int((self.y1-leftUpper[1])/zoomLevel))
            xpos2=min(image.shape[1],int((self.x2-leftUpper[0])/zoomLevel))
            ypos2=min(image.shape[0],int((self.y2-leftUpper[1])/zoomLevel))
            image = cv2.rectangle(image, thickness=thickness, pt1=(xpos1,ypos1), pt2=(xpos2,ypos2),color=self.getColor(vp), lineType=cv2.LINE_AA)

class polygonAnnotation(annotation):
    def __init__(self, uid:int, coordinates: np.ndarray = None):
        super().__init__()
        self.uid = uid
        self.annotationType = AnnotationType.POLYGON
        if (coordinates is not None):
            self.coordinates = coordinates

    def minCoordinates(self) -> annoCoordinate:
        return annoCoordinate(self.coordinates[:,0].min(), self.coordinates[:,1].min())

    def maxCoordinates(self) -> annoCoordinate:
        return annoCoordinate(self.coordinates[:,0].max(), self.coordinates[:,1].max())

    def positionInAnnotation(self, position: list) -> bool:
        p = path.Path(self.coordinates)

        return p.contains_point(position)

    def draw(self, image: np.ndarray, leftUpper: tuple, zoomLevel: float, thickness: int, vp : ViewingProfile):
        def slideToScreen(pos):
            """
                convert slide coordinates to screen coordinates
            """
            xpos,ypos = pos
            p1 = leftUpper
            cx = int((xpos - p1[0]) / zoomLevel)
            cy = int((ypos - p1[1]) / zoomLevel)
            return (cx,cy)        
        markersize = int(5/zoomLevel)
        listIdx=-1

        # small assertion to fix bug #12
        if (self.coordinates.shape[1]==0):
            return image

        for listIdx in range(self.coordinates.shape[0]-1):
            anno = slideToScreen(self.coordinates[listIdx])
            cv2.line(img=image, pt1=anno, pt2=slideToScreen(self.coordinates[listIdx+1]), thickness=2, color=self.getColor(vp), lineType=cv2.LINE_AA)       

            pt1_rect = (max(0,anno[0]-markersize),
                        max(0,anno[1]-markersize))
            pt2_rect = (min(image.shape[1],anno[0]+markersize),
                        min(image.shape[0],anno[1]+markersize))
            cv2.rectangle(img=image, pt1=(pt1_rect), pt2=(pt2_rect), color=[255,255,255,255], thickness=2)
            cv2.rectangle(img=image, pt1=(pt1_rect), pt2=(pt2_rect), color=self.getColor(vp), thickness=1)
        listIdx+=1
        anno = slideToScreen(self.coordinates[listIdx])
        pt1_rect = (max(0,anno[0]-markersize),
                    max(0,anno[1]-markersize))
        pt2_rect = (min(image.shape[1],anno[0]+markersize),
                    min(image.shape[0],anno[1]+markersize))
        cv2.rectangle(img=image, pt1=(pt1_rect), pt2=(pt2_rect), color=[255,255,255,255], thickness=2)
        cv2.rectangle(img=image, pt1=(pt1_rect), pt2=(pt2_rect), color=[0,0,0,255], thickness=1)
        cv2.line(img=image, pt1=anno, pt2=slideToScreen(self.coordinates[0]), thickness=2, color=self.getColor(vp), lineType=cv2.LINE_AA)       


class circleAnnotation(annotation):
      
      def __init__(self, uid, x1, y1, x2, y2):
            super().__init__()
            self.annotationType = AnnotationType.CIRCLE
            self.uid = uid
            self.x1 = int(0.5*(x1+x2))
            self.y1 = int(0.5*(y1+y2))
            self.r = int((x2-x1)*0.5)

      def minCoordinates(self) -> annoCoordinate:
            return annoCoordinate(self.x1-self.r, self.y1-self.r)

      def maxCoordinates(self) -> annoCoordinate:
            return annoCoordinate(self.x1+self.r, self.y1+self.r)

      def getDescription(self,db) -> list:
          return [['Position', 'x1=%d, y1=%d' % (self.x1, self.y1)]] + self.getAnnotationsDescription(db)

      def positionInAnnotation(self, position: list) -> bool:
          dist = np.sqrt(np.square(position[0]-self.x1)+np.square(position[1]-self.y1))
          return (dist<=self.r)

      def draw(self, image: np.ndarray, leftUpper: tuple, zoomLevel: float, thickness: int, vp : ViewingProfile):
            xpos1=int((self.x1-leftUpper[0])/zoomLevel)
            ypos1=int((self.y1-leftUpper[1])/zoomLevel)
            radius = int(self.r/zoomLevel)
            if (radius>=0):
                  image = cv2.circle(image, thickness=thickness, center=(xpos1,ypos1), radius=radius,color=self.getColor(vp), lineType=cv2.LINE_AA)

class spotAnnotation(annotation):

      def __init__(self, uid, x1, y1, isSpecialSpot : bool = False):
            super().__init__()
            self.uid = uid
            self.annotationType = AnnotationType.SPOT
            self.x1 = x1
            self.y1 = y1
            if (isSpecialSpot):
                self.annotationType = AnnotationType.SPECIAL_SPOT

      def minCoordinates(self) -> annoCoordinate:
            return annoCoordinate(self.x1-50, self.y1-50)

      def maxCoordinates(self) -> annoCoordinate:
            return annoCoordinate(self.x1+50, self.y1+50)

      def draw(self, image: np.ndarray, leftUpper: tuple, zoomLevel: float, thickness: int, vp : ViewingProfile):
            xpos1=int((self.x1-leftUpper[0])/zoomLevel)
            ypos1=int((self.y1-leftUpper[1])/zoomLevel)
            radius=int(vp.spotCircleRadius/zoomLevel)
            if (radius>=0):
                  image = cv2.circle(image, thickness=thickness, center=(xpos1,ypos1), radius=radius,color=self.getColor(vp), lineType=cv2.LINE_AA)

      def getDescription(self,db) -> list:
          return [['Position', 'x1=%d, y1=%d' % (self.x1, self.y1)]] + self.getAnnotationsDescription(db)

      def positionInAnnotation(self, position: list) -> bool:
          dist = np.sqrt(np.square(position[0]-self.x1)+np.square(position[1]-self.y1))
          return (dist<=25)
