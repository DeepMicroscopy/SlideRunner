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

EPS_TIME_CONVERSION = 0.001 # epsilon for time conversion uncertainty

annotationtype_to_vectortype = {
    AnnotationType.SPOT: 2,
    AnnotationType.AREA: 1,
    AnnotationType.POLYGON: 5,
    AnnotationType.SPECIAL_SPOT: 2,
    AnnotationType.CIRCLE: 2,
}

def list_to_exactvector(vector):
    retdict = {f'x{(i+1)}': v[0] for i, v in enumerate(vector)}
    retdict.update({f'y{i+1}': v[1] for i, v in enumerate(vector)} )
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
    def __init__(self, imagelist:list):
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


    def queueWorker(self):
        while (True):
            status, newjob, context = self.jobqueue.get()
            if (status==-1):
#                print('Stopping worker')
                break
            ret = newjob()
            self.resultQueue.put((ret, context))

    def __init__(self, username:str=None, password:str=None, serverurl:str=None, logfile=sys.stdout, loglevel:int=1, statusqueue:queue.Queue=None):
        self.username = username
        self.password = password
        self.serverurl = serverurl if serverurl[-1]=='/' else serverurl+'/'
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
        stat, ret = self.get('timesync/')
        timeoffset = abs(json.loads(ret)['unixtime']-time.time())
        if (stat==200) and (timeoffset>10):
            raise ExactProcessError('Your computer''s clock is incorrect')
        else:
            self.log(1,f'Time offset to server is: {timeoffset} seconds.')
    

    def terminate(self):
        for k in range(self.num_threads):
            self.jobqueue.put((-1,0,0))

    def json_post_request(self,url) -> dict:
        req = requests.post(url, auth = (self.username, self.password))
        if req.status_code==403:
            raise AccessViolationError('Permission denied by exact server for current user'+req.text)
        try: 
            return json.loads(req.text)
        except:
            return dict()


    def json_get_request(self,url) -> dict:
        req = requests.get(url, auth = (self.username, self.password))
        if req.status_code==403:
            raise AccessViolationError('Permission denied by exact server for current user'+req.text)
        try: 
            return json.loads(req.text)
        except:
            return dict()

    def csv_get_request(self,url) -> list:
        req = requests.get(url, auth = (self.username, self.password))
        try: 
            return req.text.split(',')
        except:
            return []

    def retrieve_annotationtypes(self, imageset_id:int) -> list:
        obj = self.json_get_request(self.serverurl+'annotations/api/annotation/loadannotationtypes/?imageset_id=%d' % imageset_id)['annotation_types']        
        return obj

    def download_image(self, image_id:int, target_folder:str, callback:callable=None):
        self.log(1, 'Downloading image',image_id,'to',target_folder)
        status,filename = self.getfile('images/api/image/download/%d/?original_image=True' % image_id, target_folder, callback=callback)
        return filename

    def retrieve_imagesets(self):
        status, obj = self.get('images/api/list_imagesets/')
        if (status != 200):
            raise ExactProcessError('Unable to retrieve list of image sets')
        return json.loads(obj)

    def retrieve_annotations(self,dataset_id:int) -> list:
        obj = self.json_get_request(self.serverurl+'annotations/api/annotation/load/?image_id=%d' % dataset_id)
        self.log(0, 'Retrieving annotations from ',dataset_id)
        if 'annotations' in obj:
            return obj['annotations']
        else:
            return []

    def delete_image(self, image_id:int):
        status, obj = self.get('images/api/image/delete/%d/'%image_id)
        self.log(2, 'Deleting image',image_id)
        return status, obj


    def upload_monitor(self, monitor:encoder.MultipartEncoderMonitor):
        self.progress(float(monitor.bytes_read)/monitor.len)

    def upload_image_to_imageset(self, imageset_id:int, filename:str) -> bool:
        e = encoder.MultipartEncoder(fields={'files[]': (os.path.basename(filename), open(filename, 'rb'), 'application/octet-stream')})
        m = encoder.MultipartEncoderMonitor(e, self.upload_monitor)
        headers = {'Content-Type': m.content_type, 'referer': self.serverurl}
        self.log(1, 'Uploading image',filename,'to',imageset_id)
        status, obj = self.post('images/image/upload/%d/'%imageset_id, data=m, headers=headers, timeout=120)
        if (status==200):
            return obj
        else:
            raise ExactProcessError('Unable to upload, response is: '+str(obj))

    def add_product_to_imageset(self, product_id:int, imageset_id:int):
        data = {'image_set_id':imageset_id,
                'product_id':product_id}

        self.log(1, 'Adding product',product_id,'to',imageset_id)
        obj = self.post('images/api/imageset/product/add/',data=data )       
        return obj


    def retrieve_imagelist(self, imageset_id:int) -> list:
        # this is really a format fuckup. But let's parse it nevertheless...
        self.log(0, 'Retrieving image list for ',imageset_id)
        il = self.csv_get_request(self.serverurl+'images/imagelist/%d/' % imageset_id)
        return ExactImageList([[int(x.split('?')[0].split('/')[-2]),x.split('?')[1]] for x in il if '?' in x])


    def retrieve_and_insert(self, dataset_id:int, slideuid:int, database:Database,  callback:callable=None, **kwargs ):

        def createDatabaseObject():
            zLevel = anno['vector']['z1'] if 'z1' in anno['vector'] else 0
            if (vector_type == 3): # line
                annoId = database.insertNewPolygonAnnotation(annoList=coords, slideUID=slideuid, classID=classes_rev[class_name], annotator=persons[person_name], exact_id=exact_id, description=anno['description'], zLevel=zLevel)
            elif (vector_type in [4,5]): # polygon or line
                annoId = database.insertNewPolygonAnnotation(annoList=coords, slideUID=slideuid, classID=classes_rev[class_name], annotator=persons[person_name], closed=anno['annotation_type']['closed'], exact_id=exact_id, description=anno['description'], zLevel=zLevel)
            elif (vector_type in [1,6]): # rectangle
                annoId = database.insertNewAreaAnnotation(x1=anno['vector']['x1'],y1=anno['vector']['y1'],x2=anno['vector']['x2'],y2=anno['vector']['y2'], slideUID=slideuid, classID=classes_rev[class_name], annotator=persons[person_name], exact_id=exact_id, description=anno['description'], zLevel=zLevel)                
            elif (vector_type==2): # ellipse
                r1 = int(round((anno['vector']['x2']-anno['vector']['x1'])/2))
                xpos = anno['vector']['x1']+r1
                r2 = int(round((anno['vector']['y2']-anno['vector']['y1'])/2))
                ypos = anno['vector']['y1']+r2
                if ('SpotCircleRadius' in kwargs) and (r1==r2) and (r1==kwargs['SpotCircleRadius']):
                    annoId = database.insertNewSpotAnnotation(xpos_orig=xpos,ypos_orig=ypos, slideUID=slideuid, classID=classes_rev[class_name], annotator=persons[person_name], typeId=5, exact_id=exact_id, description=anno['description'], zLevel=zLevel)                
                else:
                    annoId = database.insertNewAreaAnnotation(x1=anno['vector']['x1'],y1=anno['vector']['y1'],x2=anno['vector']['x2'],y2=anno['vector']['y2'], slideUID=slideuid, classID=classes_rev[class_name], annotator=persons[person_name], typeId=5, exact_id=exact_id, description=anno['description'], zLevel=zLevel)                
            else:
                raise NotImplementedError('Vector Type %d is unknown.' % vector_type)
            
            if (anno['deleted']):
                database.removeAnnotation(database.guids[uuid],onlyMarkDeleted=True)
            
            return annoId
        self.progress(0, callback=callback)
        annos = np.array(self.retrieve_annotations(dataset_id))
        self.log(0, f'Found {len(annos)} annotations for dataset {dataset_id}')

        createClasses = True if 'createClasses' not in kwargs else kwargs['createClasses']
        
        if (slideuid is None):
            raise ExactProcessError('Slide not in database. Please add it first.')

        database.loadIntoMemory(slideuid)
        database.deleteTriggers()
        classes = {y:x for x,y,col in database.getAllClasses()}
        classes_rev = {x:y for x,y,col in database.getAllClasses()}
        classes_col = {y:col for x,y,col in database.getAllClasses()}

        persons = {x:y for x,y in database.getAllPersons()}
        
        exactPersonId, _ = database.getExactPerson()
        persons[self.username] = exactPersonId

        # reformat to dict according to uuid
        uuids = np.array([anno['unique_identifier'] for anno in annos])

        annodict = {uuid:annos[np.where(uuids==uuid)] for uuid in uuids}
        # TODO: resolve conflict if one guid has multiple shapes

        for cntr, uuid in enumerate(uuids):
            self.progress(float(cntr)*0.5/(len(uuids)+0.001), callback=callback)
            le_array = [datetime.datetime.strptime(sanno['last_edit_time'], "%Y-%m-%dT%H:%M:%S.%f") for sanno in annodict[uuid]]
            lastedit = np.max(le_array) # maximum last_edit time is most recent for uuid


            for anno in annodict[uuid]:
                class_name = anno['annotation_type']['name']
                person_name = anno['last_editor']['name']
                exact_id = anno['id']

                # check if annotator exists already, if not, create
                if person_name not in persons.keys():
                    database.insertAnnotator(person_name)
                    self.log(1,f'Adding annotator {person_name} found in EXACT')
                    persons = {x:y for x,y in database.getAllPersons()}
                    persons[self.username] = exactPersonId
                    

                # check if class exists already in DB, if not, create
                if (class_name not in classes.values()):
                    if not createClasses:
                        raise AccessViolationError('Not permitted to create new classes, but class %d not found' % anno['annotation_type']['name'])
                    else:
                        database.insertClass(class_name)
                        classes = {x:y for y,x,col in database.getAllClasses()}
                        classes_rev = {x:y for x,y,col in database.getAllClasses()}
                        classes_col = {y:col for x,y,col in database.getAllClasses()}
                
                vector_type = anno['annotation_type']['vector_type']
                vlen = int(len(anno['vector'])/2)
                
                #lastedit = datetime.datetime.strptime(anno['last_edit_time'], "%Y-%m-%dT%H:%M:%S.%f")

                # reformat coords                
                coords = [[anno['vector']['x%d' % (x+1)] for x in range(vlen)],[anno['vector']['y%d' % (x+1)]for x in range(vlen)]]
                coords = np.array(coords).T.tolist() # transpose

                # TODO: The last edited object defines currently the coords --> this is a problem.

                if (uuid not in database.guids.keys()) and (vlen>0):
                    # Is new - woohay!
                    self.log(1, f'Importing remote object with guid {uuid}')
                    annoId = createDatabaseObject()
                    database.setGUID(annoid=annoId, guid=uuid)
                    database.setLastModified(annoid=annoId, lastModified=lastedit.timestamp())
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
                        if anno['id'] not in labels_exactids: 
                            # need to create in local DB
                            database.addAnnotationLabel(classId=classes_rev[class_name], person=persons[person_name], annoId=database.guids[uuid], exact_id=anno['id'])
                            self.log(1,'Adding new local label for annotation uuid = ',uuid,classes_rev[class_name],persons[person_name])
                    else:
                        # remote is older --> but maybe a remote label is not yet known
                        labels_exactids = [lab.exact_id for lab in database.annotations[database.guids[uuid]].labels]
                        if anno['id'] not in labels_exactids: 
                            # need to create in local DB
                            database.addAnnotationLabel(classId=classes_rev[class_name], person=persons[person_name], annoId=database.guids[uuid], exact_id=anno['id'])
                            self.log(1,'Adding new label for annotation uuid = ',uuid,classes_rev[class_name],persons[person_name])
        
        database.addTriggers()

    def delete_annotation(self, annotation_id:int,keep_deleted_element:bool=True) -> bool:
        data = {'annotation_id':annotation_id,
                'keep_deleted_element':keep_deleted_element}
        status, ret = self.delete(f'annotations/api/annotation/delete/?annotation_id={annotation_id}&keep_deleted_element={keep_deleted_element}')

        self.log(1, f'Delete of annotation {annotation_id}, keep_deleted_element={keep_deleted_element}')
        if (status==200):
            return True
        else:
            self.log(10, f'Error during delete, message was'+ret)
            raise ExactProcessError('Unable to delete annotation.')

    def update_annotation(self, annotation_id:int,  image_id:int, annotationtype_id:int, vector:list, last_modified:int, blurred:bool=False, guid:str='', deleted:int=0, description:str=''):
        data = {
            'annotation_id': annotation_id,
            'image_id' : image_id,
            'annotation_type_id' : annotationtype_id,
            'vector' : list_to_exactvector(vector),
            'unique_identifier' : guid,
            'deleted' : deleted,
            'last_edit_time' : datetime.datetime.fromtimestamp(last_modified).strftime('%Y-%m-%dT%H:%M:%S.%f'),
            'blurred' : blurred,
            'description' : description
        }
        self.log(1, f'Update of remote annotation {guid}, ts={data["last_edit_time"]}')
        status, ret = self.post('annotations/api/annotation/update/', data=json.dumps(data), headers={'content-type':'application/json'})
        if status==200:
            return ret
        else: 
            self.log(10,'Unable to update annotation, message was: '+ret)
            raise ExactProcessError('Unable to update annotation')

    def create_annotation(self, image_id:int, annotationtype_id:int, vector:list, last_modified:int, blurred:bool=False, guid:str='', description:str='', deleted:bool=False):
        data = {
            'image_id': image_id,
            'annotation_type_id' : annotationtype_id,
            'vector' : list_to_exactvector(vector),
            'unique_identifier' : guid,
            'deleted' : deleted,
            'last_edit_time' : datetime.datetime.fromtimestamp(last_modified).strftime('%Y-%m-%dT%H:%M:%S.%f'),
            'blurred' : blurred,
            'description' : description
        }
        self.log(1,f'Creating remote annotation {guid} with ts = {data["last_edit_time"]}')
        status, ret = self.post('annotations/api/annotation/create/', data=json.dumps(data), headers={'content-type':'application/json'})
        if status==201:
            return ret
        else: 
            self.log(10,'Unable to create annotation, message was: '+ret)
            raise ExactProcessError('Unable to create annotation')
            
    
    def delete_annotationtype(self, annotation_type_id:int):
        data = {'annotation_type_id':annotation_type_id}
        return self.post('administration/api/annotation_type/delete/', data=data)

    def retrieve_imageset(self,imageset_id):
        return self.json_get_request(self.serverurl+'images/api/imageset/load?image_set_id=%d' % imageset_id)['image_set']

    def create_annotationtype(self,product_id:int, name:str, vector_type:int, color_code:str='#FF0000',
                              area_hit_test:bool=True, closed:bool=False, default_width:int=50,
                              default_height:int=50, sort_order:int=0
                              ):
        data = {'product_id': product_id,
                'name': name[0:20],
                'color_code': color_code,
                'sort_order':sort_order,
                'vector_type': vector_type,
                'default_width': default_width,
                'default_height': default_height,
                'area_hit_test':area_hit_test,
                'closed':closed}
        self.log(1,'Creating remote annotation type: ',name,'product',product_id,'vector type',vector_type)
        
        status, ret =  self.post('administration/api/annotation_type/create/', data=data)
        if (status==201):
            return ret
        else:
            self.log(10,'Unable to create annotation, message was: '+ret)
            raise ExactProcessError('Unable to create annotation')


    def sync(self, dataset_id:int,imageset_id:int, product_id:int, slideuid:int, database:Database, image_id:str=None, callback:callable=None, **kwargs ):

        annotypedict = dict()
        mergeLocalClasses=dict()
        self.retrieve_and_insert(dataset_id=dataset_id, slideuid=slideuid, database=database, callback=callback)

        def getAnnotationTypes():
            annotypes = self.retrieve_annotationtypes(imageset_id)

            annotypedictret = {annotype['name']:annotype for annotype in annotypes}
            return annotypedictret 

        def get_or_create_annotationtype(labelId:int, annotationType:AnnotationType) -> (int, str):

            """
                Retrieve the correct annotation_type_id from the annotation type dictionary. If non-existent,
                create it.
            """
            nonlocal annotypedict, classToSend, mergeLocalClasses
            name = classes[labelId][0:20]
            annotationType_names = { AnnotationType.AREA: 'rect',
                                    AnnotationType.POLYGON: 'poly',
                                    AnnotationType.SPOT: 'circ',
                                    AnnotationType.SPECIAL_SPOT: 'circ',
                                    AnnotationType.CIRCLE: 'circ'}
            name_alt = name+'_'+annotationType_names[annotationType] # alternative name
            if (name in annotypedict.keys()) and (annotypedict[name]['vector_type'] == annotationtype_to_vectortype[annotationType]):
                # name and vector type match --> return id of annotation type
                return annotypedict[name]['id']
            elif ((name in annotypedict.keys()) and (annotypedict[name]['vector_type'] != annotationtype_to_vectortype[annotationType])
                and (name_alt in annotypedict.keys()) and (annotypedict[name_alt]['vector_type'] == annotationtype_to_vectortype[annotationType])):
                return annotypedict[name_alt]['id'] # alternative name matches 
            elif (name not in annotypedict.keys()):
                # nonexistant type --> create
                self.create_annotationtype(product_id=product_id,name=name, vector_type=annotationtype_to_vectortype[annotationType], color_code=classes_col[classToSend], sort_order=classToSend)
                annotypedict = getAnnotationTypes()
                return annotypedict[name]['id']
            elif (name_alt not in annotypedict.keys()): # non matching type for original name -> create alterntive name
                self.create_annotationtype(product_id=product_id,name=name_alt, vector_type=annotationtype_to_vectortype[annotationType], color_code=classes_col[classToSend], sort_order=classToSend)
                annotypedict = getAnnotationTypes()
                mergeLocalClasses[(annotationType,labelId)] = name_alt
                return annotypedict[name_alt]['id'] 
            else:
                raise ExactProcessError('Unable to create annotation type for class'+name)

        filename = database.slideFilenameForID(slideuid)

        imageset_details = self.retrieve_imageset(imageset_id)
        for imset in imageset_details['images']:
            if (imset['name']==filename):
                image_id=imset['id']

        if (image_id is None):
            raise ExactProcessError('No matching image found.')

        annos = np.array(self.retrieve_annotations(image_id))

        # retrieve all annotation types
        annotypedict = getAnnotationTypes()

        # reformat to dict according to uuid
        uuids = np.array([anno['unique_identifier'] for anno in annos])

        annodict = {uuid:annos[np.where(uuids==uuid)] for uuid in uuids}

        database.loadIntoMemory(slideuid)

        classes = {y:x for x,y,col in database.getAllClasses()}
        classes_col = {y:col for x,y,col in database.getAllClasses()}
        classes_rev = {x:y for x,y,col in database.getAllClasses()}

        uidToSend, nameToSend = database.getExactPerson()
        pending_requests=0
        self.log(0,f'Checking all {len(database.annotations.keys())} entries of DB slide {slideuid}')
        
        for cntr,annokey in enumerate(database.annotations.keys()):
            if not (self.multi_threaded):
                self.progress(0.5+(float(cntr)*0.5/(len(database.annotations.keys())+0.0001)), callback=callback)
            dbanno = database.annotations[annokey]
            # look through annotations
            labelToSend = [lab.classId for lab in dbanno.labels if lab.annnotatorId==uidToSend]
            labelToSendIdx = [i for i,lab in enumerate(dbanno.labels) if lab.annnotatorId==uidToSend]
            if len(labelToSend)==0:
                # not from expert marked as exact user --> ignore
                continue
            if (dbanno.guid in annodict.keys()):
                le_array = [datetime.datetime.strptime(_anno['last_edit_time'], "%Y-%m-%dT%H:%M:%S.%f") for _anno in annodict[dbanno.guid]]
                lastedit = np.max(le_array) # maximum last_edit time is most recent for uuid
                # highlander rule --> whoever edited last will win (for the complete annotation)

                if (lastedit.timestamp()>dbanno.lastModified):
                    # more recent version exists online
                    print('More recent version is online -> do not push')
                    # TODO: Implement storing of my version in case of creation
                elif (lastedit.timestamp()+EPS_TIME_CONVERSION<dbanno.lastModified):
                    # local annotation is more recent --> update
                    IdToSend = [lab.exact_id for lab in dbanno.labels if lab.annnotatorId==uidToSend]
                    for lts, idts,i in zip(labelToSend,IdToSend,labelToSendIdx):
                        # case: exact_id is known
                        classToSend=lts # used in embedded function
                        if (idts is not None) and (idts>0):
                            print('Remote ID known:',idts,'=> Forcing update, remote is:', lastedit.timestamp(), 'local is:',dbanno.lastModified)
                            self.update_annotation(image_id=image_id,annotation_id=idts, annotationtype_id=get_or_create_annotationtype(lts,dbanno.annotationType), last_modified=dbanno.lastModified, vector=dbanno.coordinates.tolist(), deleted=dbanno.deleted, guid=dbanno.guid, description=dbanno.text)                 
                        else:
                            # case: exact_id is unknown
                            # can have the following causes:
                            # 1. label is new for annotation --> in this case, it has to be created
                            # 2. exact_id is missing in database --> avoided by first receiving from server
                            if (self.multi_threaded):
                                context = {'labeluid': i, 'annouid': dbanno.uid}
                                annotationtype = get_or_create_annotationtype(lts, dbanno.annotationType)
                                self.jobqueue.put((0,partial(self.create_annotation, image_id=image_id, annotationtype_id=annotationtype, deleted=dbanno.deleted,last_modified=dbanno.lastModified, vector=dbanno.coordinates.tolist(), guid=dbanno.guid, description=dbanno.text),context))
                                pending_requests+=1
#                                label = dbanno.labels[i]
#                                database.setAnnotationLabel(classId=label.classId,  person=label.annnotatorId, entryId=label.uid, annoIdx=dbanno.uid, exact_id=det['annotations']['id'])
#                                label.exact_id = det['annotations']['id']
                            else:
                                det = self.create_annotation(image_id=image_id, annotationtype_id=get_or_create_annotationtype(lts, dbanno.annotationType), deleted=dbanno.deleted,last_modified=dbanno.lastModified, vector=dbanno.coordinates.tolist(), guid=dbanno.guid, description=dbanno.text)
                                # add new exact_id to DB field
                                label = dbanno.labels[i]
                                database.setAnnotationLabel(classId=label.classId,  person=label.annnotatorId, entryId=label.uid, annoIdx=dbanno.uid, exact_id=det['annotations']['id'])
                                label.exact_id = det['annotations']['id']
                                self.log(1,'Updating local exact_id (previously unknown)')
                else:
                    # Equal time stamps --> ignore
                    pass
            else:
                for i, classToSend in zip(labelToSendIdx,labelToSend):
                    if (self.multi_threaded):
                        context = {'labeluid': i, 'annouid': dbanno.uid}
                        annotationtype = get_or_create_annotationtype(classToSend, dbanno.annotationType)
                        self.jobqueue.put((0,partial(self.create_annotation, image_id=image_id, annotationtype_id=get_or_create_annotationtype(classToSend, dbanno.annotationType), deleted=dbanno.deleted,last_modified=dbanno.lastModified, vector=dbanno.coordinates.tolist(), guid=dbanno.guid, description=dbanno.text),context))
                        pending_requests+=1
                    else:
                        annotationtype=get_or_create_annotationtype(classToSend, dbanno.annotationType)
                        det = self.create_annotation(image_id=image_id, annotationtype_id=annotationtype, deleted=dbanno.deleted, last_modified=dbanno.lastModified, vector=dbanno.coordinates.tolist(), guid=dbanno.guid, description=dbanno.text)
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
            database.setAnnotationLabel(classId=label.classId,  person=label.annnotatorId, entryId=label.uid, annoIdx=dbanno.uid, exact_id=res['annotations']['id'])
            database.addTriggers()
            label.exact_id = res['annotations']['id']

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
                    database.loadIntoMemory(database.annotationsSlide)


        self.progress(1, callback=callback)



    def delete(self, url, **kwargs):
        ret= requests.delete(self.serverurl+url, auth=(self.username, self.password), **kwargs)
        try:
            return ret.status_code, json.loads(ret.text)
        except:
            return ret.status_code, ret.text

    def post(self, url, data, files=None, **kwargs):
        try:
            ret= requests.post(self.serverurl+url, auth=(self.username, self.password), data=data, files=files, **kwargs)
        except requests.exceptions.ConnectionError as e:
            return self.post(url, data, files, **kwargs)
        try:
            return ret.status_code, json.loads(ret.text)
        except:
            return ret.status_code, ret.text
    
    def get(self, url):
        ret= requests.get(self.serverurl+url, auth=(self.username, self.password))
        return ret.status_code, ret.text

    def getfile(self, url, target_folder, callback) -> (int, str, bytes):
        with requests.get(self.serverurl+url, auth=(self.username, self.password), stream=True) as r:
            r.raise_for_status()
            target_file = target_folder+os.sep+get_filename_from_cd(r.headers['content-disposition'])
            f = open(target_file,'wb')
            siz=0
            for chunk in r.iter_content(chunk_size=8192): 
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)
                    siz += len(chunk)
                    prog=float(siz)/int(r.headers['content-length'])
                    self.progress(prog, callback=callback)
            f.close()
        return r.status_code, target_file
