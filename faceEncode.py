from imutils import paths
import face_recognition
import argparse
import pickle
import cv2
import os
from sklearn.neighbors import KDTree
import numpy as np
import constants
import multiprocessing as mp
import functools


def encode_images(imagePath,detection_method):
    knownEncodings = []
    knownNames = []
    name = imagePath.split(os.path.sep)[-2]
 
    # load the input image and convert it from BGR (OpenCV ordering)
    # to dlib ordering (RGB)
    image = cv2.imread(imagePath)
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # detect the (x, y)-coordinates of the bounding boxes
    # corresponding to each face in the input image
    boxes = face_recognition.face_locations(rgb,
        model=detection_method)
 
    # compute the facial embedding for the face
    encodings = face_recognition.face_encodings(rgb, boxes)
 
    # loop over the encodings
    for encoding in encodings:
        # add each encoding + name to our set of known names and
        # encodings
        knownEncodings.append(encoding)
        knownNames.append(name)
    return (knownEncodings,knownNames)


def process_images():
    # construct the argument parser and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--dataset", required=True,
        help="path to input directory of faces + images")
    ap.add_argument("-e", "--encodings", required=True,
        help="path to serialized db of facial encodings")
    ap.add_argument("-d", "--detection-method", type=str, default="cnn",
        help="face detection model to use: either `hog` or `cnn`")
    ap.add_argument("-fnn","--fast-nn",action="store_true")
    ap.add_argument("-cores","--cores",required=False,type=int,default=1,
                    help="no of cores to run on, will decide the parallelism")
    args = vars(ap.parse_args())

    # grab the paths to the input images in our dataset
    print("[INFO] quantifying faces...")
    imagePaths = list(paths.list_images(args["dataset"]))
    knownEncodings = []
    knownNames = []
    mp_batch_size = args["cores"]*10
    encode_images_with_detection_method = functools.partial(encode_images,
                                              detection_method=args["detection_method"])
    # loop over the image paths using batching for multiprocessing
    for i in range(0,len(imagePaths),mp_batch_size):
        image_batch = imagePaths[i:i+mp_batch_size]
        # using pool for parallelism for 
        with mp.Pool(args["cores"]*2) as pool:
            encodings_names_list = pool.map(encode_images_with_detection_method,image_batch)
        for (encodings,names) in encodings_names_list:
            knownEncodings.extend(encodings)
            knownNames.extend(names)
        print("finished encoding {%d}/{%d} images"%(i+mp_batch_size,len(imagePaths)))

    # dump the facial encodings + names to disk
    print("[INFO] serializing encodings...")
    # select encoding as kdtree or list based on user args
    encoding_structure = constants.ENC_LIST
    if args["fast_nn"]:
        encoding_structure = constants.ENC_KDTREE     
        knownEncodings = KDTree(np.asarray(knownEncodings),leaf_size=constants.LEAF_SIZE_KDTREE)
    data = { constants.ENCODINGS: knownEncodings,
            constants.NAMES: knownNames, 
            constants.ENCODING_STRUCTURE : encoding_structure
            }
    f = open(args["encodings"], "wb")
    f.write(pickle.dumps(data))
    f.close()


if __name__ == "__main__" :
    process_images()
