"""

    SlideRunner 

    https://www5.cs.fau.de/~aubreville/

   Database functions
"""

import sqlite3
import os
import time
import numpy as np

class Database(object):
    def __init__(self):
        self.dbOpened = False

    def isOpen(self):
        return self.dbOpened

    def open(self, dbfilename):
        if os.path.isfile(dbfilename):
            self.db = sqlite3.connect(dbfilename)
            self.dbcur = self.db.cursor()
            self.dbOpened = True
            self.dbfilename = dbfilename
            self.dbname = os.path.basename(dbfilename)
            return True
        else:
            return False

    def findSpotAnnotations(self,leftUpper, rightLower, slideUID, blinded = False, currentAnnotator=None):
        q = ('SELECT coordinateX, coordinateY, agreedClass,Annotations_coordinates.uid,annoId,type FROM Annotations_coordinates LEFT JOIN Annotations on Annotations.uid == Annotations_coordinates.annoId WHERE coordinateX >= '+str(leftUpper[0])+
                ' AND coordinateX <= '+str(rightLower[0])+' AND coordinateY >= '+str(leftUpper[1])+' AND coordinateY <= '+str(rightLower[1])+
                ' AND Annotations.slide == %d AND (type==1 OR type==4)'%(slideUID) )
        if not blinded:
            self.execute(q)
            return self.fetchall()
    
        q=(' SELECT coordinateX, coordinateY,0,uid,annoId,1 from Annotations_coordinates WHERE coordinateX >= '+str(leftUpper[0])+
                 ' AND coordinateX <= '+str(rightLower[0])+' AND coordinateY >= '+str(leftUpper[1])+' AND coordinateY <= '+str(rightLower[1])+' AND slide == %d;' % slideUID)
                
        self.execute(q)
        resp = np.asarray(self.fetchall())

        if (resp.shape[0]==0):
            return list()


        self.execute('SELECT annoId, class from Annotations_label WHERE person==%d' % currentAnnotator)
        myAnnos = np.asarray(self.fetchall())

        if (myAnnos.shape[0]==0):
            myOnes = np.zeros(resp.shape).astype(np.bool)
            mineInAll = np.empty(0)
        else:
            myOnes = np.in1d(resp[:,4],myAnnos[:,0])
            mineInAll = np.in1d(myAnnos[:,0],resp[:,4])

        if mineInAll.shape[0]>0:
            resp[myOnes,2] = myAnnos[mineInAll,1]

        self.execute('SELECT uid,type from Annotations WHERE type IN (1,4) AND slide == %d'% slideUID)
        correctTypeUIDs = np.asarray(self.fetchall())
        if (correctTypeUIDs.shape[0]==0):
            return list() # No annotation with correct type available

        typeFilter = np.in1d(resp[:,4], correctTypeUIDs[:,0])
        assignType = np.in1d(correctTypeUIDs[:,0], resp[:,4])
        resp[:,5] = correctTypeUIDs[assignType,1]
        return resp[typeFilter,:].tolist()
 

    def checkIfUnknownAreInScreen(self,leftUpper, rightLower, slideUID, currentAnnotator):
        q = ('SELECT COUNT(*) FROM '
             'Annotations_coordinates LEFT JOIN Annotations on Annotations.uid == Annotations_coordinates.'
             'annoId WHERE coordinateX >= '+str(leftUpper[0])+
                ' AND coordinateX <= '+str(rightLower[0])+' AND coordinateY >= '+str(leftUpper[1])+' AND coordinateY <= '+str(rightLower[1])+
                ' AND Annotations.slide == %d AND type==1 AND Annotations.uid NOT IN ( SELECT Annotations_label.annoId from Annotations_label WHERE person==%d group by annoId )'%(slideUID,currentAnnotator) )
        self.execute(q)
        otherLabels = self.fetchone()[0]
        return otherLabels>0      

    def findAllAnnotationLabels(self, uid):
        q = 'SELECT person, class, uid FROM Annotations_label WHERE annoId== %d' % uid
        self.execute(q)
        return self.fetchall()

    def checkIfAnnotatorLabeled(self, uid, person):
        q = 'SELECT COUNT(*) FROM Annotations_label WHERE annoId== %d AND person == %d' % (uid, person)
        self.execute(q)
        return self.fetchone()[0]

    def findAllAnnotations(self, annoId):
        q = 'SELECT coordinateX, coordinateY FROM Annotations_coordinates WHERE annoId==%d' % annoId
        self.execute(q)
        return self.fetchall()    

    def pickRandomUnlabeled(self, slideID, type = 1, byAnnotator=0):
        q = ('SELECT coordinateX, coordinateY, Annotations.uid '
             'FROM Annotations_coordinates LEFT JOIN Annotations on Annotations.uid == Annotations_coordinates.annoId '
             'WHERE Annotations.slide == %d AND type==%d ' % (slideID, type) +
             'AND Annotations.uid NOT IN ( SELECT Annotations_label.annoId from Annotations_label WHERE person==%d group by annoId ) ' % byAnnotator +
             'ORDER BY RANDOM() LIMIT 1') 
        self.execute(q)
        ret = self.fetchone()
        if (ret is None):
            return None,None,None
        else:
            [cx,cy,annoId] = ret
            return [cx,cy,annoId]
        

    def findPolygonAnnotatinos(self,leftUpper,rightLower, slideUID,blinded = False, currentAnnotator=None):
        if not blinded:
            q = ('SELECT agreedClass,annoId FROM Annotations_coordinates LEFT JOIN Annotations on Annotations.uid == Annotations_coordinates.annoId WHERE coordinateX >= '+str(leftUpper[0])+
                ' AND coordinateX <= '+str(rightLower[0])+' AND coordinateY >= '+str(leftUpper[1])+' AND coordinateY <= '+str(rightLower[1])+
                ' AND Annotations.slide == %d AND type==3 '%(slideUID) +' GROUP BY Annotations_coordinates.annoId')
            self.execute(q)
            farr = self.fetchall()
        else:
            q = ('SELECT 0,annoId FROM Annotations_coordinates LEFT JOIN Annotations on Annotations.uid == Annotations_coordinates.annoId WHERE coordinateX >= '+str(leftUpper[0])+
                ' AND coordinateX <= '+str(rightLower[0])+' AND coordinateY >= '+str(leftUpper[1])+' AND coordinateY <= '+str(rightLower[1])+
                ' AND Annotations.slide == %d AND type==3 '%(slideUID) +' AND Annotations.uid NOT IN (SELECT annoId FROM Annotations_label WHERE person==%d GROUP BY annoID) GROUP BY Annotations_coordinates.annoId' % currentAnnotator)
            self.execute(q)
            farr1 = self.fetchall()

            q = ('SELECT class,Annotations_label.annoId FROM Annotations_coordinates LEFT JOIN Annotations on Annotations.uid == Annotations_coordinates.annoId LEFT JOIN Annotations_label ON Annotations_label.annoId == Annotations.uid WHERE coordinateX >= '+str(leftUpper[0])+
                ' AND coordinateX <= '+str(rightLower[0])+' AND coordinateY >= '+str(leftUpper[1])+' AND coordinateY <= '+str(rightLower[1])+
                ' AND Annotations.slide == %d AND type==3 '%(slideUID) +' AND Annotations_label.person == %d GROUP BY Annotations_coordinates.annoId' % currentAnnotator)
            self.execute(q)
            farr2 = self.fetchall()

            farr = farr1+farr2


        polysets = []
        
        toggler=True
        for entryOuter in range(len(farr)):
            # find all annotations for area:
            allAnnos = self.findAllAnnotations(farr[entryOuter][1])
            polygon = list()
            for entry in np.arange(0,len(allAnnos),1):
                polygon.append([allAnnos[entry][0],allAnnos[entry][1]])
            polygon.append([allAnnos[0][0],allAnnos[0][1]]) # close polygon
            polysets.append((polygon,farr[entryOuter][0],farr[entryOuter][1] ))

        return polysets

    def findAreaAnnotations(self,leftUpper, rightLower, slideUID, blinded = False, currentAnnotator = 0):
        if not blinded:
            q = ('SELECT agreedClass,annoId, type FROM Annotations_coordinates LEFT JOIN Annotations on Annotations.uid == Annotations_coordinates.annoId WHERE coordinateX >= '+str(leftUpper[0])+
                ' AND coordinateX <= '+str(rightLower[0])+' AND coordinateY >= '+str(leftUpper[1])+' AND coordinateY <= '+str(rightLower[1])+
                ' AND Annotations.slide == %d AND type IN (2,5) '%(slideUID) +' GROUP BY Annotations_coordinates.annoId')

            self.execute(q)
            farr = self.fetchall()
        else:
            q = ('SELECT 0,annoId,type FROM Annotations_coordinates LEFT JOIN Annotations on Annotations.uid == Annotations_coordinates.annoId WHERE coordinateX >= '+str(leftUpper[0])+
                ' AND coordinateX <= '+str(rightLower[0])+' AND coordinateY >= '+str(leftUpper[1])+' AND coordinateY <= '+str(rightLower[1])+
                ' AND Annotations.slide == %d AND type IN (2,5) '%(slideUID) +' AND Annotations.uid NOT IN (SELECT annoId FROM Annotations_label WHERE person==%d GROUP BY annoID) GROUP BY Annotations_coordinates.annoId' % currentAnnotator)

            self.execute(q)
            farr1 = self.fetchall()

            q = ('SELECT class,Annotations_label.annoId,type FROM Annotations_coordinates LEFT JOIN Annotations on Annotations.uid == Annotations_coordinates.annoId LEFT JOIN Annotations_label ON Annotations_label.annoId == Annotations.uid WHERE coordinateX >= '+str(leftUpper[0])+
                ' AND coordinateX <= '+str(rightLower[0])+' AND coordinateY >= '+str(leftUpper[1])+' AND coordinateY <= '+str(rightLower[1])+
                ' AND Annotations.slide == %d AND type IN (2,5) '%(slideUID) +' AND Annotations_label.person == %d GROUP BY Annotations_coordinates.annoId' % currentAnnotator)

            self.execute(q)
            farr2 = self.fetchall()

            farr = farr1+farr2
            
        reply = []
        toggler=True
        for entryOuter in range(len(farr)):
            # find all annotations for area:
            allAnnos = self.findAllAnnotations(farr[entryOuter][1])
            for entry in np.arange(0,len(allAnnos),2):
                reply.append([allAnnos[entry][0],allAnnos[entry][1],allAnnos[entry+1][0],allAnnos[entry+1][1],farr[entryOuter][0],farr[entryOuter][1],farr[entryOuter][2]])
            # tuple: x1,y1,x2,y2,class,annoId ID, type
        return reply
#        return self.fetchall()


    def findSlideWithFilename(self,slidename):
            self.execute('SELECT uid from Slides WHERE filename == "'+slidename+'"')
            ret = self.fetchone()
            if (ret is None):
                return None
            else:
                return ret[0]
    
    def insertAnnotator(self, name):
        self.execute('INSERT INTO Persons (name) VALUES ("%s")' % (name))
        self.commit()

    def insertClass(self, name):
        self.execute('INSERT INTO Classes (name) VALUES ("%s")' % (name))
        self.commit()
    
    def setAnnotationLabel(self,classId,  person, entryId, annoIdx):
        q = 'UPDATE Annotations_label SET person==%d, class=%d WHERE uid== %d' % (person,classId,entryId)
        self.execute(q)
        self.commit()
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


    def addAnnotationLabel(self,classId,  person, annoId):
        query = ('INSERT INTO Annotations_label (person, class, annoId) VALUES (%d,%d,%d)'
                 % (person, classId, annoId))
        self.execute(query)
        self.checkCommonAnnotation( annoId)
        self.commit()

    def insertNewPolygonAnnotation(self, annoList, slideUID, classID, annotator):
        query = 'INSERT INTO Annotations (slide, agreedClass, type) VALUES (%d,%d,3)' % (slideUID,classID)
#        query = 'INSERT INTO Annotations (coordinateX1, coordinateY1, coordinateX2, coordinateY2, slide, class1, person1) VALUES (%d,%d,%d,%d,%d,%d, %d)' % (x1,y1,x2,y2,slideUID,classID,annotator)
        self.execute(query)
        query = 'SELECT last_insert_rowid()'
        self.execute(query)
        annoId = self.fetchone()[0]

        for annotation in annoList:
            query = ('INSERT INTO Annotations_coordinates (coordinateX, coordinateY, slide, annoId, orderIdx) VALUES (%d,%d,%d,%d,%d)'
                    % (annotation[0],annotation[1],slideUID, annoId, 1))
            self.execute(query)

        self.addAnnotationLabel(classId=classID, person=annotator, annoId=annoId)

        self.commit()


    def insertNewAreaAnnotation(self, x1,y1,x2,y2, slideUID, classID, annotator, typeId=2):
        query = 'INSERT INTO Annotations (slide, agreedClass, type) VALUES (%d,%d,%d)' % (slideUID,classID, typeId)
#        query = 'INSERT INTO Annotations (coordinateX1, coordinateY1, coordinateX2, coordinateY2, slide, class1, person1) VALUES (%d,%d,%d,%d,%d,%d, %d)' % (x1,y1,x2,y2,slideUID,classID,annotator)
        self.execute(query)
        query = 'SELECT last_insert_rowid()'
        self.execute(query)
        annoId = self.fetchone()[0]

        query = ('INSERT INTO Annotations_coordinates (coordinateX, coordinateY, slide, annoId, orderIdx) VALUES (%d,%d,%d,%d,%d)'
                 % (x1,y1,slideUID, annoId, 1))
        self.execute(query)

        query = ('INSERT INTO Annotations_coordinates (coordinateX, coordinateY, slide, annoId, orderIdx) VALUES (%d,%d,%d,%d,%d)'
                 % (x2,y2,slideUID, annoId, 2))
        self.execute(query)

        self.addAnnotationLabel(classId=classID, person=annotator, annoId=annoId)

        self.commit()

    def insertNewSpotAnnotation(self,xpos_orig,ypos_orig, slideUID, classID, annotator, type = 1):

        if (type == 4):
            query = 'INSERT INTO Annotations (slide, agreedClass, type) VALUES (%d,0,%d)' % (slideUID, type)
            self.execute(query)
            query = 'SELECT last_insert_rowid()'
            self.execute(query)
            annoId = self.fetchone()[0]

            query = ('INSERT INTO Annotations_coordinates (coordinateX, coordinateY, slide, annoId, orderIdx) VALUES (%d,%d,%d,%d,%d)'
                    % (xpos_orig,ypos_orig,slideUID, annoId, 1))
            self.execute(query)

        else:
            query = 'INSERT INTO Annotations (slide, agreedClass, type) VALUES (%d,%d,%d)' % (slideUID,classID, type)
            self.execute(query)
            query = 'SELECT last_insert_rowid()'
            self.execute(query)
            annoId = self.fetchone()[0]

            query = ('INSERT INTO Annotations_coordinates (coordinateX, coordinateY, slide, annoId, orderIdx) VALUES (%d,%d,%d,%d,%d)'
                    % (xpos_orig,ypos_orig,slideUID, annoId, 1))
            self.execute(query)

            self.addAnnotationLabel(classId=classID, person=annotator, annoId=annoId)

        self.commit()

    def removeAnnotationLabel(self, labelIdx, annoIdx):
            q = 'DELETE FROM Annotations_label WHERE uid == %d' % labelIdx
            self.execute(q)
            self.commit()
            self.checkCommonAnnotation(annoIdx)

    def removeAnnotation(self, annoId):
            self.execute('DELETE FROM Annotations_label WHERE annoId == %d' % annoId)
            self.execute('DELETE FROM Annotations_coordinates WHERE annoId == %d' % annoId)
            self.execute('DELETE FROM Annotations WHERE uid == '+str(annoId))
            self.commit()
            

    def insertNewSlide(self,slidename):
            self.execute('INSERT INTO Slides (filename) VALUES ("' + slidename +'")')
            self.commit()


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
            return self.dbcur.execute(query)
        else:
            print('Warning: DB not opened.')

    def getDBname(self):
        if (self.dbOpened):
            return self.dbname
        else:
            return ''
    
    def getAllPersons(self):
        self.execute('SELECT name, uid FROM Persons ORDER BY uid')
        return self.fetchall()

    def getAllClasses(self):
        self.execute('SELECT name,uid FROM Classes ORDER BY uid')
        return self.fetchall()


    def commit(self):
        return self.db.commit()

    def countEntryPerClass(self, slideID = 0):
        self.dbcur.execute('SELECT Classes.uid, COUNT(*), name FROM Annotations LEFT JOIN Classes on Classes.uid == Annotations.agreedClass GROUP BY Classes.uid')
        allClasses = self.dbcur.fetchall()

        statistics = np.zeros((2,len(allClasses)))
    
        names=list()
        classids = np.zeros(len(allClasses))        
        for idx,element in enumerate(allClasses):
                classids[idx] = element[0]
                statistics[1,idx] = element[1]
                if (element[2] is not None):
                    names.append( str(element[2]))
                else:
                    names.append('unknown')
                    classids[idx] = 0

        if (slideID is not None):
            for idx, classId in enumerate(classids):
                self.dbcur.execute('SELECT COUNT(*) FROM Annotations LEFT JOIN Classes on Classes.uid == Annotations.agreedClass WHERE Annotations.slide == %d AND Classes.uid == %d' % (slideID,classId) )
                allClasses = self.dbcur.fetchone()
                statistics[0,idx] = allClasses[0]


        return (names, statistics)

    def countEntries(self):
        self.dbcur.execute('SELECT COUNT(*) FROM Annotations')
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

        tempcur.execute('CREATE TABLE `Annotations_label` ('
            '	`uid`	INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,'
            '	`person`	INTEGER,'
            '	`class`	INTEGER,'
            '	`annoId`	INTEGER'
            ');')

        tempcur.execute('CREATE TABLE `Annotations_coordinates` ('
            '`uid`	INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,'
            '`coordinateX`	INTEGER,'
            '`coordinateY`	INTEGER,'
            '`slide`	INTEGER,'
            '`annoId`	INTEGER,'
            '`orderIdx`	INTEGER'
            ');')

        tempcur.execute('CREATE TABLE `Annotations` ('
            '`uid`	INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,'
            '`slide`	INTEGER,'
            '`type`	INTEGER,'
            '`agreedClass`	INTEGER'
            ');')

        tempcur.execute('CREATE TABLE `Classes` ('
            '`uid`	INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,'
            '`name`	TEXT'
            ');')
        
        tempcur.execute('CREATE TABLE `Persons` ('
            '`uid`	INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,'
            '`name`	TEXT'
            ');')

        tempcur.execute('CREATE TABLE `Slides` ('
            '`uid`	INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,'
            '`filename`	TEXT,'
            '`width`	INTEGER,'
            '`height`	INTEGER'
            ');')

        tempdb.commit()
        self.db = tempdb
        self.dbcur = self.db.cursor()
        self.dbfilename = dbfilename
        self.dbname = os.path.basename(dbfilename)
        self.dbOpened=True

        return True
