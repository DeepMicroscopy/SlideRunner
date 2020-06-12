"""

    SlideRunner 

    https://www5.cs.fau.de/~aubreville/

   Database functions
"""

import sqlite3
import os
import time
import numpy as np
import random
import uuid



def hex_to_rgb(value):
    value = value.lstrip('#')
    lv = len(value)
    return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

def generate_uuid():
    return str(uuid.uuid4())

def rgb_to_hex(col):
    """
        Assigns one of sliderunners colors to a class
    """
    return '#{:02x}{:02x}{:02x}'.format( *col[0:3] )

def random_color():
    return rgb_to_hex([random.randrange(30,255),random.randrange(30,255),random.randrange(30,255)])

class DatabaseField(object):
    def __init__(self, keyStr:str, typeStr:str, isNull:int=0, isUnique:bool=False, isAutoincrement:bool=False, defaultValue:str='', primaryKey:int=0):
        self.key = keyStr
        self.type = typeStr
        self.isNull = isNull
        self.isUnique = isUnique
        self.isAutoincrement = isAutoincrement
        self.defaultValue = defaultValue
        self.isPrimaryKey = primaryKey

    def creationString(self):
        return ("`"+self.key+"` "+self.type+
                ((" DEFAULT %s " % self.defaultValue) if not(self.defaultValue == "") else "") + 
                (" PRIMARY KEY" if self.isPrimaryKey else "")+
                (" AUTOINCREMENT" if self.isAutoincrement else "")+
                (" UNIQUE" if self.isUnique else "") )


def isActiveClass(label, activeClasses):
        if (label) is None:
            return True
        if (label<len(activeClasses)):
            return activeClasses[label]
        else:
            print('Warning: Assigned label is: ',label,' while class list is: ',activeClasses)
            return 0

class DatabaseTable(object):
    def __init__(self, name:str):
        self.entries = dict()
        self.name = name

    def add(self, field:DatabaseField):
        self.entries[field.key] = field
        return self

    def getCreateStatement(self):
        createStatement = "CREATE TABLE `%s` (" % self.name
        cnt=0
        for idx, entry in self.entries.items():
            if cnt>0:
                createStatement += ','
            createStatement += entry.creationString()
            cnt+=1
        createStatement += ");"
        return createStatement

    def checkTableInfo(self, tableInfo):
        if (tableInfo is None) or (len(tableInfo)==0):
            return False
        allKeys=list()
        for entry in tableInfo:
            idx,key,typeStr,isNull,defaultValue,PK = entry
            if (key not in self.entries):
                return False
            if not (self.entries[key].type == typeStr):
                return False
            allKeys += [key]
        for entry in self.entries:
            if entry not in allKeys:
                return False
        # OK, defaultValue, isNull are not important to be checked

        return True


    def addMissingTableInfo(self, tableInfo, tableName):
        returnStr = list()
        if (tableInfo is None) or (len(tableInfo)==0):
            return False
        allKeys=list()
        for entry in tableInfo:
            idx,key,typeStr,isNull,defaultValue,PK = entry
            allKeys += [key]

        for entry in self.entries.keys():
            if entry not in allKeys:
                returnStr.append('ALTER TABLE %s ADD COLUMN %s' % (tableName, self.entries[entry].creationString()))

        return returnStr


from SlideRunner.dataAccess.annotations import *

from typing import Dict

class Database(object):
    annotations = Dict[int,annotation]

    minCoords = np.empty(0)
    maxCoords = np.empty(0)

    def __init__(self):
        self.dbOpened = False
        self.VA = dict()

        self.databaseStructure = dict()
        self.transformer = None
        self.annotations = dict()       
        self.doCommit = True
        self.annotationsSlide = None
        self.exactUser = 0
        self.databaseStructure['Log'] = DatabaseTable('Log').add(DatabaseField('uid','INTEGER',isAutoincrement=True, primaryKey=1)).add(DatabaseField('dateTime','FLOAT')).add(DatabaseField('labelId','INTEGER'))
        self.databaseStructure['Slides'] = DatabaseTable('Slides').add(DatabaseField('uid','INTEGER',isAutoincrement=True, primaryKey=1)).add(DatabaseField('filename','TEXT')).add(DatabaseField('width','INTEGER')).add(DatabaseField('EXACTUSER','INTEGER',defaultValue=0)).add(DatabaseField('height','INTEGER')).add(DatabaseField('directory','TEXT')).add(DatabaseField('uuid','TEXT')).add(DatabaseField('exactImageID', 'TEXT'))
        self.databaseStructure['Annotations'] = DatabaseTable('Annotations').add(DatabaseField('uid','INTEGER',isAutoincrement=True, primaryKey=1)).add(DatabaseField('guid','TEXT')).add(DatabaseField('deleted','INTEGER',defaultValue=0)).add(DatabaseField('slide','INTEGER')).add(DatabaseField('type','INTEGER')).add(DatabaseField('agreedClass','INTEGER')).add(DatabaseField('lastModified','REAL',defaultValue=str(time.time()))).add(DatabaseField('description','TEXT'))
        self.databaseStructure['Annotations_coordinates'] = DatabaseTable('Annotations_coordinates').add(DatabaseField('uid','INTEGER',isAutoincrement=True, primaryKey=1)).add(DatabaseField('coordinateX','INTEGER')).add(DatabaseField('coordinateY','INTEGER')).add(DatabaseField('coordinateZ','INTEGER',defaultValue=0)).add(DatabaseField('slide','INTEGER')).add(DatabaseField('annoId','INTEGER')).add(DatabaseField('orderIdx','INTEGER'))
        self.databaseStructure['Persons'] = DatabaseTable('Persons').add(DatabaseField('uid','INTEGER',isAutoincrement=True, primaryKey=1)).add(DatabaseField('name','TEXT')).add(DatabaseField('isExactUser','INTEGER', defaultValue=0))
        self.databaseStructure['Classes'] = DatabaseTable('Classes').add(DatabaseField('uid','INTEGER',isAutoincrement=True, primaryKey=1)).add(DatabaseField('name','TEXT')).add(DatabaseField('color','TEXT'))
        self.databaseStructure['Annotations_label'] = DatabaseTable('Annotations_label').add(DatabaseField('uid','INTEGER',isAutoincrement=True, primaryKey=1)).add(DatabaseField('exact_id','INTEGER')).add(DatabaseField('person','INTEGER',defaultValue=0)).add(DatabaseField('class','INTEGER')).add(DatabaseField('annoId','INTEGER'))

    def isOpen(self):
        return self.dbOpened

    def appendToMinMaxCoordsList(self, anno: annotation):
        self.minCoords = np.vstack((self.minCoords, np.asarray(anno.minCoordinates().tolist()+[anno.uid])))
        self.maxCoords = np.vstack((self.maxCoords, np.asarray(anno.maxCoordinates().tolist()+[anno.uid])))
    def generateMinMaxCoordsList(self):
        # MinMaxCoords lists shows extreme coordinates from object, to decide if an object shall be shown
        self.minCoords = np.zeros(shape=(len(self.annotations),3))
        self.maxCoords = np.zeros(shape=(len(self.annotations),3))
        keys = self.annotations.keys() 
        for idx,annokey in enumerate(keys):
            annotation = self.annotations[annokey]
            self.minCoords[idx] = np.asarray(annotation.minCoordinates().tolist()+[annokey])
            self.maxCoords[idx] = np.asarray(annotation.maxCoordinates().tolist()+[annokey])

#        print(self.getVisibleAnnotations([0,0],[20,20]))
    
    def getVisibleAnnotations(self, leftUpper:list, rightLower:list) -> Dict[int, annotation]:
        potentiallyVisible =  ( (self.maxCoords[:,0] > leftUpper[0]) & (self.minCoords[:,0] < rightLower[0]) & 
                                (self.maxCoords[:,1] > leftUpper[1]) & (self.minCoords[:,1] < rightLower[1]) )
        ids = self.maxCoords[potentiallyVisible,2]
        return dict(filter(lambda i:i[0] in ids, self.annotations.items()))

    def setClassColor(self, classId, color:str):
        """
            color: valid hex rgb string, e.g. #AABBCC
            classId: Class ID
        """
        self.execute(f'UPDATE Classes set COLOR="{color}" where uid=={classId}')

    def listOfSlides(self):
        self.execute('SELECT uid,filename from Slides')
        return self.fetchall()

    def listOfSlidesWithExact(self) -> list:
        self.execute('SELECT uid,filename,exactImageID,directory from Slides')
        return self.fetchall()

    def getExactPerson(self) -> (int,str):
        ret = self.execute('SELECT uid,name from Persons where isExactUser=1 LIMIT 1').fetchone()
        if ret is None:
            return 0, ''
        else:
            return ret[0],ret[1]

    def setExactPerson(self, uid):
        self.execute(f'UPDATE Persons set isExactUser=0 where uid != {uid}')
        self.execute(f'UPDATE Persons set isExactUser=1 where uid == {uid}')
        self.commit()
        self.exactUser=uid

    def updateViewingProfile(self, vp:ViewingProfile):
        classes = self.getAllClasses()
        vp.COLORS_CLASSES = { 0: [0,0,0,0] }
        for name,id,color in classes:
            vp.COLORS_CLASSES[id] = [*hex_to_rgb(color),255]
        return vp

    def annotateImage(self, img: np.ndarray, leftUpper: list, rightLower:list, zoomLevel:float, vp : ViewingProfile, selectedAnnoID:int):
        annos = self.getVisibleAnnotations(leftUpper, rightLower)
        self.VA = annos
        for idx,anno in annos.items():
            if (isActiveClass(activeClasses=vp.activeClasses,label=self.classPosition(anno.agreedLabel()))) and not anno.deleted:
                anno.draw(img, leftUpper, zoomLevel, thickness=2, vp=vp, selected=(selectedAnnoID==anno.uid))
    
    def findIntersectingAnnotation(self, anno:annotation, vp: ViewingProfile, database=None, annoType = None):    
        if (database is None):
            database = self.VA            
        for idx,DBanno in database.items():
            if (vp.activeClasses[DBanno.agreedLabel()]):
                if (DBanno.intersectingWithAnnotation(anno ))  and (DBanno.clickable):
                    if (annoType == DBanno.annotationType) or (annoType is None):
                        return DBanno
        return None

    def updateSlideFolder(self, slideUid:int, slidePath:str):
        directory = os.path.dirname(os.path.realpath(slidePath))
        self.execute(f'UPDATE Slides set directory="{directory}" where uid={slideUid}')

    def classPosition(self, classId):
        if (classId==0):
            return 0
        for pos, (name,uid,color) in enumerate(self._allclasses):
            if (uid==classId):
                return pos+1

    def findClickAnnotation(self, clickPosition, vp : ViewingProfile, database=None, annoType = None, zoom:float=1.0):
        if (database is None):
            database = self.VA            
        for idx,anno in database.items():
            if (vp.activeClasses[self.classPosition(anno.agreedLabel())]):
                if (anno.positionInAnnotation(clickPosition, zoom=zoom )) and (anno.clickable):
                    if (annoType == anno.annotationType) or (annoType is None):
                        return anno
        return None

    def getExactIDforSlide(self, slide):
        try:
            return self.execute(f'SELECT exactImageID from Slides where uid=={slide}').fetchone()[0]
        except:
            return ''

    def loadIntoMemory(self, slideId, transformer=None, zLevel=0):
        if not (self.isOpen()):
            return

        self.annotations = dict()
        self.annotationsSlide = slideId
        self.guids = dict()
        self.transformer = transformer
        self.zLevel = zLevel

        if (slideId is None):
            return

        self.dbcur.execute('SELECT uid, type,agreedClass,guid,lastModified,deleted,description FROM Annotations WHERE slide == %d'% slideId)
        allAnnos = self.dbcur.fetchall()


        self.dbcur.execute('SELECT coordinateX, coordinateY, coordinateZ, annoid FROM Annotations_coordinates where annoId IN (SELECT uid FROM Annotations WHERE slide == %d) ORDER BY orderIdx' % (slideId))
        allCoords = np.asarray(self.dbcur.fetchall())

        if self.transformer is not None:
            allCoords = self.transformer(allCoords)

        for uid, annotype,agreedClass,guid,lastModified,deleted,description in allAnnos:
            coords = allCoords[allCoords[:,3]==uid,0:2]
            zCoord = allCoords[allCoords[:,3]==uid,2][0] if allCoords.shape[0]>0 else 0

            if (zCoord != zLevel):
                continue
            if (annotype == AnnotationType.SPOT):
                self.annotations[uid] = spotAnnotation(uid, coords[0][0], coords[0][1], text=description)
            elif (annotype == AnnotationType.SPECIAL_SPOT):
                self.annotations[uid] = spotAnnotation(uid, coords[0][0], coords[0][1], True, text=description)
            elif (annotype == AnnotationType.POLYGON):
                self.annotations[uid] = polygonAnnotation(uid, coords, text=description)
            elif (annotype == AnnotationType.AREA):
                self.annotations[uid] = rectangularAnnotation(uid, coords[0][0], coords[0][1], coords[1][0], coords[1][1], text=description)
            elif (annotype == AnnotationType.CIRCLE):
                self.annotations[uid] = circleAnnotation(uid, coords[0][0], coords[0][1], coords[1][0], coords[1][1], text=description)
            elif (annotype == AnnotationType.IMAGEANNOTATION):
                self.annotations[uid] = imageAnnotation(uid, text=description)
            else:
                print('Unknown annotation type %d found :( ' % annotype)
            self.annotations[uid].agreedClass = agreedClass
            self.annotations[uid].guid = guid
            self.annotations[uid].lastModified = lastModified
            self.annotations[uid].deleted = deleted
            if (deleted):
                self.annotations[uid].clickable = False
            self.guids[guid] = uid
        # Add all labels
        self.dbcur.execute('SELECT annoid, person, class,uid, exact_id FROM Annotations_label WHERE annoID in (SELECT uid FROM Annotations WHERE slide == %d)'% slideId)
        allLabels = self.dbcur.fetchall()

        for (annoId, person, classId,uid, exact_id) in allLabels:
            if (annoId) in self.annotations:
                self.annotations[annoId].addLabel(AnnotationLabel(person, classId, uid, exact_id), updateAgreed=False)


        self.generateMinMaxCoordsList()

            
    

    def checkTableStructure(self, tableName, action='check'):
        self.dbcur.execute('PRAGMA table_info(%s)' % tableName)
        ti = self.dbcur.fetchall()
        if (action=='check'):
            return self.databaseStructure[tableName].checkTableInfo(ti)
        elif (action=='ammend'):
            return self.databaseStructure[tableName].addMissingTableInfo(ti, tableName)

    

    def open(self, dbfilename):
        if os.path.isfile(dbfilename):
            self.db = sqlite3.connect(dbfilename)
            self.dbcur = self.db.cursor()
            self.db.create_function("generate_uuid",0, generate_uuid)
            self.db.create_function("pycurrent_time",0, time.time)
            self.db.create_function("randcolor",0, random_color)

            # Check structure of database and ammend if not proper
            if not self.checkTableStructure('Slides'):
                sql_statements = self.checkTableStructure('Slides','ammend')
                for sql in sql_statements:
                    self.dbcur.execute(sql)
                self.db.commit()

            if not self.checkTableStructure('Persons'):
                sql_statements = self.checkTableStructure('Persons','ammend')
                for sql in sql_statements:
                    self.dbcur.execute(sql)
                self.db.commit()

            if not self.checkTableStructure('Classes'):
                sql_statements = self.checkTableStructure('Classes','ammend')
                for sql in sql_statements:
                    self.dbcur.execute(sql)
                self.db.commit()

            if not self.checkTableStructure('Annotations'):
                sql_statements = self.checkTableStructure('Annotations','ammend')
                for sql in sql_statements:
                    self.dbcur.execute(sql)
                self.db.commit()

            if not self.checkTableStructure('Annotations_coordinates'):
                sql_statements = self.checkTableStructure('Annotations_coordinates','ammend')
                for sql in sql_statements:
                    self.dbcur.execute(sql)
                self.db.commit()

            if not self.checkTableStructure('Annotations_label'):
                sql_statements = self.checkTableStructure('Annotations_label','ammend')
                for sql in sql_statements:
                    self.dbcur.execute(sql)
                self.db.commit()

            if not self.checkTableStructure('Log'):
                # add new log, no problemo.
                self.dbcur.execute('DROP TABLE if exists `Log`')
                self.dbcur.execute(self.databaseStructure['Log'].getCreateStatement())
                self.db.commit()
            
            self.dbOpened = True
            # Migrating vom V0 to V1 needs proper filling of GUIDs
            DBversion = self.dbcur.execute('PRAGMA user_version').fetchone()
            if (DBversion[0]==0):
                self.dbcur.execute('UPDATE Annotations set guid=generate_uuid() where guid is NULL')

                self.addTriggers()

                # Add last polygon point (close the line)
                allpolys = self.dbcur.execute('SELECT uid from Annotations where type==3').fetchall()
                for [polyid,] in allpolys:
                    coords = self.dbcur.execute(f'SELECT coordinateX, coordinateY,slide FROM Annotations_coordinates where annoid=={polyid} and orderidx==1').fetchone()
                    maxidx = self.dbcur.execute(f'SELECT MAX(orderidx) FROM Annotations_coordinates where annoid=={polyid}').fetchone()[0]+1
                    self.dbcur.execute(f'INSERT INTO Annotations_coordinates (coordinateX, coordinateY, slide, annoId, orderIdx) VALUES ({coords[0]},{coords[1]},{coords[2]},{polyid},{maxidx} )')

                DBversion = self.dbcur.execute('PRAGMA user_version = 1')
                print('Successfully migrated DB to version 1')
                self.commit()
                DBversion = self.dbcur.execute('PRAGMA user_version').fetchone()

            if (DBversion[0]==1):
                self.dbcur.execute('UPDATE Classes set color=randcolor() where color is NULL')

                # changed Slides.directory to absolute name
                allslides = self.dbcur.execute('SELECT uid, filename, directory FROM Slides').fetchall()                
                for (uid, filename, pathname) in allslides:
                    pathname = '' if pathname is None else pathname # avoid None problems
                    filename = '' if filename is None else filename
                    dirname = '.' if os.path.dirname(dbfilename) is None else os.path.dirname(dbfilename)
                    candidates = [filename, 
                                  dirname+os.sep+filename,
                                  pathname+os.sep+filename,
                                  dbfilename+os.sep+pathname+os.sep+filename]
                    found=False
                    for cand in candidates:
                        if os.path.exists(cand):
                            fn=filename
                            found=True

                    if found:
                        self.updateSlideFolder(uid, fn)

                self.addTriggers()

                self.dbcur.execute('PRAGMA user_version = 2')
                print('Successfully migrated DB to version 2')
                self.commit()

            if (DBversion[0]==2):
                self.dbcur.execute('PRAGMA user_version = 3')
                print('Successfully migrated DB to version 3')
                self.commit()


            self.dbOpened = True
            self.dbfilename = dbfilename
            self.dbname = os.path.basename(dbfilename)
            self.getAllClasses()


            return self
        else:
            return False
    

    def deleteTriggers(self):
        for event in ['UPDATE','INSERT']:
            self.dbcur.execute(f'DROP TRIGGER IF EXISTS updateAnnotation_fromLabel{event}')
            self.dbcur.execute(f'DROP TRIGGER IF EXISTS updateAnnotation_fromCoords{event}')
            self.dbcur.execute(f'DROP TRIGGER IF EXISTS updateAnnotation_{event}')
            self.dbcur.execute(f'DROP TRIGGER IF EXISTS updateAnnotation_ins')

    def addTriggers(self):
        for event in ['UPDATE','INSERT']:
            self.dbcur.execute(f"""CREATE TRIGGER IF NOT EXISTS updateAnnotation_fromLabel{event}
                        AFTER {event} ON Annotations_label
                        BEGIN
                            UPDATE Annotations SET lastModified=pycurrent_time() where uid==new.annoId;
                        END
                        ;
                        """)

            self.dbcur.execute(f"""CREATE TRIGGER IF NOT EXISTS updateAnnotation_fromCoords{event}
                        AFTER {event} ON Annotations_coordinates
                        BEGIN
                            UPDATE Annotations SET lastModified=pycurrent_time() where uid==new.annoId;
                        END
                        ;
                        """)
            self.dbcur.execute(f"""CREATE TRIGGER IF NOT EXISTS updateAnnotation_{event}
                        AFTER {event} ON Annotations
                        BEGIN
                            UPDATE Annotations SET lastModified=pycurrent_time() where uid==new.uid;
                        END
                        ;
                        """)

        self.dbcur.execute(f"""CREATE TRIGGER IF NOT EXISTS updateAnnotation_ins
                    AFTER INSERT ON Annotations
                    BEGIN
                        UPDATE Annotations SET guid=generate_uuid() where uid==new.uid and guid is Null;
                    END
                    ;
                    """)

        self.dbcur.execute(f"""CREATE TRIGGER IF NOT EXISTS setRandomcolor
                    AFTER INSERT ON Classes
                    BEGIN
                        UPDATE Classes SET color=randcolor() where uid==new.uid and color is Null;
                    END
                    ;
                    """)
    
    # copy database to new file
    def saveTo(self, dbfilename):
        new_db = sqlite3.connect(dbfilename) # create a memory database

        query = "".join(line for line in self.db.iterdump())

        # Dump old database in the new one. 
        new_db.executescript(query)

        return True



    def getUnknownInCurrentScreen(self,leftUpper, rightLower, currentAnnotator) -> annotation:
        visAnnos = self.getVisibleAnnotations(leftUpper, rightLower)
        for anno in visAnnos.keys():
            if (visAnnos[anno].labelBy(currentAnnotator) == 0):
                return anno   
        return None

    def findAllAnnotationLabels(self, uid):
        q = 'SELECT person, class, uid FROM Annotations_label WHERE annoId== %d' % uid
        self.execute(q)
        return self.fetchall()

    def checkIfAnnotatorLabeled(self, uid, person):
        q = 'SELECT COUNT(*) FROM Annotations_label WHERE annoId== %d AND person == %d' % (uid, person)
        self.execute(q)
        return self.fetchone()[0]

    def findClassidOfClass(self, classname):
        q = 'SELECT uid FROM Classes WHERE name == "%s"' % classname
        self.execute(q)
        return self.fetchall()

    def findAllAnnotations(self, annoId, slideUID = None, zLevel=0):
        if (slideUID is None):
            q = 'SELECT coordinateX, coordinateY FROM Annotations_coordinates WHERE annoId==%d' % annoId
        else:
            q = 'SELECT coordinateX, coordinateY FROM Annotations_coordinates WHERE annoId==%d AND slide == %d and coordinateZ == %d' % (annoId, slideUID, zLevel)
        self.execute(q)
        return self.fetchall()    

    def findSlideForAnnotation(self, annoId):
        q = 'SELECT filename FROM Annotations_coordinates LEFT JOIN Slides on Slides.uid == Annotations_coordinates.slide WHERE annoId==%d' % annoId
        self.execute(q)
        return self.fetchall()    


    def pickRandomUnlabeled(self, byAnnotator=0) -> annotation:
        annoIds = list(self.annotations.keys())
        random.shuffle(annoIds)
        for annoId in annoIds:
            if (self.annotations[annoId].labelBy(byAnnotator) == 0):
                return self.annotations[annoId]
        return None



    def setSlideDimensions(self,slideuid,dimensions):
        if dimensions is None:
            return
        if (slideuid is None):
            return
        if (dimensions[0] is None):
            return
        if (dimensions[1] is None):
            return
        print('Setting dimensions of slide ',slideuid,'to',dimensions)
        self.execute('UPDATE Slides set width=%d, height=%d WHERE uid=%d' % (dimensions[0],dimensions[1],slideuid))
        self.db.commit()

    def slideFilenameForID(self, slideuid):
        try:
            return self.execute(f'SELECT filename FROM Slides where uid=={slideuid}').fetchone()[0]
        except:
            return ''

    def setPathForSlide(self, slideuid, slidepath):
        self.execute(f'UPDATE SLIDES set directory="{os.path.dirname(slidepath)}" where uid=={slideuid}')
        self.commit()
        return slideuid

    def findSlideWithFilename(self,slidename,slidepath, uuid:str=None):
        if (slidepath=='') and (os.sep in slidename):
            slidepath,slidename = os.path.split(slidename)

        if (len(slidepath.split(os.sep))>1):
            directory = slidepath.split(os.sep)[-2]
        else:
            directory = slidepath

        ret = self.execute('SELECT uid,directory,uuid,filename from Slides ').fetchall()
#        print('Looking up',slidename,'in',directory)
        secondBest=None
        for (uid,slidedir,suuid,fname) in ret:
            if (uuid is not None) and (suuid==uuid):
                return uid
            elif (fname==slidename):
                if slidedir is None:
                    secondBest=uid
                elif (slidedir.upper() == directory.upper()):
                    return uid 
                elif (os.path.realpath(slidedir).upper() == directory.upper()):
                    return uid
                else:
                    secondBest=uid
        return secondBest
    
    def insertAnnotator(self, name):
        self.execute('INSERT INTO Persons (name) VALUES ("%s")' % (name))
        self.commit()
        query = 'SELECT last_insert_rowid()'
        return self.execute(query).fetchone()[0]

    def changeAllAnnotationLabelsOfType(self, classId:int, annotationType:int, newClassId:int):
        self.execute(f'UPDATE Annotations_label set class={newClassId} where annoid in (SELECT uid from Annotations where type=={annotationType}) and class=={classId}')
        self.execute(f'UPDATE Annotations set agreedClass={newClassId} where uid in (SELECT uid from Annotations where type=={annotationType}) and agreedClass=={classId}')

    def insertClass(self, name):
        self.execute('INSERT INTO Classes (name) VALUES ("%s")' % (name))
        self.commit()
        query = 'SELECT last_insert_rowid()'
        return self.execute(query).fetchone()[0]
    
    def setAgreedClass(self, classId, annoIdx):
        self.annotations[annoIdx].agreedClass = classId
        q = 'UPDATE Annotations SET agreedClass==%d WHERE uid== %d' % (classId,annoIdx)
        self.execute(q)
        self.commit()
         

    def setAnnotationLabel(self,classId,  person, entryId, annoIdx, **kwargs):
        if ('exact_id' in kwargs): # try to keep exact_id, if not explicitly overwritten
            q = f'UPDATE Annotations_label SET person=={person}, class={classId}, exact_id={kwargs["exact_id"]} WHERE uid== {entryId}'
        else:
            q = f'UPDATE Annotations_label SET person=={person}, class={classId} WHERE uid== {entryId}'
            
        self.execute(q)
        self.commit()
        self.annotations[annoIdx].changeLabel(entryId, person, classId)
        
        # check if all labels belong to one class now
        if np.all(np.array([lab.classId for lab in self.annotations[annoIdx].labels])==classId):
            self.setAgreedClass(classId, annoIdx)

        self.checkCommonAnnotation(annoIdx)

    def checkCommonAnnotation(self, annoIdx ):
        allAnnos = self.findAllAnnotationLabels(annoIdx)
        if (len(allAnnos)>0):
            matching = allAnnos[0][1]
            for anno in allAnnos:
                if (anno[1] != matching):
                    matching=0
        else:
            matching=0
        
        q = 'UPDATE Annotations set agreedClass=%d WHERE UID=%d' % (matching, annoIdx)
        self.execute(q)
        self.commit()

    def logLabel(self, labelId):
        query = 'INSERT INTO Log (dateTime, labelId) VALUES (%d, %d)' % (time.time(), labelId)
        self.execute(query)


    def addAnnotationLabel(self,classId,  person, annoId, exact_id:int=None):
        if (exact_id is None):
            exact_id = 'Null'
        query = ('INSERT INTO Annotations_label (person, class, annoId, exact_id) '
                  f'VALUES ({person},{classId},{annoId},{exact_id})')
        self.execute(query)
        query = 'SELECT last_insert_rowid()'
        self.execute(query)
        newid = self.fetchone()[0]
        self.logLabel(newid)

        if annoId in self.annotations: # slide needs to be loaded in order to work
            self.annotations[annoId].addLabel(AnnotationLabel(person, classId, newid, exact_id))

        self.checkCommonAnnotation( annoId)
        self.commit()

    def exchangePolygonCoordinates(self, annoId, slideUID, annoList, zLevel):
        self.annotations[annoId].annotationType = AnnotationType.POLYGON
        self.annotations[annoId].coordinates = np.asarray(annoList)
        self.generateMinMaxCoordsList()

        query = 'DELETE FROM Annotations_coordinates where annoId == %d' % annoId
        self.execute(query)
        self.commit()

        self.insertCoordinates(np.array(annoList), slideUID, annoId, zLevel)
        

    def insertCoordinates(self, annoList:np.ndarray, slideUID, annoId, zLevel):
        """
                Insert an annotation into the database.
                annoList must be a numpy array, but can be either 2 columns or 3 columns (3rd is order)
        """

        if self.transformer is not None:
            annoList = self.transformer(annoList, inverse=True)

        for num, annotation in enumerate(annoList.tolist()):
            query = (f'INSERT INTO Annotations_coordinates (coordinateX, coordinateY, coordinateZ, slide, annoId, orderIdx) VALUES ({annotation[0]},{annotation[1]},{zLevel}, {slideUID},{annoId},{annotation[2] if len(annotation)>2 else num+1})')
            self.execute(query)
        self.commit()

    def setPolygonCoordinates(self, annoId, coords, slideUID, zLevel):
        self.execute(f'DELETE FROM Annotations_coordinates where annoId={annoId}')

        self.insertCoordinates(np.array(coords), slideUID, annoId, zLevel)
        self.commit()

    def insertNewPolygonAnnotation(self, annoList, slideUID, classID, annotator, closed:bool=True, exact_id="Null", description:str='', zLevel:int=0):
        query = 'INSERT INTO Annotations (slide, agreedClass, type, description) VALUES (%d,%d,3,"%s")' % (slideUID,classID, description)
#        query = 'INSERT INTO Annotations (coordinateX1, coordinateY1, coordinateX2, coordinateY2, slide, class1, person1) VALUES (%d,%d,%d,%d,%d,%d, %d)' % (x1,y1,x2,y2,slideUID,classID,annotator)
        if (isinstance(annoList, np.ndarray)):
            annoList=annoList.tolist()
        if (closed):
            annoList.append(annoList[0])
        self.execute(query)
        query = 'SELECT last_insert_rowid()'
        self.execute(query)
        annoId = self.fetchone()[0]
        assert(len(annoList)>0)
        self.annotations[annoId] = polygonAnnotation(annoId, np.asarray(annoList))
        self.appendToMinMaxCoordsList(self.annotations[annoId])
        self.insertCoordinates(np.array(annoList), slideUID, annoId, zLevel)

        self.addAnnotationLabel(classId=classID, person=annotator, annoId=annoId, exact_id=exact_id)

        self.commit()
        return annoId

        

    def addAnnotationToDatabase(self, anno:annotation, slideUID:int, classID:int, annotatorID:int, zLevel:int, description:str=''):
        if (anno.annotationType == AnnotationType.AREA):
            self.insertNewAreaAnnotation(anno.x1,anno.y1,anno.x2,anno.y2,slideUID,classID, annotatorID,description=description, zLevel=zLevel)
        elif (anno.annotationType == AnnotationType.POLYGON):
            self.insertNewPolygonAnnotation(anno.coordinates, slideUID, classID, annotatorID, description=description, zLevel=zLevel)
        elif (anno.annotationType == AnnotationType.CIRCLE):
            coords = anno.coordinates
            self.insertNewAreaAnnotation(coords[0],coords[1],coords[2],coords[3],slideUID,classID, annotatorID, typeId=5,description=description, zLevel=zLevel)
        elif (anno.annotationType == AnnotationType.SPOT):
            self.insertNewSpotAnnotation(anno.x1, anno.y1, slideUID, classID, annotatorID, description=description, zLevel=zLevel)
        elif (anno.annotationType == AnnotationType.SPECIAL_SPOT):
            self.insertNewSpotAnnotation(anno.x1, anno.y1, slideUID, classID, annotatorID, type=4, description=description, zLevel=zLevel)
        

    def getGUID(self, annoid) -> str:
        try:
            return self.execute(f'SELECT guid from Annotations where uid=={annoid}').fetchone()[0]
        except:
            return None

    def insertNewAreaAnnotation(self, x1,y1,x2,y2, slideUID, classID, annotator, typeId=2, uuid=None, exact_id="Null", description="", zLevel=0):
        if (uuid is None):
            query = 'INSERT INTO Annotations (slide, agreedClass, type, description) VALUES (%d,%d,%d,"%s")' % (slideUID,classID, typeId, description)
        else:
            query = 'INSERT INTO Annotations (slide, agreedClass, type, guid, description) VALUES (%d,%d,%d,"%s","%s")' % (slideUID,classID, typeId, uuid,description)
#        query = 'INSERT INTO Annotations (coordinateX1, coordinateY1, coordinateX2, coordinateY2, slide, class1, person1) VALUES (%d,%d,%d,%d,%d,%d, %d)' % (x1,y1,x2,y2,slideUID,classID,annotator)
        self.execute(query)
        query = 'SELECT last_insert_rowid()'
        self.execute(query)
        annoId = self.fetchone()[0]
        if (typeId==2):
            self.annotations[annoId] = rectangularAnnotation(annoId, x1,y1,x2,y2)
        else:
            self.annotations[annoId] = circleAnnotation(annoId, x1,y1,x2,y2)
        
        self.appendToMinMaxCoordsList(self.annotations[annoId])

        annoList = np.array([[x1,y1,1],[x2,y2,2]])
        self.insertCoordinates(np.array(annoList), slideUID, annoId, zLevel)
        
        self.addAnnotationLabel(classId=classID, person=annotator, annoId=annoId, exact_id=exact_id)

        self.commit()
        return annoId

    def setLastModified(self, annoid:int, lastModified:float):
        self.execute(f'UPDATE Annotations SET lastModified="{lastModified}" where uid={annoid}')
        self.annotations[annoid].lastModified = lastModified

    def setGUID(self, annoid:int, guid:str):
        self.execute(f'UPDATE Annotations SET guid="{guid}" where uid={annoid}')
        self.guids[guid]=annoid
    
    def last_inserted_id() -> int:
            query = 'SELECT last_insert_rowid()'
            self.execute(query)
            return self.fetchone()[0]

    def removeImageAnnotation(self, slideUID:int, zLevel:int, annotator:int, exact_id="Null"):
        query = f'SELECT annoId FROM Annotations_coordinates where coordinateX IS NULL and coordinateY IS NULL and coordinateZ=={zLevel} and slide=={slideUID} and annoID in (SELECT annoID FROM Annotations_label where person=={annotator})'
        # delete all previous labels by current annotator
        self.execute(query)
        for [aid,] in self.fetchall():
            self.removeAnnotation(aid)


    def insertNewImageAnnotation(self, slideUID:int, zLevel:int, classID:int, annotator:int, exact_id="Null", description:str=''):

        self.removeImageAnnotation(slideUID=slideUID, zLevel=zLevel, annotator=annotator)

        query = 'INSERT INTO Annotations (slide,agreedClass,type,description) VALUES (%d,0,%d, "%s")' % (slideUID, AnnotationType.IMAGEANNOTATION,description)
        self.execute(query)
        query = 'SELECT last_insert_rowid()'
        self.execute(query)
        annoId = self.fetchone()[0]
        self.annotations[annoId] = imageAnnotation(annoId)
        self.insertCoordinates(np.array([['Null', 'Null',1]]), slideUID, annoId, zLevel)
        self.addAnnotationLabel(classId=classID, person=annotator, annoId=annoId, exact_id=exact_id)
        self.appendToMinMaxCoordsList(self.annotations[annoId])



    def insertNewSpotAnnotation(self,xpos_orig,ypos_orig, slideUID, classID, annotator, type = 1, exact_id="Null", description:str='', zLevel=0):

        if (type == 4):
            query = 'INSERT INTO Annotations (slide, agreedClass, type,description) VALUES (%d,0,%d, "%s")' % (slideUID, type,description)
            self.execute(query)
            query = 'SELECT last_insert_rowid()'
            self.execute(query)
            annoId = self.fetchone()[0]

            self.insertCoordinates(np.array([[xpos_orig, ypos_orig,1]]), slideUID, annoId, zLevel)
            self.annotations[annoId] = spotAnnotation(annoId, xpos_orig,ypos_orig, (type==4))

        else:
            query = 'INSERT INTO Annotations (slide, agreedClass, type, description) VALUES (%d,%d,%d,"%s")' % (slideUID,classID, type,description)
            self.execute(query)
            query = 'SELECT last_insert_rowid()'
            self.execute(query)
            annoId = self.fetchone()[0]

            self.insertCoordinates(np.array([[xpos_orig, ypos_orig,1]]), slideUID, annoId, zLevel)
            self.execute(query)

            self.annotations[annoId] = spotAnnotation(annoId, xpos_orig,ypos_orig, (type==4))
            self.addAnnotationLabel(classId=classID, person=annotator, annoId=annoId, exact_id=exact_id)

        self.appendToMinMaxCoordsList(self.annotations[annoId])
        self.commit()
        return annoId

    def removeFileFromDatabase(self, fileUID:str):
        self.execute('DELETE FROM Annotations_label where annoID IN (SELECT uid FROM Annotations where slide == %d)' % fileUID)
        self.execute('DELETE FROM Annotations_coordinates where annoID IN (SELECT uid FROM Annotations where slide == %d)' % fileUID)
        self.execute('DELETE FROM Annotations where slide == %d' % fileUID)
        self.execute('DELETE FROM Slides where uid == %d' % fileUID)
        self.commit()

    def removeAnnotationLabel(self, labelIdx, annoIdx):
            q = 'DELETE FROM Annotations_label WHERE uid == %d' % labelIdx
            self.execute(q)
            self.annotations[annoIdx].removeLabel(labelIdx)
            self.commit()
            self.checkCommonAnnotation(annoIdx)

    def updatePolygonPoint(self, annoId, orderIdx, coords):
        self.execute(f'UPDATE Annotations_coordinates SET coordinateX={coords[0]}, coordinateY={coords[1]} where annoId=={annoId} and orderIdx=={orderIdx}+1')
        self.commit()

    def removePolygonPoint(self, annoId:int, coord_idx:int):
        self.execute(f'DELETE FROM Annotations_coordinates where annoId=={annoId} and orderIdx=={coord_idx}+1')
        self.execute(f'UPDATE Annotations_coordinates SET orderidx=orderidx-1 where annoId=={annoId} and orderIdx>{coord_idx}')
        retain = [np.arange(0,coord_idx).tolist()+np.arange(coord_idx+1,self.annotations[annoId].coordinates.shape[0]).tolist()]
        self.annotations[annoId].coordinates = self.annotations[annoId].coordinates[retain,:][0,:,:]
        self.commit()

    def changeAnnotationID(self, annoId:int, newAnnoID:int):
            self.execute('SELECT COUNT(*) FROM Annotations where uid == (%d)' % newAnnoID)
            if (self.fetchone()[0] > 0):
                return False

            self.execute('UPDATE Annotations_label SET annoId = %d WHERE annoId == %d' % (newAnnoID,annoId))
            self.execute('UPDATE Annotations_coordinates SET annoId = %d WHERE annoId == %d' % (newAnnoID,annoId))
            self.execute('UPDATE Annotations SET uid= %d WHERE uid == %d ' % (newAnnoID,annoId))
            self.annotations[annoId].uid = newAnnoID
            self.annotations[newAnnoID] = self.annotations[annoId]
            self.annotations.pop(annoId)
            self.appendToMinMaxCoordsList(self.annotations[newAnnoID])
            self.commit()
            return True


    def removeAnnotation(self, annoId, onlyMarkDeleted:bool=True):
            if (onlyMarkDeleted):
                self.execute('UPDATE Annotations SET deleted=1 WHERE uid == '+str(annoId))
                self.annotations[annoId].deleted = 1
                self.annotations[annoId].clickable = 0
            else:
                self.execute('DELETE FROM Annotations_label WHERE annoId == %d' % annoId)
                self.execute('DELETE FROM Annotations_coordinates WHERE annoId == %d' % annoId)
                self.execute('DELETE FROM Annotations WHERE uid == '+str(annoId))
                self.annotations.pop(annoId)
            self.commit()
            

    def insertNewSlide(self,slidename:str,slidepath:str,uuid:str=""):
            if (len(slidepath.split(os.sep))>1):
                directory = os.path.dirname(os.path.realpath(slidepath))
            else:
                directory = ''
            self.execute('INSERT INTO Slides (filename,directory,uuid) VALUES ("%s","%s", "%s")' % (slidename,directory,uuid))
            self.commit()
            query = 'SELECT last_insert_rowid()'
            return self.execute(query).fetchone()[0]


    def fetchall(self):
        if (self.isOpen()):
            return self.dbcur.fetchall()
        else:
            print('Warning: DB not opened for fetch.')

    def fetchone(self):
        if (self.isOpen()):
            return self.dbcur.fetchone()
        else:
            print('Warning: DB not opened for fetch.')

    def execute(self, query):
        if (self.isOpen()):
            try:
                return self.dbcur.execute(query)
            except Exception as e:
                import sys
                raise type(e)(str(e) +
                      ' Failed query was: %s' % query).with_traceback(sys.exc_info()[2])
        else:
            print('Warning: DB not opened.')

    def getDBname(self):
        if (self.dbOpened):
            return self.dbname
        else:
            return ''
    
    def getAnnotatorByID(self, id):
        if (id is None):
            return ''
        self.execute('SELECT name FROM Persons WHERE uid == %d' % id)
        fo = self.fetchone()
        if (fo is not None):
            return fo[0]
        else:
            return ''

    def getClassByID(self, id):
        try:
            self.execute('SELECT name FROM Classes WHERE uid == %d' % id)
            return self.fetchone()[0]
        except:
            return '-unknown-'+str(id)+'-'


    def getAllPersons(self):
        self.execute('SELECT name, uid FROM Persons ORDER BY uid')
        return self.fetchall()

    def getAllClasses(self):
        self.execute('SELECT name,uid,color FROM Classes ORDER BY uid')
        self._allclasses = self.fetchall() # save for later
        return self._allclasses
    
    def renameClass(self, classID, name):
        self.execute('UPDATE Classes set name="%s" WHERE uid ==  %d' % (name, classID))
        self.commit()

    def deleteClass(self, classID):
        self.execute('DELETE FROM Classes WHERE uid ==  %d' % ( classID))
        self.execute('UPDATE Annotations set agreedClass=0 WHERE agreedClass ==  %d' % ( classID))
        self.execute('DELETE FROM Annotations_label WHERE class ==  %d' % ( classID))
        self.commit()

    def commit(self):
        return self.db.commit()

    def countEntryPerClass(self, slideID = 0):
        retval = {'unknown' :  {'uid': 0, 'count_total':0, 'count_slide':0}}
        self.dbcur.execute('SELECT Classes.uid, COUNT(*), name FROM Annotations LEFT JOIN Classes on Classes.uid == Annotations.agreedClass where Annotations.deleted == 0 GROUP BY Classes.uid')
        allClasses = self.dbcur.fetchall()
    
        classids = np.zeros(len(allClasses))        
        for idx,element in enumerate(allClasses):
                name = element[2] if element[2] is not None else 'unknown'
                
                retval[name] = {'uid': element[0], 'count_total':element[1], 'count_slide':0}
        uidToName = {uid:name for uid,_,name in allClasses}


        if (slideID is not None):

            self.dbcur.execute('SELECT Classes.uid, COUNT(*), name FROM Annotations LEFT JOIN Classes on Classes.uid == Annotations.agreedClass where slide==%d and deleted==0 GROUP BY Classes.uid' % slideID)
            allClasses = self.dbcur.fetchall()
            
            for uid,cnt,name in allClasses:
                name = 'unknown' if name is None else name
                if name not in retval:
                    retval[name] = {'uid': 0, 'count_total':0, 'count_slide':0}
                retval[name]['count_slide'] = cnt

        return retval


    def countEntries(self):
        self.dbcur.execute('SELECT COUNT(*) FROM Annotations where deleted==0')
        num1 = self.dbcur.fetchone()

        return num1[0]

    def fetchSpotAnnotation(self,entryId=0):
        self.dbcur.execute('SELECT coordinateX, coordinateY FROM Annotations_coordinates WHERE annoId ==  '+str(entryId))
        coords = self.dbcur.fetchone()
        
        class1,class2,person1,person2=None,None,None,None
        self.dbcur.execute('SELECT Classes.name FROM Annotations_label LEFT JOIN Classes on Annotations_label.class == Classes.uid WHERE Annotations_label.annoId ==  '+str(entryId))
        classes = self.dbcur.fetchall()

        self.dbcur.execute('SELECT Persons.name FROM Annotations_label LEFT JOIN Persons on Annotations_label.person == Persons.uid WHERE Annotations_label.annoId ==  '+str(entryId))
        persons = self.dbcur.fetchall()

        return coords, classes, persons

    def fetchAreaAnnotation(self,entryId=0):
        self.dbcur.execute('SELECT coordinateX, coordinateY FROM Annotations_coordinates WHERE annoId ==  '+str(entryId)+' ORDER BY Annotations_coordinates.orderIdx')
        coords1 = self.dbcur.fetchone()
        coords2 = self.dbcur.fetchone()
        
        class1,class2,person1,person2=None,None,None,None
        self.dbcur.execute('SELECT Classes.name FROM Annotations_label LEFT JOIN Classes on Annotations_label.class == Classes.uid WHERE Annotations_label.annoId ==  '+str(entryId))
        classes = self.dbcur.fetchall()

        self.dbcur.execute('SELECT Persons.name FROM Annotations_label LEFT JOIN Persons on Annotations_label.person == Persons.uid WHERE Annotations_label.annoId ==  '+str(entryId))
        persons = self.dbcur.fetchall()

        return coords1, coords2, classes, persons

    

    def create(self,dbfilename) -> bool:
 
        if (os.path.isfile(dbfilename)):
             # ok, remove old file
            os.remove(dbfilename)

        try:
            tempdb = sqlite3.connect(dbfilename)
        except sqlite3.OperationalError:
            return False

        tempcur = tempdb.cursor()
        tempdb.create_function("randcolor",0, random_color)

        tempcur.execute('CREATE TABLE `Annotations_label` ('
            '	`uid`	INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,'
            '	`person`	INTEGER,'
            '	`class`	INTEGER,'
            '   `exact_id` INTEGER,'
            '	`annoId`	INTEGER'
            ');')
        
        tempcur.execute('CREATE TABLE `Annotations_coordinates` ('
            '`uid`	INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,'
            '`coordinateX`	INTEGER,'
            '`coordinateY`	INTEGER,'
            '`coordinateZ`	INTEGER DEFAULT 0,'
            '`slide`	INTEGER,'
            '`annoId`	INTEGER,'
            '`orderIdx`	INTEGER'
            ');')

        tempcur.execute('CREATE TABLE `Annotations` ('
            '`uid`	INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,'
            '`slide`	INTEGER,'
           	'`guid`	TEXT,'
            f'`lastModified`	REAL DEFAULT {time.time()},'
         	'`deleted`	INTEGER DEFAULT 0,'
            '`type`	INTEGER,'
            '`agreedClass`	INTEGER,'
            '`description` TEXT'
            ');')

        tempcur.execute('CREATE TABLE `Classes` ('
            '`uid`	INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,'
            '`name`	TEXT,'
            '`color` TEXT'
            ');')
        
        tempcur.execute('CREATE TABLE `Persons` ('
            '`uid`	INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,'
            '`name`	TEXT,'
            '`isExactUser` INTEGER DEFAULT 0'
            ');')

        tempcur.execute('CREATE TABLE `Slides` ('
            '`uid`	INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,'
            '`filename`	TEXT,'
            '`width`	INTEGER,'
            '`height`	INTEGER,'
            '`directory` TEXT,'
            '`uuid` TEXT,'
            '`exactImageID` TEXT'
            ');')

        tempdb.commit()
        self.db = tempdb
        self.dbcur = self.db.cursor()
        self.dbcur.execute('PRAGMA user_version = 1')
        self.db.create_function("generate_uuid",0, generate_uuid)
        self.db.create_function("pycurrent_time",0, time.time)
        self.dbfilename = dbfilename
        self.dbcur.execute(self.databaseStructure['Log'].getCreateStatement())
        self.annotations = dict()
        self.dbname = os.path.basename(dbfilename)
        self.dbOpened=True
        self.generateMinMaxCoordsList()
        self.addTriggers()

        return self
