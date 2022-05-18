import cv2
import argparse
import multiprocessing as mp
import mediapipe as pipe
# Hand Tracking
mp_hands = pipe.solutions.hands
mp_drawing_styles = pipe.solutions.drawing_styles
mp_drawing = pipe.solutions.drawing_utils
# Object Detection
mp_object_detection = pipe.solutions.object_detection
mp_drawing = pipe.solutions.drawing_utils
# Pose Estimation
mp_drawing = pipe.solutions.drawing_utils
mp_drawing_styles = pipe.solutions.drawing_styles
mp_pose = pipe.solutions.pose

case = 1
Speedup = 5

queue = mp.Queue(maxsize=2)
def gstreamer_camera(queue):
    # Use the provided pipeline to construct the video capture in opencv
    pipeline = (
        "nvarguscamerasrc ! "
            "video/x-raw(memory:NVMM), "
            "width=(int)1920, height=(int)1080, "
            "format=(string)NV12, framerate=(fraction)30/1 ! "
        "queue ! "
        "nvvidconv ! "
            "video/x-raw, "
            "width=(int)1920, height=(int)1080, "
            "format=(string)BGRx, framerate=(fraction)30/1 ! "
        "videoconvert ! "
            "video/x-raw, format=(string)BGR ! "
        "appsink"
    )
    # Complete the function body
    cap = cv2.VideoCapture(pipeline)
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            # print(time.strftime('%X'), frame.shape)
            queue.put(frame)
    except KeyboardInterrupt as e:
        cap.release()


def gstreamer_rtmpstream(queue):
    # Use the provided pipeline to construct the video writer in opencv
    pipeline = (
        "appsrc ! "
            "video/x-raw, format=(string)BGR ! "
        "queue ! "
        "videoconvert ! "
            "video/x-raw, format=RGBA ! "
        "nvvidconv ! "
        "nvv4l2h264enc bitrate=8000000 ! "
        "h264parse ! "
        "flvmux ! "
        'rtmpsink location="rtmp://localhost/rtmp/live live=1"'
    )
    # Complete the function body
    p = mp.Process(target=gstreamer_camera, args=(queue,))
    p.start()
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(pipeline, cv2.CAP_GSTREAMER, fourcc, 30.0, (1920, 1080))
    framecount = 0
    try:
        if case == 1:
            with mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5) as hands:
                while True:
                    if queue.empty():continue
                    frame = queue.get()
                    if framecount % Speedup == 0:
                        results = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                        if results.multi_hand_landmarks:
                            hand_result = results.multi_hand_landmarks
                        else:
                            hand_result =[]
                    for hand_landmarks in hand_result:
                        mp_drawing.draw_landmarks(
                            frame,
                            hand_landmarks,
                            mp_hands.HAND_CONNECTIONS,
                            mp_drawing_styles.get_default_hand_landmarks_style(),
                            mp_drawing_styles.get_default_hand_connections_style())
                    out.write(frame)
                    framecount += 1
        elif case == 2:
            with mp_object_detection.ObjectDetection(min_detection_confidence=0.1) as object_detection:
                while True:
                    if queue.empty():continue
                    frame = queue.get()
                    if framecount % Speedup == 0:
                        results = object_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                        if results.detections:
                            detection_result = results.detections
                        else:
                            detection_result =[]
                    for detection in detection_result:
                        mp_drawing.draw_detection(frame, detection)
                    out.write(frame)
                    framecount += 1
        elif case == 3:
            with mp_pose.Pose(model_complexity=0, enable_segmentation=True,min_detection_confidence=0.5) as pose:
                while True:
                    if queue.empty():continue
                    frame = queue.get()
                    if framecount % Speedup == 0:
                        results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                        if results.pose_landmarks:
                            pose_result = results.pose_landmarks
                        else:
                            pose_result = []
                    # print(len(pose_result))
                    if pose_result:
                        mp_drawing.draw_landmarks(
                            frame,
                            pose_result,
                            mp_pose.POSE_CONNECTIONS,
                            landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style())
                    out.write(frame)
                    framecount += 1
        p.terminate()
        p.join()
    except:
        p.terminate()
        p.join()
    # You can apply some simple computer vision algorithm here



# Complelte the code
gstreamer_rtmpstream(queue)

#https://forums.raspberrypi.com/viewtopic.php?t=244975

#check if camera is working:
#sudo systemctl restart nvargus-daemon.service
