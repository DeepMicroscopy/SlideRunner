import cv2
import numpy as np
from SlideRunner.dataAccess.exact import *
from SlideRunner.dataAccess.database import Database
import os

EXACT_UNITTEST_URL = 'https://exact.cs.fau.de/srut/'




def test_setup():
    cleanup()
    exm = ExactManager('sliderunner_unittest','unittestpw', EXACT_UNITTEST_URL)
    imageset=1
    product_id=1

    # Delete all previous annotation types
    annoTypes = exm.retrieve_annotationtypes(product_id)
    for at in annoTypes:
        http_status, res = exm.delete_annotationtype(at['id'])
        assert(http_status==200)

    # Add new annotation type
    ret = exm.create_annotationtype(product_id, 'bogus', vector_type=1)

    assert(len(exm.retrieve_annotationtypes(product_id))==1)

    # And delete it, again
    http_status, res = exm.delete_annotationtype(int(ret['annotationType']['id']))
    assert(http_status==200)

    exm.terminate()

def test_images():
    exm = ExactManager('sliderunner_unittest','unittestpw', EXACT_UNITTEST_URL)

    # Delete all images

    imageset = exm.retrieve_imagesets()[0]['id']
    product_id=1

    allImagesInSet = exm.retrieve_imagelist(imageset)
    for img_id in allImagesInSet.dict():
        http_status, _ = exm.delete_image(img_id)
        assert(http_status==200)

    allImagesInSet = exm.retrieve_imagelist(imageset)
    assert(len(list(allImagesInSet.dict().keys()))==0) # all images gone

    # generate dummy image
    dummy=np.random.randint(0,255, (200,200,3))
    cv2.imwrite('dummy.tiff', dummy)

    exm.upload_image_to_imageset(imageset_id=1, filename='dummy.tiff')

    imagesets= exm.retrieve_imagesets()
    assert(len(imagesets[0]['images'])==1)
    assert(imagesets[0]['images'][0]['name']=='dummy.tiff')

    allImagesInSet = exm.retrieve_imagelist(imageset)
    # select first image in imageset
    imageid = list(allImagesInSet.dict().keys())[0]

    assert(exm.download_image(imageid,'.') == './dummy.tiff')

    http_status, res = exm.delete_image(imageid)
    assert(http_status==200) # all gone, again

    allImagesInSet = exm.retrieve_imagelist(imageset)
    assert(len(list(allImagesInSet.dict().keys()))==0) # all images gone

    exm.terminate()

    os.remove('dummy.tiff')

def cleanup():
    exm = ExactManager('sliderunner_unittest','unittestpw', EXACT_UNITTEST_URL)

    imageset = exm.retrieve_imagesets()[0]['id']

    # loop through dataset, delete all annotations and images
    allImagesInSet = exm.retrieve_imagelist(imageset)
    # select first image in imageset
    for imageid in list(allImagesInSet.dict().keys()):
        annos = exm.retrieve_annotations(imageid)
        for anno in annos:
            exm.delete_annotation(anno['id'], keep_deleted_element=False)
        exm.delete_image(imageid)
    
    product_id=1

    # Delete all previous annotation types
    annoTypes = exm.retrieve_annotationtypes(product_id)
    for at in annoTypes:
        http_status, res = exm.delete_annotationtype(at['id'])
        assert(http_status==200)

    exm.terminate()

def test_pushannos():
    imageset=1
    product_id=1

    exm = ExactManager('sliderunner_unittest','unittestpw', EXACT_UNITTEST_URL)

    randstr = ''.join(['{:02x}'.format(x) for x in np.random.randint(0,255,6)])
    imagename = f'dummy{randstr}.tiff'

    # generate dummy image
    dummy=np.random.randint(0,255, (200,200,3))
    cv2.imwrite(imagename, dummy)

    exm.upload_image_to_imageset(imageset_id=imageset, filename=imagename)

    imageset_details = exm.retrieve_imageset(imageset)
#        print(imageset_details)
    for imset in imageset_details['images']:
        if (imset['name']==imagename):
            imageid=imset['id']


    DB = Database().create(':memory:')
#    DB = Database().create('test.sqlite')
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
    annos = exm.retrieve_annotations(imageid)
    for anno in annos:
        exm.delete_annotation(anno['id'], keep_deleted_element=False)

#    for anno in exm.retrieve_annotations(imageid):
#        print(anno) 
    # All annotations have been removed
    assert(len(exm.retrieve_annotations(imageid))==0)

    exm.sync(imageid, imageset_id=imageset, product_id=product_id, slideuid=slideuid, database=DB)

    # Only 2 annotations have been inserted
    assert(len(exm.retrieve_annotations(imageid))==2)

    uuids = [x['unique_identifier'] for x in exm.retrieve_annotations(imageid)]
    # All were created with correct guid
    for dbanno in list(DB.annotations.keys())[:-1]:
        assert(DB.annotations[dbanno].guid in uuids)

    print('--- resync ---')

    # Sync again
    exm.sync(imageid, imageset_id=imageset, product_id=product_id, slideuid=slideuid, database=DB)

    # No change
    assert(len(exm.retrieve_annotations(imageid))==2)

    # All were created with correct guid
    uuids = [x['unique_identifier'] for x in exm.retrieve_annotations(imageid)]
    for dbanno in list(DB.annotations.keys())[:-1]:
        assert(DB.annotations[dbanno].guid in uuids)

    print('--- local update created ---')

    # Now let's create a local update - keep same exact_id (crucial!)
    DB.loadIntoMemory(1)
    DB.setAnnotationLabel(classId=1, person=1, annoIdx=1, entryId=DB.annotations[1].labels[0].uid, exact_id=DB.annotations[1].labels[0].exact_id)

    # Sync again
    exm.sync(imageid, imageset_id=imageset, product_id=product_id, slideuid=slideuid, database=DB)

    # check if remote has been updated
    annos = exm.retrieve_annotations(imageid)
    for anno in annos:
        if (anno['id']==DB.annotations[1].labels[0].exact_id):
            assert(anno['annotation_type']['name']=='BB')
            annotype_id = anno['annotation_type']['id']

    # Now update remotely and see if changes are reflected
    newguid = str(uuid.uuid4())
    created = exm.create_annotation(image_id=imageid, annotationtype_id=annotype_id, vector=[[90,80],[20,30]], last_modified=time.time(), guid=newguid, description='abcdef' )

    exm.sync(imageid, imageset_id=imageset, product_id=product_id, slideuid=slideuid, database=DB)
    found=False
    for annoI in DB.annotations:
        anno=DB.annotations[annoI]
        if (anno.guid == newguid):
            found=True
            assert(anno.annotationType==AnnotationType.POLYGON)
            assert(anno.text=='abcdef')
            assert(anno.labels[0].exact_id==created['annotations']['id'])
    
    assert(found)
    
    # also check in stored database
    DB.loadIntoMemory(1)
    for annoI in DB.annotations:
        anno=DB.annotations[annoI]
        if (anno.guid == newguid):
            found=True
            assert(anno.annotationType==AnnotationType.POLYGON)
            assert(anno.labels[0].exact_id==created['annotations']['id'])

    # Clean up --> remove all annotations
    annos = exm.retrieve_annotations(imageid)
    for anno in annos:
        exm.delete_annotation(anno['id'], keep_deleted_element=False)

    # All gone
    assert(len(exm.retrieve_annotations(imageid))==0)

    # Now delete image
    exm.delete_image(imageid)

    os.remove(imagename)
    exm.terminate()

if __name__ == "__main__":
    test_setup()
    cleanup()
    test_images() 
    test_pushannos()    
    cleanup()
