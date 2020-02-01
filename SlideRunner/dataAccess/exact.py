import requests
import json
from requests.auth import HTTPBasicAuth
from SlideRunner.dataAccess.database import *
from SlideRunner.dataAccess.annotations import *
import time
import datetime
import re

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

    def __init__(self, username:str=None, password:str=None, serverurl:str=None):
        self.username = username
        self.password = password
        self.serverurl = serverurl

        self.loggedIn=False
        #if (self.username is not None):
        #    self.login(self.username, self.password, self.serverurl)

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

    def download_image(self, image_id:int, target_folder:str):
        status,filename,blob = self.getfile('images/api/image/download/%d/' % image_id)
        if (status==200):
            open(target_folder+os.sep+filename, 'wb').write(blob)
            return target_folder+os.sep+filename
        else:
            return ''

    def retrieve_annotations(self,dataset_id:int) -> list:
        obj = self.json_get_request(self.serverurl+'annotations/api/annotation/load/?image_id=%d' % dataset_id)
        if 'annotations' in obj:
            return obj['annotations']
        else:
            return []

    def delete_image(self, image_id:int):
        status, obj = self.get('images/api/image/delete/%d/'%image_id)
        return status, obj


    def upload_image_to_imageset(self, imageset_id:int, filename:str) -> bool:
        status, obj = self.post('images/image/upload/%d/'%imageset_id, data={}, headers={'referer': self.serverurl}, files={'files[]': open(filename, 'rb')}, timeout=20)
        if (status==200):
            return True
        else:
            return False

    def add_product_to_imageset(self, product_id:int, imageset_id:int):
        data = {'image_set_id':imageset_id,
                'product_id':product_id}

        obj = self.post('images/api/imageset/product/add/',data=data )       
        return obj


    def retrieve_imagelist(self, imageset_id:int) -> list:
        # this is really a format fuckup. But let's parse it nevertheless...
        il = self.csv_get_request(self.serverurl+'images/imagelist/%d/' % imageset_id)
        return ExactImageList([[int(x.split('?')[0].split('/')[-2]),x.split('?')[1]] for x in il if '?' in x])


    def retrieve_and_insert(self, dataset_id:int, filename:str, database:Database, **kwargs ):

        def createDatabaseObject():
            if (vector_type == 3): # line
                annoId = database.insertNewPolygonAnnotation(annoList=coords, slideUID=slideuid, classID=classes_rev[class_name], annotator=persons[person_name])
            elif (vector_type in [4,5]): # polygon or line
                annoId = database.insertNewPolygonAnnotation(annoList=coords, slideUID=slideuid, classID=classes_rev[class_name], annotator=persons[person_name], closed=anno['annotation_type']['closed'])
            elif (vector_type in [1,6]): # rectangle
                annoId = database.insertNewAreaAnnotation(x1=anno['vector']['x1'],y1=anno['vector']['y1'],x2=anno['vector']['x2'],y2=anno['vector']['y2'], slideUID=slideuid, classID=classes_rev[class_name], annotator=persons[person_name])                
            elif (vector_type==2): # ellipse
                r1 = int(round((anno['vector']['x2']-anno['vector']['x1'])/2))
                xpos = anno['vector']['x1']+r1
                r2 = int(round((anno['vector']['y2']-anno['vector']['y1'])/2))
                ypos = anno['vector']['y1']+r2
                if ('SpotCircleRadius' in kwargs) and (r1==r2) and (r1==kwargs['SpotCircleRadius']):
                    annoId = database.insertNewSpotAnnotation(xpos_orig=xpos,ypos_orig=ypos, slideUID=slideuid, classID=classes_rev[class_name], annotator=persons[person_name], typeId=5)                
                else:
                    annoId = database.insertNewAreaAnnotation(x1=anno['vector']['x1'],y1=anno['vector']['y1'],x2=anno['vector']['x2'],y2=anno['vector']['y2'], slideUID=slideuid, classID=classes_rev[class_name], annotator=persons[person_name], typeId=5)                
            else:
                raise NotImplementedError('Vector Type %d is unknown.' % vector_type)
            if (anno['deleted']):
                database.removeAnnotation(database.guids[uuid],onlyMarkDeleted=True)
            
            return annoId

        annos = self.retrieve_annotations(dataset_id)

        createClasses = True if 'createClasses' not in kwargs else kwargs['createClasses']
        
        slideuid = database.findSlideWithFilename(filename,slidepath='')
        
        if (slideuid is None):
            raise ExactProcessError('Slide not in database. Please add it first.')

        database.loadIntoMemory(slideuid)
        database.deleteTriggers()
        classes = {y:x for x,y in database.getAllClasses()}
        classes_rev = {x:y for x,y in database.getAllClasses()}

        persons = {x:y for x,y in database.getAllPersons()}
        for anno in annos:
           # print(anno)
            class_name = anno['annotation_type']['name']
            person_name = anno['last_editor']['name']
            uuid = anno['unique_identifier']

            if person_name not in persons.values():
                database.insertAnnotator(person_name)
                persons = {x:y for x,y in database.getAllPersons()}

            if (class_name not in classes.values()):
                if not createClasses:
                    raise AccessViolationError('Not permitted to create new classes, but class %d not found' % anno['annotation_type']['name'])
                else:
                    database.insertClass(class_name)
                    classes = {x:y for y,x in database.getAllClasses()}
                    classes_rev = {x:y for x,y in database.getAllClasses()}
            
            vector_type = anno['annotation_type']['vector_type']
            vlen = int(len(anno['vector'])/2)
            
            lastedit = datetime.datetime.strptime(anno['last_edit_time'], "%Y-%m-%dT%H:%M:%S.%f")
            
            coords = [[anno['vector']['x%d' % (x+1)] for x in range(vlen)],[anno['vector']['y%d' % (x+1)]for x in range(vlen)]]
            coords = np.array(coords).T.tolist() # transpose

            if (uuid not in database.guids.keys()) and (vlen>0):
                # Is new - woohay!
                annoId = createDatabaseObject()
                database.setGUID(annoid=annoId, guid=uuid)
                database.setLastModified(annoid=annoId, lastModified=lastedit.timestamp())
            elif (vlen>0):
                print('Object exists, last edit was: ',lastedit.timestamp(), database.annotations[database.guids[uuid]].lastModified)
                if (lastedit.timestamp()>database.annotations[database.guids[uuid]].lastModified):
                    database.removeAnnotation(database.guids[uuid],onlyMarkDeleted=False)
                    #TODO: recreate
                    createDatabaseObject()
            else:
                print('Ignoring zero-coordinate object')
        database.addTriggers()

    def delete_annotation(self, annotation_id:int,keep_deleted_element:bool=True) -> bool:
        data = {'annotation_id':annotation_id,
                'keep_deleted_element':keep_deleted_element}
        status, ret = self.delete(f'annotations/api/annotation/delete/?annotation_id={annotation_id}&keep_deleted_element={keep_deleted_element}')
        if (status==200):
            return True
        else:
            return False

    def create_annotation(self, image_id:int, annotationtype_id:int, vector:list, blurred:bool=False, guid:str='', description:str=''):
        data = {
            'image_id': image_id,
            'annotation_type_id' : annotationtype_id,
            'vector' : list_to_exactvector(vector),
            'unique_identifier' : guid,
            'blurred' : blurred,
            'description' : description
        }
        status, ret = self.post('annotations/api/annotation/create/', data=json.dumps(data), headers={'content-type':'application/json'})
        if status==201:
            return True
        else: 
#            print(ret)
            return False
            
    
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
                'name': name,
                'color_code': color_code,
                'sort_order':sort_order,
                'vector_type': vector_type,
                'default_width': default_width,
                'default_height': default_height,
                'area_hit_test':area_hit_test,
                'closed':closed}

        return self.post('administration/api/annotation_type/create/', data=data)

    def retrieve_and_upload(self, dataset_id:int,imageset_id:int, product_id:int, filename:str, database:Database, image_id:str=None, **kwargs ):
        def getAnnotationTypes():
            annotypes = self.retrieve_annotationtypes(imageset_id)

            annotypedict = {annotype['name']:annotype for annotype in annotypes}
            return annotypedict 


        imageset_details = self.retrieve_imageset(imageset_id)
#        print(imageset_details)
        for imset in imageset_details['images']:
            if (imset['name']==filename):
                image_id=imset['id']

        if (image_id is None):
            raise ExactProcessError('No matching image found.')

        annos = self.retrieve_annotations(image_id)

        # retrieve all annotation types
        annotypedict = getAnnotationTypes()

        # reformat to dict according to uuid
        annodict = {anno['unique_identifier']:anno for anno in annos}

        # loop through annotations
        slideuid = database.findSlideWithFilename(filename,slidepath='')
        
        if (slideuid is None):
            raise ExactProcessError('Slide not in database. Please add it first.')

        annotationtype_to_vectortype = {
            AnnotationType.SPOT: 2,
            AnnotationType.AREA: 1,
            AnnotationType.POLYGON: 5,
            AnnotationType.SPECIAL_SPOT: 2,
            AnnotationType.CIRCLE: 2,
        }

        database.loadIntoMemory(slideuid)

        classes = {y:x for x,y in database.getAllClasses()}
        classes_rev = {x:y for x,y in database.getAllClasses()}

        uidToSend = database.getExactPerson()
        
        for annokey in database.annotations.keys():
            dbanno = database.annotations[annokey]
            # look through annotations
            labelToSend = [lab.classId for lab in dbanno.labels if lab.annnotatorId==uidToSend]
            if len(labelToSend)==0:
                # not from expert marked as exact user --> ignore
                break
            if (dbanno.guid in annodict.keys()):
                print('Annotation exists remotely')
            else:
                print('Annotation does not yet exist')
                for classToSend in labelToSend:
                    if ((classes[classToSend] in annotypedict.keys())
                    and (annotationtype_to_vectortype[dbanno.annotationType]==annotypedict[classes[classToSend]]['vector_type'])):
                        self.create_annotation(image_id=image_id, annotationtype_id=annotypedict[classes[classToSend]]['id'], vector=dbanno.coordinates.tolist(), guid=dbanno.guid)
                    elif (classes[classToSend] in annotypedict.keys()):
                        # class exists but is of wrong type
                        print('Class exists')
                        # TODO --> create new class with new type and new name OR use class created with this step
                        pass
                    else:
                        # class does not exist --> create
                        self.create_annotationtype(product_id=product_id,name=classes[classToSend], vector_type=annotationtype_to_vectortype[dbanno.annotationType], color_code=get_hex_color(classToSend), sort_order=classToSend)
                        annotypedict = getAnnotationTypes()
                        self.create_annotation(image_id=image_id, annotationtype_id=annotypedict[classes[classToSend]]['id'], vector=dbanno.coordinates.tolist(), guid=dbanno.guid)

                        pass

#                print(classes, annotypedict.keys())


    def delete(self, url, **kwargs):
        ret= requests.delete(self.serverurl+url, auth=(self.username, self.password), **kwargs)
        try:
            return ret.status_code, json.loads(ret.text)
        except:
            return ret.status_code, ret.text

    def post(self, url, data, files=None, **kwargs):
        ret= requests.post(self.serverurl+url, auth=(self.username, self.password), data=data, files=files, **kwargs)
        try:
            return ret.status_code, json.loads(ret.text)
        except:
            return ret.status_code, ret.text
    
    def get(self, url):
        ret= requests.get(self.serverurl+url, auth=(self.username, self.password))
        return ret.status_code, ret.text

    def getfile(self, url) -> (int, str, bytes):
        ret= requests.get(self.serverurl+url, auth=(self.username, self.password))
        return ret.status_code, get_filename_from_cd(ret.headers.get('content-disposition')), ret.content
