import os #to interact with operating system.Here to get the current directory of modes
import pickle #serialize and deserialize python objects.Here  open encodefile.py in binary read mode,then use load() to deseialize and load the data from file into varible
#presistenlt store data between programs,efficient storage,cross platform compatibility
import cv2 #importing opencv
import face_recognition #face recognition library
import cvzone #additional computer vision functionalities
import firebase_admin #firebase services
from firebase_admin import credentials # import credentials from firebase for authentication
from firebase_admin import db #import db module for working with firebase realtime database
from firebase_admin import storage # import storage module for interacting with firebase cloud storage
import numpy as np #numpy for numerical calculations
from datetime import datetime# for date and time

cred = credentials.Certificate("serviceAccountKey.json")#load the firebase service account credientials from .json file
firebase_admin.initialize_app(cred, {
    'databaseURL': "https://faceattendancerealtime-9b10f-default-rtdb.firebaseio.com/",
    'storageBucket': "faceattendancerealtime-9b10f.appspot.com"
}) # initialize firebase account with ur url
bucket = storage.bucket() #creating a reference to the firebase cloud storage bucket
#to capture the face
cap = cv2.VideoCapture(0)# open a video capture object with camera index 0
cap.set(3, 640)#width 640
cap.set(4, 480)#height 480

imgBackground = cv2.imread('Resources/background.png')# read and load the bg image. this is the background image for application

# Importing the mode images into a list
folderModePath = 'Resources/Modes'#different modes of application
modePathList = os.listdir(folderModePath)#list the files 
imgModeList = []#an empty list for storing mode images
for path in modePathList:
    imgModeList.append(cv2.imread(os.path.join(folderModePath, path)))#loop through the modes and append the loaded imagees to list
# print(len(imgModeList))

# Load the encoding file
print("Loading Encode File ...")
file = open('EncodeFile.p', 'rb')#open this file in binary read mode
encodeListKnownWithIds = pickle.load(file)#load with pickle
file.close()
encodeListKnown, studentIds = encodeListKnownWithIds# Seperate the data into 2 variables
#print(studentIds)
#print(encodeListKnown)
print("Encode File Loaded")

modeType = 0 
counter = 0
id = -1
imgStudent = []# store student image

while True:# STARTS INFINTITE LOOP,continously captures frames from camera and performs face recognition
    success, img = cap.read()#if successfully captured a image from camera using cap object.img will contain the captured frame

    imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)#resize the image by a factor of .25 to speed up face recog and store in imgs
    imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)#convert color space to from bgr to rgb for face recog operations

    faceCurFrame = face_recognition.face_locations(imgS)# find the face locations in curr frame and store in facecuframe,find the coordinations of rec box of detected faec
    encodeCurFrame = face_recognition.face_encodings(imgS, faceCurFrame)#encode the faces

    imgBackground[162:162 + 480, 55:55 + 640] = img #overlay the captured frame onto the bg image at specific coordinates
    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]#overlay each modes acc to modetype

    if faceCurFrame: #if any faces in current frame
        for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):#loop through encoded faec and locations
            matches = face_recognition.compare_faces(encodeListKnown, encodeFace)#compare the encoded face from the current frame with known face stored in enocde list known.if thereis a match
            faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)#calculate the distance between two images.distance means how simialr or dissimialr
            # print("matches", matches)
            # print("faceDis", faceDis)

            matchIndex = np.argmin(faceDis)#find index of known face with closest match in terms of face distance,return min value in an array or sequence
            # print("Match Index", matchIndex)

            if matches[matchIndex]:
                # print("Known Face Detected")
                # print(studentIds[matchIndex])
                y1, x2, y2, x1 = faceLoc #extract the coordinates of detected face top right bottom left
                y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4#highlight the face as we resized by 0.25
                bbox = 55 + x1, 162 + y1, x2 - x1, y2 - y1# calculates a bounding box ,x coordinate of top left corner,y coordinate of top left corner,width ,height
                imgBackground = cvzone.cornerRect(imgBackground, bbox, rt=0)#draw a rect around the detected face, image on which rect has to be drawn,coordinated and dimension of bbox,rotation of rect
                id = studentIds[matchIndex]#assign id to matched student id
                if counter == 0:
                    cvzone.putTextRect(imgBackground, "Loading", (275, 400))#shows loading 
                    cv2.imshow("Face Attendance", imgBackground)
                    cv2.waitKey(1)#waut and update counter and next mode
                    counter = 1
                    modeType = 1

        if counter != 0:#next mode when count is not zero

            if counter == 1:
                # Get the Data
                studentInfo = db.reference(f'Students/{id}').get()#from firebae db
                print(studentInfo)
                # Get the Image from the storage
                blob = bucket.get_blob(f'Images/{id}.jpg')

                if blob is not None:#image found in storage
                    array = np.frombuffer(blob.download_as_string(), np.uint8)# retrives image as bnart string.then to numpy of 8bit unsigned integers
                    imgStudent = cv2.imdecode(array, cv2.COLOR_BGRA2BGR)#decode and process the data
                    # Continue processing the image
                else:
                    print(f"Error: Blob with ID {id} not found or could not be fetched.")

                # Update data of attendance
                datetimeObject = datetime.strptime(studentInfo['last_attendance_time'],
                                                   "%Y-%m-%d %H:%M:%S")
                secondsElapsed = (datetime.now() - datetimeObject).total_seconds()#calculates no of seconds elapsed since the last recordd attendance
                print(secondsElapsed)
                if secondsElapsed > 30:#if greater thean 30 sec
                    ref = db.reference(f'Students/{id}')#retrived a refernce to data
                    studentInfo['total_attendance'] += 1#increment
                    ref.child('total_attendance').set(studentInfo['total_attendance'])#update
                    ref.child('last_attendance_time').set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))#update
                else:#if not
                    modeType = 3#last mode as already marked
                    counter = 0#ready to process 
                    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]#add the last mode

            if modeType != 3:
# display the details
                if 10 < counter < 20:
                    modeType = 2

                imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

                if counter <= 10:
                    cv2.putText(imgBackground, str(studentInfo['total_attendance']), (861, 125),cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 1)
                    cv2.putText(imgBackground, str(studentInfo['major']), (1006, 550),cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)
                    cv2.putText(imgBackground, str(id), (1006, 493),cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)
                    cv2.putText(imgBackground, str(studentInfo['standing']), (910, 625),cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                    cv2.putText(imgBackground, str(studentInfo['year']), (1025, 625),cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                    cv2.putText(imgBackground, str(studentInfo['starting_year']), (1125, 625),cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)

                    (w, h), _ = cv2.getTextSize(studentInfo['name'], cv2.FONT_HERSHEY_COMPLEX, 1, 1)
                    offset = (414 - w) // 2
                    cv2.putText(imgBackground, str(studentInfo['name']), (808 + offset, 445),cv2.FONT_HERSHEY_COMPLEX, 1, (50, 50, 50), 1)

                    imgBackground[175:175 + 216, 909:909 + 216] = imgStudent

                counter += 1
# empty everything
                if counter >= 20:
                    counter = 0
                    modeType = 0
                    studentInfo = []
                    imgStudent = []
                    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]
    else:# no face detected
        modeType = 0
        counter = 0
    # cv2.imshow("Webcam", img)
    cv2.imshow("Face Attendance", imgBackground)
    cv2.waitKey(1)