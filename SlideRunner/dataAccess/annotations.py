import cv2
import matplotlib.path as path
import numpy as np
import SlideRunner.general.SlideRunnerPlugin as SlideRunnerPlugin
class AnnotationType(enumerate):
    SPOT = 1
    AREA = 2
    POLYGON = 3
    SPECIAL_SPOT = 4
    CIRCLE = 5
    IMAGEANNOTATION = 6
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
                  [255,200,200,255],
                  [10, 166, 168,255],
                  [166, 10, 168,255],
                  [166,168,10,255]]
    spotCircleRadius = 25
    minimumAnnotationLabelZoom = 4
    majorityClassVote = False
    activeClasses = dict()



class AnnotationLabel(object):
    def __init__(self,annotatorId:int, classId:int, uid:int, exact_id:int=None):
        self.annnotatorId = annotatorId
        self.classId = classId
        self.uid = uid
        self.exact_id = exact_id
    

class annoCoordinate(object):
    x = None
    y = None
    def __init__(self,x,y,x_abs=None,y_abs=None):
        self.x = x
        self.y = y
        self.x_abs = x_abs
        self.y_abs = y_abs
    
    def totuple(self):
        return (self.x, self.y)
    
    def tolist(self):
        return [self.x, self.y]
    
    def __str__(self):
        return f'annoCoordinate at x={self.x}, y={self.y}'

    def __repr__(self):
        return f'annoCoordinate at x={self.x}, y={self.y}'

class AnnotationHandle(object):
    pt1 = None
    pt2 = None

    def __init__(self, pt1:annoCoordinate, pt2:annoCoordinate):
        self.pt1 = pt1
        self.pt2 = pt2

    def positionWithinRectangle(self,position:tuple, absolute:bool=False, tolerance:int=2, zoom:float=1):
        tolerance = tolerance * zoom
        if (absolute):
            return ((position[0]>=self.pt1.x_abs-tolerance) and (position[1]>=self.pt1.y_abs-tolerance) and
                    (position[0]<=self.pt2.x_abs+tolerance) and (position[1]<=self.pt2.y_abs+tolerance))
        else:
            return ((position[0]>=self.pt1.x-tolerance) and (position[1]>=self.pt1.y-tolerance) and
                    (position[0]<=self.pt2.x+tolerance) and (position[1]<=self.pt2.y+tolerance))



class annotation():

      def __init__(self, uid=0, text='',pluginAnnotationLabel=None):
          self.annotationType = AnnotationType.UNKNOWN
          self.labels = list()
          self.uid = uid
          self.text = text if text is not None else ''
          self.agreedClass = None
          self.clickable = True
          self.guid = ''
          self.deleted = 0
          self.lastModified = 0.
          self.minimumAnnotationLabelZoom = 1
          self.pluginAnnotationLabel = None
          if (pluginAnnotationLabel is not None):
              if (isinstance(pluginAnnotationLabel, SlideRunnerPlugin.PluginAnnotationLabel)):
                  self.pluginAnnotationLabel = pluginAnnotationLabel
              else:
                  raise ValueError('pluginAnnotationLabel needs to be of class SlideRunnerPlugin.PluginAnnotationLabel')

      def draw(self, image: np.ndarray, leftUpper: tuple, zoomLevel: float, thickness: int = 1, vp: ViewingProfile = ViewingProfile(), selected=False):
            return
        
      def setAgreedClass(self, agreedClass):
          self.agreedClass = agreedClass
    
      def positionInAnnotation(self, position: list, zoom:float) -> bool:
            return False

      def intersectingWithAnnotation(self, anno) -> bool:
          return self.convertToPath().intersects_path(anno.convertToPath())

      def convertToPath(self):
            return path.Path([])

      def getAnnotationsDescription(self, db) -> list:
           retval = list()
           if (self.pluginAnnotationLabel is None):
                for idx,label in enumerate(self.labels):
                    annotatorName = db.getAnnotatorByID(label.annnotatorId)
                    className = db.getClassByID(label.classId)
                    retval.append(['Anno %d' % (idx+1), '%s (%s)' % (className,annotatorName)])
                retval.append(['Agreed Class', db.getClassByID(self.agreedLabel())])
           else:
                retval.append(['Plugin class', str(self.pluginAnnotationLabel)])
                if (self.text is not None):
                    retval.append(['Description', str(self.text)])

           return retval
          
      def getBoundingBox(self) -> [int,int,int,int]:
        """
            returns the bounding box (x,y,w,h) for an object         
        """
        minC = self.minCoordinates()
        return [minC.x,minC.y] + list(self.getDimensions())

      def positionInAnnotationHandle(self, position: tuple, zoom:float) -> int:
          return None
    
          
          
      def getDescription(self, db, micronsPerPixel=None) -> list:
            if (self.pluginAnnotationLabel is None):
                return self.getAnnotationsDescription(db)
            else:
                return [['Plugin Anno',self.pluginAnnotationLabel.name],]

      def addLabel(self, label:AnnotationLabel, updateAgreed=True):
          self.labels.append(label)
          
          if (updateAgreed):
              self.agreedClass = self.majorityLabel()

      def _create_annohandle(self, image:np.ndarray, coord:tuple, markersize:int, color:tuple, abscoord:tuple=(None,None)) -> AnnotationHandle:
            pt1_rect = (max(0,coord[0]-markersize),
                        max(0,coord[1]-markersize))
            pt2_rect = (min(image.shape[1],coord[0]+markersize),
                        min(image.shape[0],coord[1]+markersize))
            cv2.rectangle(img=image, pt1=(pt1_rect), pt2=(pt2_rect), color=[255,255,255,255], thickness=2)
            cv2.rectangle(img=image, pt1=(pt1_rect), pt2=(pt2_rect), color=color, thickness=1)

            pt1_abs = (abscoord[0]-markersize, abscoord[1]-markersize)
            pt2_abs = (abscoord[0]+markersize, abscoord[1]+markersize)
            return AnnotationHandle(annoCoordinate(*pt1_rect, *pt1_abs), annoCoordinate(*pt2_rect, *pt2_abs))

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
          if (self.agreedClass is not None):
              return self.agreedClass
          else:
              return 0

      
      def labelBy(self, annotatorId):
          for label in np.arange(0, len(self.labels)):
               if (self.labels[label].annnotatorId == annotatorId):
                    return self.labels[label].classId
          return 0
        
      def getColor(self, vp : ViewingProfile):
          if (self.pluginAnnotationLabel is not None):
              return self.pluginAnnotationLabel.color
          if (vp.blindMode):
            return vp.COLORS_CLASSES[self.labelBy(vp.annotator) ]
          elif (vp.majorityClassVote):
            return vp.COLORS_CLASSES[self.majorityLabel() ]
          else:
            return vp.COLORS_CLASSES[self.agreedLabel()]
      
      def minCoordinates(self) -> annoCoordinate:
            print('Whopsy... you need to overload this.')
            return annoCoordinate(None, None)

      def maxCoordinates(self) -> annoCoordinate:
            print('Whopsy... you need to overload this.')
            return annoCoordinate(None, None)


class imageAnnotation(annotation):
      def __init__(self, uid, text='', pluginAnnotationLabel=None, minimumAnnotationLabelZoom=1):
            super().__init__(uid=uid, text=text, pluginAnnotationLabel=pluginAnnotationLabel)
            self.text = text
            self.minimumAnnotationLabelZoom = minimumAnnotationLabelZoom
            self.annotationType = AnnotationType.AREA
            self.clickable=False
    
      def draw(self, image: np.ndarray, leftUpper: tuple, zoomLevel: float, thickness: int, vp : ViewingProfile, selected = False):

            image = cv2.rectangle(image, thickness=thickness, pt1=(0,0), pt2=(image.shape[1],image.shape[0]),color=self.getColor(vp), lineType=cv2.LINE_AA)

            if (len(self.text)>0) and (zoomLevel < self.minimumAnnotationLabelZoom):
                  cv2.putText(image, self.text, (10, 10), cv2.FONT_HERSHEY_PLAIN , 0.7,self.getColor(vp),1,cv2.LINE_AA)
    
      def minCoordinates(self) -> annoCoordinate:
         return annoCoordinate(0,0)
    
      def maxCoordinates(self) -> annoCoordinate:
         return annoCoordinate(np.inf,np.inf)


class rectangularAnnotation(annotation):
      def __init__(self, uid, x1, y1, x2, y2, text='', pluginAnnotationLabel=None, minimumAnnotationLabelZoom=1):
            super().__init__(uid=uid, text=text, pluginAnnotationLabel=pluginAnnotationLabel)
            self.x1 = x1
            self.y1 = y1
            self.x2 = x2
            self.y2 = y2
            self.minimumAnnotationLabelZoom = minimumAnnotationLabelZoom
            self.annotationType = AnnotationType.AREA
            self.text = text
      
      @property
      def coordinates(self):
          return np.array([[self.x1, self.y1], [self.x2, self.y2]])

      def minCoordinates(self) -> annoCoordinate:
            return annoCoordinate(self.x1, self.y1)
      
      def getDescription(self,db, micronsPerPixel=None) -> list:
          return [['Position', 'x1=%d, y1=%d, x2=%d, y2=%d' % (self.x1,self.y1,self.x2,self.y2)]] + self.getAnnotationsDescription(db)

      def maxCoordinates(self) -> annoCoordinate:
            return annoCoordinate(self.x2, self.y2)

      def positionInAnnotation(self, position: list, zoom:float) -> bool:
            return ((position[0]>self.x1) and (position[0]<self.x2) and 
                   (position[1]>self.y1) and (position[1]<self.y2))

      def width(self) -> float:
          return self.x2-self.x1

      def height(self) -> float:
          return self.y2-self.y1
        
      def centerCoordinate(self) -> tuple:
          return annoCoordinate(x=int(0.5*(self.x1+self.x2)),y=int(0.5*(self.y1+self.y2)))

      def convertToPath(self):
          return path.Path(np.array([[self.x1, self.x2, self.x2, self.x1, self.x1] ,[self.y1, self.y1, self.y2, self.y2, self.y1]]).T)

      def draw(self, image: np.ndarray, leftUpper: tuple, zoomLevel: float, thickness: int, vp : ViewingProfile, selected = False):
            xpos1=max(0,int((self.x1-leftUpper[0])/zoomLevel))
            ypos1=max(0,int((self.y1-leftUpper[1])/zoomLevel))
            xpos2=min(image.shape[1],int((self.x2-leftUpper[0])/zoomLevel))
            ypos2=min(image.shape[0],int((self.y2-leftUpper[1])/zoomLevel))

            image = cv2.rectangle(image, thickness=thickness, pt1=(xpos1,ypos1), pt2=(xpos2,ypos2),color=self.getColor(vp), lineType=cv2.LINE_AA)

            if (len(self.text)>0) and (zoomLevel < self.minimumAnnotationLabelZoom):
                  cv2.putText(image, self.text, (xpos1+3, ypos2+10), cv2.FONT_HERSHEY_PLAIN , 0.7,(0,0,0),1,cv2.LINE_AA)

class polygonAnnotation(annotation):
    def __init__(self, uid:int, coordinates: np.ndarray = None, text='', pluginAnnotationLabel=None, minimumAnnotationLabelZoom=1):
        super().__init__(uid=uid, pluginAnnotationLabel=pluginAnnotationLabel, text=text)
        self.annotationType = AnnotationType.POLYGON
        self.annoHandles = list()
        self.minimumAnnotationLabelZoom = minimumAnnotationLabelZoom
        if (coordinates is not None):
            self.coordinates = coordinates
    
    def positionInAnnotationHandle(self, position: tuple, zoom:float) -> int:
        for key,annoHandle in enumerate(self.annoHandles):
             if (annoHandle.positionWithinRectangle(position,absolute=True,zoom=zoom)):
                 return key
        return None

    def minCoordinates(self) -> annoCoordinate:
        return annoCoordinate(self.coordinates[:,0].min(), self.coordinates[:,1].min())

    def maxCoordinates(self) -> annoCoordinate:
        return annoCoordinate(self.coordinates[:,0].max(), self.coordinates[:,1].max())
    
    def area_px(self) -> float:
        print(np.array(self.coordinates).shape,np.array(self.coordinates).dtype)
        return cv2.contourArea(np.int32(np.array(self.coordinates)))

    # Largest diameter --> 2* radius of minimum enclosing circle
    def diameter_px(self) -> float:
        (x,y),radius = cv2.minEnclosingCircle(np.int32(np.array(self.coordinates)))
        return radius*2

    def getDescription(self,db, micronsPerPixel=None) -> list:
        mc = annoCoordinate(self.coordinates[:,0].mean(), self.coordinates[:,1].mean())
        area_px = float(self.area_px())
        diameter_px = float(self.diameter_px())
        micronsPerPixel = float(micronsPerPixel)
        if micronsPerPixel < 2E-6:
            area = '%d px^2' % area_px
            diameter = '%d px' % diameter_px
        else:
            area_mum2 = (area_px*micronsPerPixel*micronsPerPixel)
            diameter_mum = diameter_px*micronsPerPixel
            if (area_mum2 < 1E4):
                area = '%.2f µm^2' % area_mum2
            else:
                area = '%.2f mm^2' % (1E-6 * area_mum2)
            if (diameter_mum < 1e3):
                diameter = '%.2f µm' % diameter_mum
            else:
                diameter = '%.2f mm' % (diameter_mum * 1e-3)

        return [['Position', 'x1=%d, y1=%d' % (mc.x,mc.y)], ['Area', area], ['Largest diameter', diameter]] + self.getAnnotationsDescription(db)

    def convertToPath(self):
        p = path.Path(self.coordinates)
        return p

    def positionInAnnotation(self, position: list, zoom:float) -> bool:
        return self.convertToPath().contains_point(position) or self.positionInAnnotationHandle(position, zoom=zoom) is not None

    def draw(self, image: np.ndarray, leftUpper: tuple, zoomLevel: float, thickness: int, vp : ViewingProfile, selected=False):
        def slideToScreen(pos):
            """
                convert slide coordinates to screen coordinates
            """
            xpos,ypos = pos
            p1 = leftUpper
            cx = int((xpos - p1[0]) / zoomLevel)
            cy = int((ypos - p1[1]) / zoomLevel)
            return (cx,cy)        
        markersize = 4#min(4,int(5/zoomLevel))
        listIdx=-1

        self.annoHandles=list()

        # small assertion to fix bug #12
        if (self.coordinates.shape[1]==0):
            return image

        for listIdx in range(self.coordinates.shape[0]-1):
            anno = slideToScreen(self.coordinates[listIdx])
            cv2.line(img=image, pt1=anno, pt2=slideToScreen(self.coordinates[listIdx+1]), thickness=2, color=self.getColor(vp), lineType=cv2.LINE_AA)       

            if (selected):
                self.annoHandles.append(self._create_annohandle(image, anno, markersize, self.getColor(vp), abscoord=self.coordinates[listIdx]))


        listIdx+=1
        anno = slideToScreen(self.coordinates[listIdx])
        if (selected):
                self.annoHandles.append(self._create_annohandle(image, anno, markersize, self.getColor(vp), abscoord=self.coordinates[listIdx]))

        cv2.line(img=image, pt1=anno, pt2=slideToScreen(self.coordinates[0]), thickness=2, color=self.getColor(vp), lineType=cv2.LINE_AA)       

        if (len(self.text)>0) and (zoomLevel < self.minimumAnnotationLabelZoom):
                xpos1=int(0.5*(np.max(self.coordinates[:,0])+np.min(self.coordinates[:,0]) ))
                ypos1=int(0.5*(np.max(self.coordinates[:,1])+np.min(self.coordinates[:,1])))
                cv2.putText(image, self.text, slideToScreen((xpos1+3, ypos1+10)), cv2.FONT_HERSHEY_PLAIN , 0.7,(0,0,0),1,cv2.LINE_AA)



class circleAnnotation(annotation):
      
      def __init__(self, uid, x1, y1, x2 = None, y2 = None, r = None, text='', pluginAnnotationLabel=None, minimumAnnotationLabelZoom=1):
            super().__init__(uid=uid, text=text, pluginAnnotationLabel=pluginAnnotationLabel)
            self.annotationType = AnnotationType.CIRCLE
            self.minimumAnnotationLabelZoom = minimumAnnotationLabelZoom

            if (r is None):
                self.x1 = int(0.5*(x1+x2))
                self.y1 = int(0.5*(y1+y2))
                if (x2>x1):
                    self.r = int((x2-x1)*0.5)
                else:
                    self.r = int((x1-x2)*0.5)
            else:
                self.x1 = int(x1)
                self.y1 = int(y1)
                self.r = int(r)

      @property
      def coordinates(self):
          return np.array([[self.x1-self.r, self.y1-self.r], [self.x1+self.r, self.y1+self.r]])

      def minCoordinates(self) -> annoCoordinate:
            return annoCoordinate(self.x1-self.r, self.y1-self.r)

      def convertToPath(self):
          pi = np.linspace(0,2*np.pi,100)
          x = np.sin(pi)*self.r+self.x1
          y = np.cos(pi)*self.r+self.y1
          return path.Path(np.c_[x,y])
          

      def maxCoordinates(self) -> annoCoordinate:
            return annoCoordinate(self.x1+self.r, self.y1+self.r)

      def getDescription(self,db, micronsPerPixel=None) -> list:
          return [['Position', 'x1=%d, y1=%d' % (self.x1, self.y1)]] + self.getAnnotationsDescription(db)

      def positionInAnnotation(self, position: list,zoom:float) -> bool:
          dist = np.sqrt(np.square(position[0]-self.x1)+np.square(position[1]-self.y1))
          return (dist<=self.r)

      def draw(self, image: np.ndarray, leftUpper: tuple, zoomLevel: float, thickness: int, vp : ViewingProfile, selected=False):
            xpos1=int((self.x1-leftUpper[0])/zoomLevel)
            ypos1=int((self.y1-leftUpper[1])/zoomLevel)
            radius = int(self.r/zoomLevel)
            if (radius>=0):
                  image = cv2.circle(image, thickness=thickness, center=(xpos1,ypos1), radius=radius,color=self.getColor(vp), lineType=cv2.LINE_AA)
            if (len(self.text)>0) and (zoomLevel < self.minimumAnnotationLabelZoom):
                    cv2.putText(image, self.text, (xpos1,ypos1), cv2.FONT_HERSHEY_PLAIN , 0.7,(0,0,0),1,cv2.LINE_AA)


class spotAnnotation(annotation):

      def __init__(self, uid, x1, y1, isSpecialSpot : bool = False,text='', pluginAnnotationLabel=None, minimumAnnotationLabelZoom=1, radius=None):
            super().__init__(uid=uid, text=text, pluginAnnotationLabel=pluginAnnotationLabel)
            self.annotationType = AnnotationType.SPOT
            self.x1 = x1
            self.y1 = y1
            self.r = 25 if radius is None else radius
            if (isSpecialSpot):
                self.annotationType = AnnotationType.SPECIAL_SPOT
            self.minimumAnnotationLabelZoom = minimumAnnotationLabelZoom

      def minCoordinates(self) -> annoCoordinate:
            return annoCoordinate(self.x1-25, self.y1-25)

      def maxCoordinates(self) -> annoCoordinate:
            return annoCoordinate(self.x1+25, self.y1+25)

      def intersectingWithAnnotation(self, anno) -> bool:
            return False

      @property
      def coordinates(self):
          return np.array([[self.x1-self.r, self.y1-self.r], [self.x1+self.r, self.y1+self.r]])


      def draw(self, image: np.ndarray, leftUpper: tuple, zoomLevel: float, thickness: int, vp : ViewingProfile, selected=False):
            xpos1=int((self.x1-leftUpper[0])/zoomLevel)
            ypos1=int((self.y1-leftUpper[1])/zoomLevel)
            radius=int(int(vp.spotCircleRadius)/zoomLevel)
            if (radius>=0):
                  image = cv2.circle(image, thickness=thickness, center=(xpos1,ypos1), radius=radius,color=self.getColor(vp), lineType=cv2.LINE_AA)
            if (len(self.text)>0) and (zoomLevel < self.minimumAnnotationLabelZoom):
                    cv2.putText(image, self.text, (xpos1+3, ypos1+10), cv2.FONT_HERSHEY_PLAIN , 0.7,(0,0,0),1,cv2.LINE_AA)

      def getDescription(self,db, micronsPerPixel=None) -> list:
          return [['Position', 'x1=%d, y1=%d' % (self.x1, self.y1)]] + self.getAnnotationsDescription(db)

      def positionInAnnotation(self, position: list, zoom:float) -> bool:
          dist = np.sqrt(np.square(position[0]-self.x1)+np.square(position[1]-self.y1))
          return (dist<=25)
