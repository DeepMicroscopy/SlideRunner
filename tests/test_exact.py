import cv2
import numpy as np
from SlideRunner.dataAccess.exact import *
from SlideRunner.dataAccess.database import Database
import os

EXACT_UNITTEST_URL = 'https://exact.cs.fau.de/srut/'

def test_retrieve():
    exm = ExactManager('sliderunner_unittest','unittestpw', EXACT_UNITTEST_URL)
    allImagesInSet = exm.retrieve_imagelist(59)
    print(allImagesInSet.dict())

    # select first image in imageset
    imageid = list(allImagesInSet.dict().keys())[0]

    # retrieve annotations from first image in imageset
    annos = exm.retrieve_annotations(imageid)

    assert(isinstance(annos,list))
    assert(len(annos)>0)
#    print(len(annos), annos[0])

    DB = Database().create(':memory:')
    # Add slide to database
    DB.insertNewSlide(allImagesInSet.dict()[imageid],'')
    
    exm.retrieve_and_insert(973, filename=allImagesInSet.dict()[imageid], database=DB)
    oldCount = DB.execute('SELECT COUNT(*) FROM Annotations where slide==1').fetchone()[0]

    # try once again - number of objets in DB needs to be constant
    exm.retrieve_and_insert(973, filename=allImagesInSet.dict()[imageid], database=DB)
    newCount = DB.execute('SELECT COUNT(*) FROM Annotations where slide==1').fetchone()[0]
    print('Newcount:',newCount,oldCount)
    assert(oldCount==newCount)

    # fake new GUID for an entry
    DB.execute('UPDATE Annotations set guid="" where uid==1')

    exm.retrieve_and_insert(973, filename=allImagesInSet.dict()[imageid], database=DB)
    newCount = DB.execute('SELECT COUNT(*) FROM Annotations where slide==1').fetchone()[0]
    print('Newcount:',newCount,oldCount)
    assert(oldCount==newCount-1)

    # make DB entry deprecated
    DB.deleteTriggers()
    DB.dbcur.execute('UPDATE Annotations set lastModified=10.0 where uid==3')
    exm.retrieve_and_insert(973, filename=allImagesInSet.dict()[imageid], database=DB)
    newCount = DB.execute('SELECT COUNT(*) FROM Annotations where slide==1').fetchone()[0]
    assert(oldCount==newCount-1)



def test_setup():
    exm = ExactManager('sliderunner_unittest','unittestpw', EXACT_UNITTEST_URL)
    imageset=1
    product_id=1

    # Delete all previous annotation types
    annoTypes = exm.retrieve_annotationtypes(product_id)
    for at in annoTypes:
        http_status, res = exm.delete_annotationtype(at['id'])
        assert(http_status==200)

    # Add new annotation type
    http_status, res = exm.create_annotationtype(product_id, 'bogus', vector_type=1)
    assert(http_status==201)

    assert(len(exm.retrieve_annotationtypes(product_id))==1)

    # And delete it, again
    http_status, res = exm.delete_annotationtype(int(res['annotationType']['id']))
    assert(http_status==200)

def test_images():
    exm = ExactManager('sliderunner_unittest','unittestpw', EXACT_UNITTEST_URL)

    # Delete all images

    imageset=1
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

    allImagesInSet = exm.retrieve_imagelist(imageset)
    # select first image in imageset
    imageid = list(allImagesInSet.dict().keys())[0]

    assert(exm.download_image(imageid,'.') == './dummy.tiff')

    http_status, res = exm.delete_image(imageid)
    assert(http_status==200) # all gone, again

    allImagesInSet = exm.retrieve_imagelist(imageset)
    assert(len(list(allImagesInSet.dict().keys()))==0) # all images gone

    os.remove('dummy.tiff')

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
    # Add slide to database
    DB.insertNewSlide(imagename,'')
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

    exm.retrieve_and_upload(imageid, imageset_id=imageset, product_id=product_id, filename=imagename, database=DB)

    # Only 2 annotations have been inserted
    assert(len(exm.retrieve_annotations(imageid))==2)

    # All were created with correct guid
    for dbanno, anno in zip(DB.annotations, exm.retrieve_annotations(imageid)):
        assert(anno['unique_identifier']==DB.annotations[dbanno].guid)

    # Sync again
    exm.retrieve_and_upload(imageid, imageset_id=imageset, product_id=product_id, filename=imagename, database=DB)

    # No change
    assert(len(exm.retrieve_annotations(imageid))==2)

    # All were created with correct guid
    for dbanno, anno in zip(DB.annotations, exm.retrieve_annotations(imageid)):
        assert(anno['unique_identifier']==DB.annotations[dbanno].guid)

    # Clean up --> remove all annotations
    annos = exm.retrieve_annotations(imageid)
    for anno in annos:
        exm.delete_annotation(anno['id'], keep_deleted_element=False)

    # All gone
    assert(len(exm.retrieve_annotations(imageid))==0)

    # Now delete image
    exm.delete_image(imageid)


if __name__ == "__main__":
#    test_setup()
#    test_images() 
    test_pushannos()    
