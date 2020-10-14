import cv2
import numpy as np
from SlideRunner.dataAccess.exact import *
from SlideRunner.dataAccess.database import Database
import os

EXACT_UNITTEST_URL = 'https://exact.cs.fau.de/srut/'


from exact_sync.v1.api_client import ApiClient as client
from exact_sync.v1.api.image_sets_api import ImageSetsApi  # noqa: E501
from exact_sync.v1.api.teams_api import TeamsApi
from exact_sync.v1.rest import ApiException
from exact_sync.v1.models import ImageSet, Team


from exact_sync.v1.api.annotations_api import AnnotationsApi
from exact_sync.v1.api.images_api import ImagesApi
from exact_sync.v1.api.image_sets_api import ImageSetsApi
from exact_sync.v1.api.annotation_types_api import AnnotationTypesApi
from exact_sync.v1.api.products_api import ProductsApi
from exact_sync.v1.api.teams_api import TeamsApi

from exact_sync.v1.models import ImageSet, Team, Product, AnnotationType as ExactAnnotationType, Image, Annotation, AnnotationMediaFile
from exact_sync.v1.rest import ApiException
from exact_sync.v1.configuration import Configuration
from exact_sync.v1.api_client import ApiClient

from pathlib import Path

configuration = Configuration()
configuration.username = 'sliderunner_unittest'
configuration.password = 'unittestpw'
configuration.host = EXACT_UNITTEST_URL



def test_setup():

    client = ApiClient(configuration)
    apis = ExactAPIs(client)


#    annos = image_sets_api.list_image_sets(expand="product_set")
#    image_sets_api.retrieve_image_set(1, expand="product_set")

    # Delete all previous annotation types
    try:
        for at in apis.annotation_types_api.list_annotation_types().results:
            if not (at.deleted):
                apis.annotation_types_api.destroy_annotation_type(id=at.id)
    except:
        print('Unable to destroy annotation types')    


def test_images():

    client = ApiClient(configuration)
    apis = ExactAPIs(client)

    imageset =  apis.image_sets_api.list_image_sets().results[0].id

    # Delete all images
    product_id=1

    allImagesInSet = apis.images_api.list_images(omit="annotations").results
    for img in allImagesInSet:
        apis.images_api.destroy_image(id=img.id)

    allImagesInSet = apis.images_api.list_images(omit="annotations").results
    assert(len(allImagesInSet)==0) # all images gone

    # generate dummy image
    dummy=np.random.randint(0,255, (200,200,3))
    cv2.imwrite('dummy.png', dummy)



    apis.images_api.create_image(file_path='dummy.png', image_type=0, image_set=imageset).results

    allImagesInSet = apis.images_api.list_images(omit="annotations").results
    # select first image in imageset
    imageid = allImagesInSet[0].id

    assert(apis.images_api.retrieve_image(id=imageid).filename=='dummy.tiff')

    apis.images_api.download_image(id=imageid, target_path='./dummy-retrieved.png',original_image=True)
    retr = cv2.imread('dummy-retrieved.png')

    assert(np.all(retr==dummy))

    apis.images_api.destroy_image(id=imageid)

    allImagesInSet = apis.images_api.list_images(omit="annotations").results


    assert(len(allImagesInSet)==0) # all images gone


    os.remove('dummy.png')
    os.remove('dummy-retrieved.png')

def cleanup():

    client = ApiClient(configuration)
    apis = ExactAPIs(client)

    imageset =  apis.image_sets_api.list_image_sets().results[0].id

    # loop through dataset, delete all annotations and images
    allImagesInSet = apis.images_api.list_images(omit="annotations").results
    # select first image in imageset
    for image in allImagesInSet:
        annos = apis.annotations_api.list_annotations(id=image.id, pagination=False).results
        for anno in annos:
            apis.annotations_api.destroy_annotation(anno.id, keep_deleted_element=False)
        apis.images_api.destroy_image(id=image.id)
    
    product_id=1

    # Delete all previous annotation types
    annoTypes = apis.annotation_types_api.list_annotation_types(product_id).results
    for at in annoTypes:
        apis.annotation_types_api.destroy_annotation_type(at.id)

    assert(len(apis.annotation_types_api.list_annotation_types(product_id).results)==0)


def test_pushannos():
    imageset=1
    product_id=1

    client = ApiClient(configuration)
    apis = ExactAPIs(client)

    randstr = ''.join(['{:02x}'.format(x) for x in np.random.randint(0,255,6)])
    imagename = f'dummy{randstr}.png'

    imageset =  apis.image_sets_api.list_image_sets().results[0].id

    # generate dummy image
    dummy=np.random.randint(0,255, (200,200,3))
    cv2.imwrite(imagename, dummy)

    exm = ExactManager(username=configuration.username, password=configuration.password, serverurl=configuration.host)
    iset = exm.upload_image_to_imageset(imageset_id=imageset, filename=imagename)
#    apis.images_api.create_image(file_path=imagename, image_type=0, image_set=imageset).results
    imageset_details = apis.image_sets_api.retrieve_image_set(id=imageset, expand='images')

    imageid=imageset_details.images[0]['id']

    DB = Database().create(':memory:')

    # Add slide to database
    slideuid = DB.insertNewSlide(imagename,'')
    DB.insertClass('BB')
    DB.insertAnnotator('sliderunner_unittest')
    DB.insertAnnotator('otherexpert') # we will only send annotations of the marked expert
    DB.insertClass('POLY')

    coords = np.array([[100,200],[150,220],[180,250]])
    
    DB.insertNewPolygonAnnotation(annoList=coords, slideUID=1, classID=2, annotator=1)

    coords = np.array([[150,250],[350,220],[0,250]])
    DB.insertNewPolygonAnnotation(annoList=coords, slideUID=1, classID=2, annotator=1)

    coords = np.array([[150,255],[350,210],[50,250]])
    DB.insertNewPolygonAnnotation(annoList=coords, slideUID=1, classID=2, annotator=2)

    DB.setExactPerson(1)
    #empty image
    annos = apis.annotations_api.list_annotations(id=imageid, pagination=False).results

    for anno in annos:
        apis.annotations_api.destroy_annotation(id=anno.id)

#    for anno in exm.retrieve_annotations(imageid):
#        print(anno) 
    # All annotations have been removed
    assert(len(apis.annotations_api.list_annotations(id=imageid, pagination=False).results)==0)

    exm.sync(imageid, imageset_id=imageset, product_id=product_id, slideuid=slideuid, database=DB)

    # Only 2 annotations have been inserted
    assert(len(apis.annotations_api.list_annotations(imageid).results)==2)

    uuids = [x.unique_identifier for x in apis.annotations_api.list_annotations(imageid).results]
    # All were created with correct guid
    for dbanno in list(DB.annotations.keys())[:-1]:
        assert(DB.annotations[dbanno].guid in uuids)

    print('--- resync ---')

    # Sync again
    exm.sync(imageid, imageset_id=imageset, product_id=product_id, slideuid=slideuid, database=DB)

    # No change
    print('Length is now: ',len(apis.annotations_api.list_annotations(imageid).results))
    assert(len(apis.annotations_api.list_annotations(imageid).results)==2)

    # All were created with correct guid
    uuids = [x.unique_identifier for x in apis.annotations_api.list_annotations(imageid).results]
    for dbanno in list(DB.annotations.keys())[:-1]:
        assert(DB.annotations[dbanno].guid in uuids)

    print('--- local update created ---')

    # Now let's create a local update - keep same exact_id (crucial!)
    DB.loadIntoMemory(1)
    DB.setAnnotationLabel(classId=1, person=1, annoIdx=1, entryId=DB.annotations[1].labels[0].uid, exact_id=DB.annotations[1].labels[0].exact_id)

    # Sync again
    exm.sync(imageid, imageset_id=imageset, product_id=product_id, slideuid=slideuid, database=DB)

    # check if remote has been updated
#    annos = apis.annotations_api.list_annotations(id=imageid, pagination=False).results
    annos = np.array(apis.annotations_api.list_annotations(imageid, expand='annotation_type').results)

    assert(len(annos)>0)

    for anno in annos:
        if (anno.id==DB.annotations[1].labels[0].exact_id):
            assert(anno.annotation_type['name']=='BB')
            annotype_id = anno.annotation_type['id']

    # Now update remotely and see if changes are reflected
    newguid = str(uuid.uuid4())
    vector = list_to_exactvector([[90,80],[20,30]])
    vector['frame']=2
    lastModified=datetime.datetime.fromtimestamp(time.time()).strftime( "%Y-%m-%dT%H:%M:%S.%f")
    annotation = Annotation(annotation_type=annotype_id, vector=vector, image=imageid, unique_identifier=newguid, last_edit_time=lastModified, time=lastModified, description='abcdef')
    created = apis.annotations_api.create_annotation(body=annotation )

    exm.sync(imageid, imageset_id=imageset, product_id=product_id, slideuid=slideuid, database=DB)
    DB.loadIntoMemory(1, zLevel=None)
    found=False
    for annoI in DB.annotations:
        anno=DB.annotations[annoI]
        if (anno.guid == newguid):
            found=True
            assert(anno.annotationType==AnnotationType.POLYGON)
            assert(anno.text=='abcdef')

            assert(anno.labels[0].exact_id==created.id)
    
    assert(found)
    
    # also check in stored database
    DB.loadIntoMemory(1)
    for annoI in DB.annotations:
        anno=DB.annotations[annoI]
        if (anno.guid == newguid):
            found=True
            assert(anno.annotationType==AnnotationType.POLYGON)
            assert(anno.labels[0].exact_id==created.id)


    annos = apis.annotations_api.list_annotations(id=imageid, pagination=False).results
    for anno in annos:
        apis.annotations_api.destroy_annotation(anno.id, keep_deleted_element=False)


    # All gone
    assert(len(apis.annotations_api.list_annotations(id=imageid, pagination=False).results)==0)

    # Now delete image
    apis.images_api.destroy_image(id=imageid)

    os.remove(imagename)
    exm.terminate()

if __name__ == "__main__":
    test_setup()
    cleanup()
    test_images() 
    test_pushannos()    
    cleanup()
