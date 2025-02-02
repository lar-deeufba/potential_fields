#!/usr/bin/env python 
import sys
import os
import numpy as np
import cv2
import cv2.aruco as aruco
import glob
import rospy
from geometry_msgs.msg import Point, Pose, Quaternion, PoseStamped
from std_msgs.msg import Header
from tf.transformations import quaternion_from_euler

class ArucoInterface(object):

    def __init__(self):
        # Size of the ArUco marker in meters
        self.marker_size = 0.05
        rospy.init_node("aruco_pose_publisher", disable_signals=True)
        self.posePublisher = rospy.Publisher("marker_pose", PoseStamped, queue_size=10)

    def checkCamera(self):
        """ Checks if the camera is available """
        cameraFound = False
        print("[INFO]: Searching for camera...")
        try:
            for camera in glob.glob("/dev/video?"):
                if camera == "/dev/video2":
                    cameraIndex = 2
                    cameraFound = True
                    print("[INFO]: Using index 2 for the camera.")
                    return cameraIndex, cameraFound
                elif camera == "/dev/video1":
                    cameraIndex = 1
                    cameraFound = True
                    print("[INFO]: Using index 1 for the camera.")
                    return cameraIndex, cameraFound
                elif camera == "/dev/video0":
                    cameraIndex = 0
                    cameraFound = True
                    print("[INFO]: Using index 0 for the camera")
                    return cameraIndex, cameraFound
                else:
                    print("[ERROR]: No camera found.")
                    cameraFound = False
                    cameraIndex = 0
                    return cameraIndex, cameraFound
        except(TypeError):
            print("[ERROR]: Camera is probably not connected.")

    def extractCalibration(self):
        """ Gets the the camera and distortion matrix from the calibrate_camera method by reading the yaml file. """
        #TODO add function to check if the folder exists because opencv points to other error rather than saying it doesnt exist
        cv_file = cv2.FileStorage("calibration/calibration.yaml", cv2.FILE_STORAGE_READ)
        camera_matrix = cv_file.getNode("camera_matrix").mat()
        dist_matrix = cv_file.getNode("dist_coeff").mat()
        print("[INFO]: Extracted camera parameters.")
        cv_file.release()
        return camera_matrix, dist_matrix

    def concatenateIntoPose(self, tx, ty, tz, ori):
        """ Concatenates the translation and rotation vectors from the detection to a Pose message. """
        hdr = Header()
        # TODO: Check if it creates the frame or do we need to do it manually on the xacro
        # frameId = "aruco_marker" + id
        hdr.frame_id = "aruco_marker"
        hdr.stamp = rospy.Time.now()
        pos = Point()
        pos.x = tx
        pos.y = ty
        pos.z = tz
        orient = Quaternion(ori[0], ori[1], ori[2], ori[3])
        pose = Pose(pos, orient)
        ps = PoseStamped(hdr, pose)
        return ps

    def trackAruco(self):
        """ Tracks the ArUco Marker in real time. """
        marker_size = self.marker_size
        # Getting the parameters from the calibration
        camera_matrix, dist_matrix = self.extractCalibration()

        # Performs the checking from the video index for the USB camera
        cameraIndex, foundCamera = self.checkCamera()

        try:
            cap = cv2.VideoCapture(cameraIndex)
            while (True and foundCamera):
                # Getting a frame from video stream
                ret, frame = cap.read()
                if ret is True:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                else:
                    print("[ERROR]: Some error with the frames, restart your program.")
                    break
                
                # Using the 6x6 dictionary from ArUco
                aruco_dict = aruco.Dictionary_get(aruco.DICT_6X6_100)
                parameters = aruco.DetectorParameters_create()

                # Lists of ids and the corners belonging to each id
                corners, ids, rejectedImgPoints = aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

                font = cv2.FONT_HERSHEY_SIMPLEX


                #  Just enters this condition if any id is found on the camera frame
                if np.all(ids is not None):
                    # Retrieves the rotation and translation vector, i.e orientation and position from the camera wrt. marker
                    rvec, tvec, _ = aruco.estimatePoseSingleMarkers(corners[0], marker_size, camera_matrix, dist_matrix)

                    # Converts from RPY to Quaternion
                    quat = quaternion_from_euler(rvec[0][0][0],rvec[0][0][1],rvec[0][0][2])
                    poseStampedMsg = self.concatenateIntoPose(tvec[0][0][0], tvec[0][0][1], tvec[0][0][2], quat)
                    self.posePublisher.publish(poseStampedMsg)

                    # Drawing axis to represent the orientation of the marker and drawing a square around the identified marker
                    aruco.drawAxis(frame, camera_matrix, dist_matrix, rvec[0], tvec[0], 0.1)
                    aruco.drawDetectedMarkers(frame, corners)

                    # Draw ID on the screen
                    cv2.putText(frame, "Id: " + str(ids), (0,64), font, 1, (0,255,0),2,cv2.LINE_AA)

                cv2.imshow('ArucoDetection', frame)
                # If any key is pressed then it exits
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            cap.release()
            cv2.destroyAllWindows()

        except(KeyboardInterrupt):
            print("[ERROR]: Interrupt from keyboard, closing caption")
            cap.release()
            sys.exit(0)



ai = ArucoInterface()
ai.trackAruco()