import requests
import json
from requests.auth import HTTPBasicAuth
from SlideRunner.dataAccess.database import *
from SlideRunner.dataAccess.annotations import *
import time
import datetime
import re
import sys
from functools import partial
import threading
import queue
from requests_toolbelt.multipart import encoder

from exact_sync.v1.api.annotations_api import AnnotationsApi
from exact_sync.v1.api.images_api import ImagesApi
from exact_sync.v1.api.image_sets_api import ImageSetsApi
from exact_sync.v1.api.annotation_types_api import AnnotationTypesApi
from exact_sync.v1.api.products_api import ProductsApi
from exact_sync.v1.api.teams_api import TeamsApi
from exact_sync.v1.api.users_api import UsersApi

from exact_sync.v1.models import ImageSet, Team, Product, AnnotationType as ExactAnnotationType, Image, Annotation, AnnotationMediaFile
from exact_sync.v1.rest import ApiException
from exact_sync.v1.configuration import Configuration
from exact_sync.v1.api_client import ApiClient

class ExactAPIs():
    def __init__(self, client):
        self.image_sets_api = ImageSetsApi(client)
        self.annotations_api = AnnotationsApi(client)
        self.annotation_types_api = AnnotationTypesApi(client)
        self.images_api = ImagesApi(client)
        self.product_api = ProductsApi(client)
        self.team_api = TeamsApi(client)
        self.users_api = UsersApi(client)


EPS_TIME_CONVERSION = 0.001 # epsilon for time conversion uncertainty


annotationtype_to_vectortype = {
    AnnotationType.SPOT: ExactAnnotationType.VECTOR_TYPE.POINT,
    AnnotationType.AREA: ExactAnnotationType.VECTOR_TYPE.BOUNDING_BOX,
    AnnotationType.POLYGON: ExactAnnotationType.VECTOR_TYPE.POLYGON,
    AnnotationType.SPECIAL_SPOT: ExactAnnotationType.VECTOR_TYPE.POINT,
    AnnotationType.CIRCLE: ExactAnnotationType.VECTOR_TYPE.POINT,
}

def list_to_exactvector(vector, zLevel=None):
    retdict = {f'x{(i+1)}': v[0] for i, v in enumerate(vector)}
    retdict.update({f'y{i+1}': v[1] for i, v in enumerate(vector)} )
    if zLevel is not None:
        retdict['frame']=int(zLevel+1)
    return retdict

def get_hex_color(id):
    """
        Assigns one of sliderunners colors to a class
    """
    vp = ViewingProfile()
    idm = id % len(vp.COLORS_CLASSES)
    col = vp.COLORS_CLASSES[idm]
    return '#{:02x}{:02x}{:02x}'.format( *col[0:3] )

def get_filename_from_cd(cd):
    """
    Get filename from content-disposition
    """
    if not cd:
        return None
    fname = re.findall('filename=(.+)', cd)
    if len(fname) == 0:
        return None
    return fname[0]


class ExactImageList():
    def __init__(self, imagelist):
        self._list = imagelist
        if len(imagelist)>0:
            if len(imagelist[0])!=2:
                raise ValueError('Must be a list of lists of size 2.')
    
    @property
    def list(self) -> list:
        return self._list

    def dict(self) -> dict:
        return {x:y for x,y in self._list}

class AccessViolationError(Exception):
    def __init__(self, message:str):
        self.__str__ = message

class ExactProcessError(Exception):
    def __init__(self, message:str):
        self.__str__ = message

class ExactManager():

    def log(self,level, *args):
        logmsg=' '.join([str(x) for x in args])
        if level>=self.loglevel:
            self.logfile.write( '%s ' % str(datetime.datetime.now()) + logmsg +'\n')
        if (self.statusqueue is not None) and (level>1):
            self.statusqueue.put((1, logmsg))

    def progress(self, value:float, callback:callable=None):
        value=value/self.progress_denominator+self.offset
        if (self.statusqueue is not None):
            self.statusqueue.put((0, value*100 if value<1 else -1))
        if (callback is not None):
            callback(value*100)

    def set_progress_properties(self, denominator:float, offset:float):
        self.progress_denominator=float(denominator)
        self.offset=float(offset)

    def upload_image_to_imageset(self, imageset_id:int, filename:str):
        apic = self.APIs.images_api.create_image(file_path=filename, image_type=0, image_set=imageset_id)
        pass
        return apic.results

    def queueWorker(self):
        while (True):
            status, newjob, context = self.jobqueue.get()
            if (status==-1):
                break
            ret = newjob()
            self.resultQueue.put((ret, context))

    def __init__(self, username:str=None, password:str=None, serverurl:str=None, logfile=sys.stdout, loglevel:int=1, statusqueue:queue.Queue=None):

        configuration = Configuration()
        configuration.username = username
        configuration.password = password
        configuration.host = serverurl

        self.client = ApiClient(configuration=configuration)
        self.APIs = ExactAPIs(self.client)
        self.configuration = configuration
        self.statusqueue = statusqueue
        self.progress_denominator = 1
        self.progress_offset = 0
        self.set_progress_properties(1,0)
        self.multi_threaded=True
        self.num_threads=10
        if (self.multi_threaded):
            self.jobqueue = queue.Queue()
            self.resultQueue = queue.Queue()
            self.workers={}
            for k in range(self.num_threads):
                self.workers[k] = threading.Thread(target=self.queueWorker, daemon=True)
                self.workers[k].start()

        self.logfile = logfile
        self.loglevel = loglevel
        self.log(0,f'Created EXM with username {username}, serverurl: {serverurl}')

        # TODO: Include V1 time sync, once available
#        stat, ret = self.get('timesync/')
#        timeoffset = abs(json.loads(ret)['unixtime']-time.time())
#        if (stat==200) and (timeoffset>10):
#            raise ExactProcessError('Your computer''s clock is incorrect')
#        else:
#            self.log(1,f'Time offset to server is: {timeoffset} seconds.')
    

    def terminate(self):
        for k in range(self.num_threads):
            self.jobqueue.put((-1,0,0))


    def upload_monitor(self, monitor:encoder.MultipartEncoderMonitor):
        self.progress(float(monitor.bytes_read)/monitor.len)


    def retrieve_and_insert(self, dataset_id:int, slideuid:int, database:Database,  callback:callable=None, **kwargs ):

        def createDatabaseObject():
            database.deleteTriggers()
            zLevel = anno.vector['frame']-1 if 'frame' in anno.vector else 0
            if (vector_type == 3): # line
                annoId = database.insertNewPolygonAnnotation(annoList=coords, slideUID=slideuid, classID=classes_rev[class_name], annotator=persons[person_name], exact_id=exact_id, description=anno.description, zLevel=zLevel)
            elif (vector_type in [4,5]): # polygon or line
                annoId = database.insertNewPolygonAnnotation(annoList=coords, slideUID=slideuid, classID=classes_rev[class_name], annotator=persons[person_name], closed=anno.annotation_type['closed'], exact_id=exact_id, description=anno.description, zLevel=zLevel)
            elif (vector_type in [1,6]): # rectangle
                annoId = database.insertNewAreaAnnotation(x1=anno.vector['x1'],y1=anno.vector['y1'],x2=anno.vector['x2'],y2=anno.vector['y2'], slideUID=slideuid, classID=classes_rev[class_name], annotator=persons[person_name], exact_id=exact_id, description=anno.description, zLevel=zLevel)                
            elif (vector_type==2): # ellipse
                r1 = int(round((anno.vector['x2']-anno.vector['x1'])/2))
                xpos = anno.vector['x1']+r1
                r2 = int(round((anno.vector['y2']-anno.vector['y1'])/2))
                ypos = anno.vector['y1']+r2
                if ('SpotCircleRadius' in kwargs) and (r1==r2) and (r1==kwargs['SpotCircleRadius']):
                    annoId = database.insertNewSpotAnnotation(xpos_orig=xpos,ypos_orig=ypos, slideUID=slideuid, classID=classes_rev[class_name], annotator=persons[person_name], typeId=5, exact_id=exact_id, description=anno.description, zLevel=zLevel)                
                else:
                    annoId = database.insertNewAreaAnnotation(x1=anno.vector['x1'],y1=anno.vector['y1'],x2=anno.vector['x2'],y2=anno.vector['y2'], slideUID=slideuid, classID=classes_rev[class_name], annotator=persons[person_name], typeId=5, exact_id=exact_id, description=anno.description, zLevel=zLevel)                
            else:
                raise NotImplementedError('Vector Type %d is unknown.' % vector_type)
            
            if (anno.deleted):
                database.removeAnnotation(database.guids[uuid],onlyMarkDeleted=True)
            
            database.addTriggers()
            return annoId

        self.progress(0, callback=callback)
        annos = np.array(self.APIs.annotations_api.list_annotations(image=dataset_id, expand='annotation_type,last_editor', pagination=False).results)
        #print('Annos: ',annos)
        self.log(0, f'Found {len(annos)} annotations for dataset {dataset_id}')

        createClasses = True if 'createClasses' not in kwargs else kwargs['createClasses']
        
        if (slideuid is None):
            raise ExactProcessError('Slide not in database. Please add it first.')

        database.deleteTriggers()

        classes = {y:x for x,y,col in database.getAllClasses()}
        classes_rev = {x:y for x,y,col in database.getAllClasses()}
        classes_col = {y:col for x,y,col in database.getAllClasses()}

        persons = {x:y for x,y in database.getAllPersons()}
        
        exactPersonId, _ = database.getExactPerson()
        persons[self.configuration.username] = exactPersonId

        database.loadIntoMemory(slideuid, zLevel=None)

        # reformat to dict according to uuid
        uuids = np.array([anno.unique_identifier for anno in annos])

        annodict = {uuid:annos[np.where(uuids==uuid)] for uuid in uuids}
        # TODO: resolve conflict if one guid has multiple shapes

        for cntr, uuid in enumerate(uuids):
            self.progress(float(cntr)*0.5/(len(uuids)+0.001), callback=callback)
            le_array = [sanno.last_edit_time for sanno in annodict[uuid]]
            lastedit = np.max(le_array) # maximum last_edit time is most recent for uuid


            # TODO: expand this in the first place
            for anno in annodict[uuid]:
                class_name = anno.annotation_type['name']
                person_name = anno.last_editor['username'] if anno.last_editor is not None and 'username' in anno.last_editor else 'unknown'
                exact_id = anno.id

                # check if annotator exists already, if not, create
                if person_name not in persons.keys():
                    database.insertAnnotator(person_name)
                    self.log(1,f'Adding annotator {person_name} found in EXACT')
                    persons = {x:y for x,y in database.getAllPersons()}
                    persons[self.configuration.username] = exactPersonId
                    

                # check if class exists already in DB, if not, create
                if (class_name not in classes.values()):
                    if not createClasses:
                        raise AccessViolationError('Not permitted to create new classes, but class %d not found' % anno.annotation_type['name'])
                    else:
                        database.insertClass(class_name)
                        classes = {x:y for y,x,col in database.getAllClasses()}
                        classes_rev = {x:y for x,y,col in database.getAllClasses()}
                        classes_col = {y:col for x,y,col in database.getAllClasses()}
                
                vector_type = anno.annotation_type['vector_type']
                vlen = int(len(anno.vector)/2)
                
                #lastedit = datetime.datetime.strptime(anno['last_edit_time'], "%Y-%m-%dT%H:%M:%S.%f")

                # reformat coords               
#                coords = np.array(anno.vector).T.tolist()
                coords = [[anno.vector['x%d' % (x+1)] for x in range(vlen)],[anno.vector['y%d' % (x+1)]for x in range(vlen)]]
                coords = np.array(coords).T.tolist() # transpose

                # TODO: The last edited object defines currently the coords --> this is a problem.

                if (uuid not in database.guids.keys()) and (vlen>0):
                    # Is new - woohay!
                    annoId = createDatabaseObject()
                    database.setGUID(annoid=annoId, guid=uuid)
                    database.setLastModified(annoid=annoId, lastModified=lastedit.timestamp())
                    self.log(1, f'Importing remote object with guid {uuid}')
                elif (vlen>0):
#                    print('Object exists, last edit was: ',lastedit.timestamp(), database.annotations[database.guids[uuid]].lastModified)
                    if (lastedit.timestamp()-EPS_TIME_CONVERSION>database.annotations[database.guids[uuid]].lastModified):
                        self.log(1,f'Recreating local object with guid {uuid}, remote was more recent')
                        database.removeAnnotation(database.guids[uuid],onlyMarkDeleted=False)
                        createDatabaseObject()
                        database.setGUID(annoid=annoId, guid=uuid)
                        database.setLastModified(annoid=annoId, lastModified=lastedit.timestamp())
                        
                    elif abs(lastedit.timestamp()-database.annotations[database.guids[uuid]].lastModified)<EPS_TIME_CONVERSION:
                        # equal time stamp --> maybe further annotation with same guid, let's check.
#                        print('Time stamps difference: ', lastedit.timestamp()-database.annotations[database.guids[uuid]].lastModified)
#                        print('Last edit (online): ',lastedit.timestamp())
#                        print('Last modified (DB): ',database.annotations[database.guids[uuid]].lastModified)
                        labels_exactids = [lab.exact_id for lab in database.annotations[database.guids[uuid]].labels]
                        if anno.id not in labels_exactids: 
                            # need to create in local DB
                            database.addAnnotationLabel(classId=classes_rev[class_name], person=persons[person_name], annoId=database.guids[uuid], exact_id=anno.id)
                            self.log(1,'Adding new local label for annotation uuid = ',uuid,classes_rev[class_name],persons[person_name])
                    else:
                        # remote is older --> but maybe a remote label is not yet known
                        labels_exactids = [lab.exact_id for lab in database.annotations[database.guids[uuid]].labels]
                        if anno.id not in labels_exactids: 
                            # need to create in local DB
                            database.addAnnotationLabel(classId=classes_rev[class_name], person=persons[person_name], annoId=database.guids[uuid], exact_id=anno.id)
                            self.log(1,'Adding new label for annotation uuid = ',uuid,classes_rev[class_name],persons[person_name])
        
        database.addTriggers()

    def retrieve_imagesets(self):
        imagesets = self.APIs.image_sets_api.list_image_sets(pagination=False, expand='product_set').results
        return imagesets

    def sync(self, dataset_id:int,imageset_id:int, product_id:int, slideuid:int, database:Database, image_id:str=None, callback:callable=None, **kwargs ):

        annotypedict = dict()
        mergeLocalClasses=dict()
        self.retrieve_and_insert(dataset_id=dataset_id, slideuid=slideuid, database=database, callback=callback)

        def getAnnotationTypes():
            annotypes = self.APIs.annotation_types_api.list_annotation_types(product=product_id, pagination=False).results

            annotypedictret = {annotype.name:annotype for annotype in annotypes}
            return annotypedictret 

        def get_or_create_annotationtype(labelId:int, annotationType:AnnotationType) -> (int, str):

            """
                Retrieve the correct annotation_type_id from the annotation type dictionary. If non-existent,
                create it.
            """
            nonlocal annotypedict, classToSend, mergeLocalClasses
            name = classes[labelId][0:20]
            annotationType_names = { AnnotationType.AREA: 'area',
                                    AnnotationType.POLYGON: 'poly',
                                    AnnotationType.SPOT: 'spot',
                                    AnnotationType.SPECIAL_SPOT: 'spot',
                                    AnnotationType.CIRCLE: 'circ'}
            name_alt = name+'_'+annotationType_names[annotationType] # alternative name
            if (name in annotypedict.keys()) and (annotypedict[name].vector_type == annotationtype_to_vectortype[annotationType]):
                # name and vector type match --> return id of annotation type
                return annotypedict[name].id
            elif ((name in annotypedict.keys()) and (annotypedict[name].vector_type != annotationtype_to_vectortype[annotationType])
                and (name_alt in annotypedict.keys()) and (annotypedict[name_alt].vector_type == annotationtype_to_vectortype[annotationType])):
                return annotypedict[name_alt].id # alternative name matches 
            elif (name not in annotypedict.keys()):
                # nonexistant type --> create
                annotation_type = ExactAnnotationType(name=name, vector_type=annotationtype_to_vectortype[annotationType], product=product_id, color_code=classes_col[classToSend], sort_order=classToSend)
                annotypeID = self.APIs.annotation_types_api.create_annotation_type(body=annotation_type)
                print('CREATING NEW ANNOTATION TYPE A:',annotation_type)
                annotypedict = getAnnotationTypes()
                return annotypeID.id
            elif (name_alt not in annotypedict.keys()): # non matching type for original name -> create alterntive name
#                self.create_annotationtype(product_id=product_id,name=name_alt, vector_type=annotationtype_to_vectortype[annotationType], color_code=classes_col[classToSend], sort_order=classToSend)
                annotation_type = ExactAnnotationType(name=name_alt, vector_type=annotationtype_to_vectortype[annotationType], product=product_id, color_code=classes_col[classToSend], sort_order=classToSend)
                annotypeID = self.APIs.annotation_types_api.create_annotation_type(body=annotation_type)
                print('CREATING NEW ANNOTATION TYPE B:',annotation_type)
                annotypedict = getAnnotationTypes()
                mergeLocalClasses[(annotationType,labelId)] = name_alt
                return annotypeID.id
            else:
                raise ExactProcessError('Unable to create annotation type for class'+name)

        filename = database.slideFilenameForID(slideuid)

        imageset_details = self.APIs.image_sets_api.retrieve_image_set(imageset_id, expand='images')
        
        for imset in imageset_details.images:
            if (imset['name']==filename):
                image_id=imset['id']

        if (image_id is None):
            raise ExactProcessError('No matching image found.')

#        annos = self.APIs.annotations_api.list_annotations(id=image_id).results
        annos = np.array(self.APIs.annotations_api.list_annotations(image=dataset_id, expand=['last_editor','annotation_type'], pagination=False).results)

        # retrieve all annotation types
        annotypedict = getAnnotationTypes()

        # reformat to dict according to uuid
        uuids = np.array([anno.unique_identifier for anno in annos])

        annodict = {uuid:annos[np.where(uuids==uuid)] for uuid in uuids}


        classes = {y:x for x,y,col in database.getAllClasses()}
        classes_col = {y:col for x,y,col in database.getAllClasses()}
        classes_rev = {x:y for x,y,col in database.getAllClasses()}

        uidToSend, nameToSend = database.getExactPerson()
        pending_requests=0

        database.loadIntoMemory(slideuid, zLevel=None)
        self.log(0,f'Checking all {len(database.annotations.keys())} entries of DB slide {slideuid}')
#            print('Loading zLevel: ',zLevel,'annos=',len(database.annotations.keys()))
       
        for cntr,annokey in enumerate(database.annotations.keys()):
            if not (self.multi_threaded):
                self.progress(0.5+(float(cntr)*0.5/(len(database.annotations.keys())+0.0001)), callback=callback)
            dbanno = database.annotations[annokey]
            # look through annotations
            labelToSend = [lab.classId for lab in dbanno.labels if lab.annnotatorId==uidToSend]
            labelToSendIdx = [i for i,lab in enumerate(dbanno.labels) if lab.annnotatorId==uidToSend]
#                print('LabelToSend:',uidToSend, labelToSend)
            if len(labelToSend)==0:
                # not from expert marked as exact user --> ignore
                continue
#                print('DB ANNO: ',dbanno.guid,'ANNO DICT:',annodict.keys())
            if (dbanno.guid in annodict.keys()):
                le_array = [_anno.last_edit_time for _anno in annodict[dbanno.guid]]
                lastedit = np.max(le_array) # maximum last_edit time is most recent for uuid
                # highlander rule --> whoever edited last will win (for the complete annotation)

                if (lastedit.timestamp()>dbanno.lastModified):
                    pass
                    print('A more recent version of ',dbanno.guid,'is available',lastedit.timestamp(), dbanno.lastModified)
                    # more recent version exists online
                    # TODO: Implement storing of my version in case of creation
                elif (lastedit.timestamp()+EPS_TIME_CONVERSION<dbanno.lastModified):
                    # local annotation is more recent --> update
                    IdToSend = [lab.exact_id for lab in dbanno.labels if lab.annnotatorId==uidToSend]
                    for lts, idts,i in zip(labelToSend,IdToSend,labelToSendIdx):
                        # case: exact_id is known
                        classToSend=lts # used in embedded function
                        if (idts is not None) and (idts>0):
#                            print('Remote ID known:',idts,'=> Forcing update, remote is:', lastedit.timestamp(), 'local is:',dbanno.lastModified)
                            lastModified=datetime.datetime.fromtimestamp(dbanno.lastModified).strftime( "%Y-%m-%dT%H:%M:%S.%f")
                            vector = list_to_exactvector(dbanno.coordinates.tolist(),zLevel=dbanno.zLevel)
                            self.APIs.annotations_api.partial_update_annotation(id=idts, annotation_type=get_or_create_annotationtype(lts,dbanno.annotationType), last_edit_time=lastModified, vector=vector, deleted=dbanno.deleted, unique_identifier=dbanno.guid, description=dbanno.text)
#                            self.update_annotation(,annotation_id=idts, )      
#                            print('UPDATING Annotation')           
                        else:
                            # case: exact_id is unknown
                            # can have the following causes:
                            # 1. label is new for annotation --> in this case, it has to be created
                            # 2. exact_id is missing in database --> avoided by first receiving from server
                            annotationtype = get_or_create_annotationtype(lts, dbanno.annotationType)
                            vector = list_to_exactvector(dbanno.coordinates.tolist(),zLevel=dbanno.zLevel)
                            
                            lastModified=datetime.datetime.fromtimestamp(dbanno.lastModified).strftime( "%Y-%m-%dT%H:%M:%S.%f")
                            annotation = Annotation(annotation_type=annotationtype, vector=vector, image=image_id, unique_identifier=dbanno.guid, last_edit_time=lastModified, time=lastModified, description=dbanno.text, deleted=dbanno.deleted)
                            if (self.multi_threaded):
                                context = {'labeluid': i, 'annouid': dbanno.uid}
                                self.jobqueue.put((0,partial(self.APIs.annotations_api.create_annotation, body=annotation ),context))
                                pending_requests+=1
                            else:
                                det = self.APIs.annotations_api.create_annotation(body=annotation)
#                                det = self.create_annotation(image_id=image_id, annotationtype_id=get_or_create_annotationtype(lts, dbanno.annotationType), deleted=dbanno.deleted,last_modified=dbanno.lastModified, vector=dbanno.coordinates.tolist(), guid=dbanno.guid, description=dbanno.text)
                                # add new exact_id to DB field
                                label = dbanno.labels[i]
                                database.setAnnotationLabel(classId=label.classId,  person=label.annnotatorId, entryId=label.uid, annoIdx=dbanno.uid, exact_id=det['id'])
                                label.exact_id = det['annotations']['id']
                                self.log(1,'Updating local exact_id (previously unknown)')
                else:
                    # Equal time stamps --> ignore
#                    print('EQUAL TIME STAMPS FOR ',dbanno.guid,'is available',lastedit.timestamp(), dbanno.lastModified)
                    pass
            else: # database annotation not in 
                for i, classToSend in zip(labelToSendIdx,labelToSend):
                    lastModified=datetime.datetime.fromtimestamp(dbanno.lastModified).strftime( "%Y-%m-%dT%H:%M:%S.%f")
                    if (self.multi_threaded):
                        context = {'labeluid': i, 'annouid': dbanno.uid}
                        annotationtype = get_or_create_annotationtype(classToSend, dbanno.annotationType)
                        vector = list_to_exactvector(dbanno.coordinates.tolist(),zLevel=dbanno.zLevel)
                        annotation = Annotation(annotation_type=annotationtype, vector=vector, image=image_id, unique_identifier=str(dbanno.guid), last_edit_time=lastModified, time=lastModified,   description=dbanno.text, deleted=dbanno.deleted)
#                        self.jobqueue.put((0,partial(self.create_annotation, image_id=image_id, annotationtype_id=get_or_create_annotationtype(classToSend, dbanno.annotationType), deleted=dbanno.deleted,last_modified=dbanno.lastModified, vector=dbanno.coordinates.tolist(), guid=dbanno.guid, description=dbanno.text),context))
                        self.jobqueue.put((0,partial(self.APIs.annotations_api.create_annotation, body=annotation ),context))
                        pending_requests+=1
                    else:
                        annotationtype=get_or_create_annotationtype(classToSend, dbanno.annotationType)
#                        det = self.create_annotation(image_id=image_id, annotationtype_id=annotationtype, deleted=dbanno.deleted, last_modified=dbanno.lastModified, vector=dbanno.coordinates.tolist(), guid=dbanno.guid, description=dbanno.text)
                        vector = list_to_exactvector(dbanno.coordinates.tolist(), zLevel=dbanno.zLevel)
                        annotation = Annotation(annotation_type=annotationtype, vector=vector, image=image_id, unique_identifier=dbanno.guid, last_edit_time=lastModified, time=lastModified, description=dbanno.text, deleted=dbanno.deleted)
                        det = self.APIs.annotations_api.create_annotation(body=annotation)

                        # add new exact_id to DB field
                        label = dbanno.labels[i]
                        # for local update, do not set Annotation.lastModified
                        database.deleteTriggers()
                        database.setAnnotationLabel(classId=label.classId,  person=label.annnotatorId, entryId=label.uid, annoIdx=dbanno.uid, exact_id=det['annotations']['id'])
                        database.addTriggers()
                        label.exact_id = det['annotations']['id']

            # make updates to local database until final.
            while (pending_requests>0):
                self.progress(1.0-(float(pending_requests)*0.5/(len(database.annotations.keys())+0.0001)), callback=callback)
                res, context = self.resultQueue.get()
                dbanno = database.annotations[context['annouid']]
                pending_requests-=1
                i = context['labeluid']
                label = dbanno.labels[i]
                database.deleteTriggers()
                print('Received reply:',res)
                database.setAnnotationLabel(classId=label.classId,  person=label.annnotatorId, entryId=label.uid, annoIdx=dbanno.uid, exact_id=res.id)
                database.addTriggers()
                label.exact_id = res.id

            # finally, lets find out if we need to make modifications to the 
            # local database due to annotation type conversions
            if len(list(mergeLocalClasses.keys()))>0:
                self.log(1,'Need to make adjustments to local DB due to annotation type conversion..')
                for key in mergeLocalClasses:
                    (annoType, oldId) = key
                    newname = mergeLocalClasses[key]
                    if (database.findClassidOfClass(newname) is not None):
                        # we need to add the new class
                        newId = database.insertClass(newname)
                        self.log(1,f'Changing all annotation labels of old type = {oldId}, with annotation Type={annoType}, to new type: {newId}')
                        database.changeAllAnnotationLabelsOfType(oldId, annoType, newId)
                        # reload slide
                        database.loadIntoMemory(database.annotationsSlide,zLevel)


        self.progress(1, callback=callback)



