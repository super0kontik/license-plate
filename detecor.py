# This code is written at BigVision LLC. It is based on the OpenCV project. It is subject to the license terms in the LICENSE file found in this distribution and at http://opencv.org/license.html

# Usage example:  python3 object_detection_yolo.py --video=run.mp4
#                 python3 object_detection_yolo.py --image=bird.jpg

import cv2 as cv
import argparse
import sys
import numpy as np
import os.path
from datetime import datetime
import math
from tensorflow import keras

alphabets_dic = {
    0: '0', 1: '1', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9',
    10: 'A', 11: 'B', 12: 'C', 13: 'D', 14: 'E', 15: 'F', 16: 'G', 17: 'H', 18: 'I', 19: 'J',
    20: 'K', 21: 'L', 22: 'M', 23: 'N', 24: 'O', 25: 'P', 26: 'Q', 27: 'R', 28: 'S', 29: 'T',
    30: 'U', 31: 'V', 32: 'W', 33: 'X', 34: 'Y', 35: 'Z'
  }

recogn_model = keras.models.load_model("cnn_classifier2.h5")

# Initialize the parameters
confThreshold = 0.2  #Confidence threshold
nmsThreshold = 0.1  #Non-maximum suppression threshold
char_conf_threshold = 0.0
inpWidth = 608  #608  || 416   #Width of network's input image
inpHeight = 608  #608  || 416   #Height of network's input image

parser = argparse.ArgumentParser(description='Object Detection using YOLO in OPENCV')
parser.add_argument('--image', help='Path to image file.')
parser.add_argument('--video', help='Path to video file.')
args = parser.parse_args()

# Load names of classes
classesFile = "classes.names";

classes = None
with open(classesFile, 'rt') as f:
    classes = f.read().rstrip('\n').split('\n')

# Give the configuration and weight files for the model and load the network using them.

modelConfiguration = "darknet-yolov3.cfg";
modelWeights = "lapi.weights";

net = cv.dnn.readNetFromDarknet(modelConfiguration, modelWeights)
net.setPreferableBackend(cv.dnn.DNN_BACKEND_OPENCV)
net.setPreferableTarget(cv.dnn.DNN_TARGET_CPU)

# Get the names of the output layers
def getOutputsNames(net):
    # Get the names of all the layers in the network
    layersNames = net.getLayerNames()
    # Get the names of the output layers, i.e. the layers with unconnected outputs
    return [layersNames[i[0] - 1] for i in net.getUnconnectedOutLayers()]


def get_line_length(x1, y1, x2, y2):
    vec = (x2 - x1, y2 - y1)
    vec_len = math.sqrt(vec[0]**2 + vec[1]**2)
    return vec_len


def get_angle(x1, y1, x2, y2):
    k = (y2 - y1) / (x2 - x1)
    print('K: '+ str(k))
    angle = round(math.degrees(math.atan(k)))
    return angle


def rotate_img(img, angle):
    num_rows, num_cols = img.shape[:2]
    rotation_matrix = cv.getRotationMatrix2D((num_cols / 2, num_rows / 2), angle, 1)
    img_rotation = cv.warpAffine(img, rotation_matrix, (num_cols, num_rows))
    # cv.imshow('Rotation', img_rotation)
    # cv.waitKey(0)
    return img_rotation


def cut(img):
    height, width, channels = img.shape
    y_upper = 0
    for row in img:
        r1 = row[0][0]
        g1 = row[0][1]
        b1 = row[0][2]

        r2 = row[width-1][0]
        g2 = row[width-1][1]
        b2 = row[width-1][2]

        if (r1 != 0 and g1 != 0 and b1 != 0) or (r2 != 0 and g2 != 0 and b2 != 0) :
            break
        else:
            y_upper += 1

    y_lower = height - 1
    while y_lower > 0:
        r1 = img[y_lower][0][0]
        g1 = img[y_lower][0][1]
        b1 = img[y_lower][0][2]

        r2 = img[y_lower][width - 1][0]
        g2 = img[y_lower][width - 1][1]
        b2 = img[y_lower][width - 1][2]
        if (r1 != 0 and g1 != 0 and b1 != 0) or (r2 != 0 and g2 != 0 and b2 != 0) :
            break
        else:
            y_lower -= 1
    img = img[y_upper: y_lower, 0:width]
    # cv.imshow('Cropped', img)
    # cv.waitKey(0)
    return img

def separate(img, hor_part):
    height, width, channels = img.shape
    print(width)
    step = round(width*hor_part)
    pos = step
    i = 0
    while pos < width:
        img = cv.line(img, (pos, 0), (pos, height), (0, 255, 0), 1)
        pos += step
        i += 1
    # cv.imshow('Lines', img)
    # cv.waitKey(0)


def resize(img):
    width = int(img.shape[1] * 10)
    height = int(img.shape[0] * 10)
    dim = (width, height)
    print(img.shape)
    img = cv.resize(img, dim, interpolation = cv.INTER_LINEAR)
    print(img.shape)
    #cv.imshow('Bigger', img)
    # cv.waitKey(0)
    return img


def find_thresh(gray):
    width = gray.shape[1]
    height = gray.shape[0]
    width_part = round(width*0.095)
    height_part = round(height*0.11)
    arr = np.array(gray[height_part : height - height_part, width_part: width - width_part])
    mean = np.mean(arr)
    print('MEAN: ' + str(mean))
    return round(mean*0.75)


def put_label(top, left, frame, label):
    labelSize, baseLine = cv.getTextSize(label, cv.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    top = max(top, labelSize[1])
    cv.rectangle(frame, (left, top - round(1.5 * labelSize[1])), (left + round(1.5 * labelSize[0]), top + baseLine),
                 (0, 0, 255), cv.FILLED)
    # cv.rectangle(frame, (left, top - round(1.5*labelSize[1])), (left + round(1.5*labelSize[0]), top + baseLine),    (255, 255, 255), cv.FILLED)
    cv.putText(frame, label, (left, top), cv.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 2)

def process_symbs(symb_arr):
    labels = ''
    for i in symb_arr:
        symb = cv.resize(~i, (28, 28), interpolation=cv.INTER_LINEAR)
        symb_copy = np.copy(symb).reshape(28, 28, 1) / 255.0
        pred = recogn_model.predict(np.asarray([symb_copy]))
        if pred[0][np.argmax(pred)] >= char_conf_threshold:
            label = alphabets_dic[np.argmax(pred)]
            labels += label
            # cv.imshow(label, symb)
            # cv.waitKey(0)
            # cv.destroyAllWindows()
    print('plate: '+ labels)
    return labels

def find_chars(img):
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    # cv.imshow('2gray', gray)
    # cv.waitKey(0)
    # THRESHOLD
    # gray = cv.GaussianBlur(gray, (10, 10), 3)
    thresh = find_thresh(gray)

    gray = cv.threshold(gray, thresh, 255, cv.THRESH_BINARY)[1]
    # gray = cv.threshold(gray, 105, 255, cv.THRESH_BINARY)[1]
    # gray = cv.adaptiveThreshold(gray, 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY, 12, 6)
    # gray = cv.adaptiveThreshold(gray, 255, cv.ADAPTIVE_THRESH_MEAN_C, cv.THRESH_BINARY, 11, 2)
    #cv.imshow('thresh', gray)
    # cv.waitKey(0)
    # CANNY

    canny = cv.Canny(gray, 60, 100, 3)
    # cv.imshow('canny', canny)
    # cv.waitKey(0)
    width = canny.shape[1]
    height = canny.shape[0]
    area = width * height
    print('area: ' + str(area))
    Contours, Hierarchy = cv.findContours(canny, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    Contours = sorted(Contours, key=lambda ctr: cv.boundingRect(ctr)[0])
    symbs = []
    for contour in Contours:
        # --- select contours above a certain area ---
        # if cv.contourArea(contour) > area/30:
        # --- store the coordinates of the bounding boxes ---
        [X, Y, W, H] = cv.boundingRect(contour)
        rect_area = W * H
        if (H / W >= 3 and rect_area > area / 72) or (rect_area > area / 36 and rect_area < area / 4 and H / W > 0.75):
            src = gray[Y:(Y+H), X:(X+W)]
            # --- draw those bounding boxes in the actual image as well as the plain blank image ---
            symbs.append(
                cv.copyMakeBorder(
                    src = src,
                    top = 20, bottom = 20, left = 20, right = 20,
                    borderType = cv.BORDER_CONSTANT,
                    value=255
                )
            )
            cv.rectangle(img, (X, Y), (X + W, Y + H), (0, 0, 255), 2)
    cv.drawContours(img, Contours, -1, (0, 255, 0), 1)
    plate = process_symbs(symbs)
    cv.imshow(plate, img)
    cv.waitKey(0)
    cv.destroyAllWindows()


def get_lines(img):
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    canny = cv.Canny(gray, 180, 200, 3)
    lines = cv.HoughLinesP(canny, 1, 3.14/160, 30, 40)
    maxlen = 0
    maxline = 0
    for line in lines:
        line_len = get_line_length(line[0][0], line[0][1], line[0][2], line[0][3])
        if line_len > maxlen:
            maxlen = line_len
            maxline = line
    print('maxline length: ' + str(maxlen))
    print(maxline)
    # img = cv.line(img, (maxline[0][0], maxline[0][1]), (maxline[0][2], maxline[0][3]), (0, 255, 0), 1)
    angle = get_angle(maxline[0][0], maxline[0][1], maxline[0][2], maxline[0][3])
    print('angle : ' + str(angle))
    img_rotation = rotate_img(img, angle)
    # cv.imshow('Rotation', img_rotation)
    # cv.waitKey(0)
    cropped = cut(img_rotation)
    img = resize(cropped)
    find_chars(img)
    # separate(img, 1 / 15)
    return img
# for line in lines:
#     img = cv.line(img, (line[0][0], line[0][1]), (line[0][2], line[0][3]), (0, 255, 0), 1)

    # cv.imshow('line', img)
    # cv.waitKey(0)
    # cv.destroyAllWindows()

# Draw the predicted bounding box
def drawPred(classId, conf, left, top, right, bottom):
    # Draw a bounding box.
    plate = frame[top:bottom, left:right]
    cropped = get_lines(plate)
    # plate_gray = cv.cvtColor(plate, cv.COLOR_BGR2GRAY)
    # gray = cv.threshold(plate_gray, 0, 255,cv.THRESH_BINARY | cv.THRESH_OTSU)[1]
    cv.imwrite('./numbers/'+args.image[:-4]+str(datetime.now())+'.png', cropped)
    cv.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 1)

    label = '%.2f' % conf

    # Get the label for the class name and its confidence
    if classes:
        assert(classId < len(classes))
        label = '%s:%s' % (classes[classId], label)

    #Display the label at the top of the bounding box
    labelSize, baseLine = cv.getTextSize(label, cv.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    top = max(top, labelSize[1])
    cv.rectangle(frame, (left, top - round(1.5*labelSize[1])), (left + round(1.5*labelSize[0]), top + baseLine), (0, 0, 255), cv.FILLED)
    #cv.rectangle(frame, (left, top - round(1.5*labelSize[1])), (left + round(1.5*labelSize[0]), top + baseLine),    (255, 255, 255), cv.FILLED)
    cv.putText(frame, label, (left, top), cv.FONT_HERSHEY_SIMPLEX, 0.75, (0,0,0), 2)

# Remove the bounding boxes with low confidence using non-maxima suppression
def postprocess(frame, outs):
    frameHeight = frame.shape[0]
    frameWidth = frame.shape[1]
    cv.imshow('pic', frame)
    classIds = []
    confidences = []
    boxes = []
    # Scan through all the bounding boxes output from the network and keep only the
    # ones with high confidence scores. Assign the box's class label as the class with the highest score.
    classIds = []
    confidences = []
    boxes = []
    for out in outs:
        print("out.shape : ", out.shape)
        for detection in out:
            #if detection[4]>0.001:
            scores = detection[5:]
            classId = np.argmax(scores)
            #if scores[classId]>confThreshold:
            confidence = scores[classId]
            if detection[4]>confThreshold:
                print(detection[4], " - ", scores[classId], " - th : ", confThreshold)
                print(detection)
            if confidence > confThreshold:
                center_x = int(detection[0] * frameWidth)
                center_y = int(detection[1] * frameHeight)
                width = int(detection[2] * frameWidth)
                height = int(detection[3] * frameHeight)
                left = int(center_x - width / 2)
                top = int(center_y - height / 2)
                classIds.append(classId)
                confidences.append(float(confidence))
                boxes.append([left, top, width, height])

    # Perform non maximum suppression to eliminate redundant overlapping boxes with
    # lower confidences.
    indices = cv.dnn.NMSBoxes(boxes, confidences, confThreshold, nmsThreshold)
    for i in indices:
        i = i[0]
        box = boxes[i]
        left = box[0]
        top = box[1]
        width = box[2]
        height = box[3]
        drawPred(classIds[i], confidences[i], left, top, left + width, top + height)

# Process inputs
# winName = 'Deep learning object detection in OpenCV'
# cv.namedWindow(winName, cv.WINDOW_NORMAL)

outputFile = "yolo_out_py.avi"
if (args.image):
    # Open the image file
    if not os.path.isfile(args.image):
        print("Input image file ", args.image, " doesn't exist")
        sys.exit(1)
    cap = cv.VideoCapture(args.image)
    outputFile = args.image[:-4]+'_yolo_out_py.jpg'
elif (args.video):
    # Open the video file
    if not os.path.isfile(args.video):
        print("Input video file ", args.video, " doesn't exist")
        sys.exit(1)
    cap = cv.VideoCapture(args.video)
    outputFile = args.video[:-4]+'_yolo_out_py.avi'
else:
    # Webcam input
    cap = cv.VideoCapture(0)

# Get the video writer initialized to save the output video
if (not args.image):
    vid_writer = cv.VideoWriter(outputFile, cv.VideoWriter_fourcc('M','J','P','G'), 30, (round(cap.get(cv.CAP_PROP_FRAME_WIDTH)),round(cap.get(cv.CAP_PROP_FRAME_HEIGHT))))

while cv.waitKey(1) < 0:

    # get frame from the video
    hasFrame, frame = cap.read()

    # Stop the program if reached end of video
    if not hasFrame:
        print("Done processing !!!")
        print("Output file is stored as ", outputFile)
        cv.waitKey(3000)
        break

    # Create a 4D blob from a frame.
    blob = cv.dnn.blobFromImage(cv.resize(frame, (608, 608)), 1/255, (inpWidth, inpHeight), [0,0,0], 1, crop=False)

    # Sets the input to the network
    net.setInput(blob)

    # Runs the forward pass to get output of the output layers
    outs = net.forward(getOutputsNames(net))

    # Remove the bounding boxes with low confidence
    postprocess(frame, outs)

    # Put efficiency information. The function getPerfProfile returns the overall time for inference(t) and the timings for each of the layers(in layersTimes)
    t, _ = net.getPerfProfile()
    label = 'Inference time: %.2f ms' % (t * 1000.0 / cv.getTickFrequency())
    #cv.putText(frame, label, (0, 15), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255))

    # Write the frame with the detection boxes
    if (args.image):
        cv.imwrite('./output/'+outputFile, frame.astype(np.uint8));
    else:
        vid_writer.write(frame.astype(np.uint8))