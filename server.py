import os
import os.path as osp
import sys
BUILD_DIR = osp.join(osp.dirname(osp.abspath(__file__)), "build/service/")
sys.path.insert(0, BUILD_DIR)
import argparse

import grpc
from concurrent import futures
import fib_pb2
import fib_pb2_grpc

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
    except KeyboardInterrupt:
        cap.release()


def gstreamer_rtmpstream(queue,mode):
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
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(pipeline, cv2.CAP_GSTREAMER, fourcc, 30.0, (1920, 1080))
    framecount = 0
    current_mode = 1
    Speedup = 5
    hand_result = []
    detection_result = []
    pose_result = None
    try:
        while True:    
            if queue.empty():continue
            frame = queue.get()
            if not mode.empty(): 
                current_mode = mode.get()
            if current_mode == 1:
                with mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5) as hands:
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
            elif current_mode == 2:
                with mp_object_detection.ObjectDetection(min_detection_confidence=0.1) as object_detection:
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
            elif current_mode == 3:
                with mp_pose.Pose(model_complexity=0, enable_segmentation=True,min_detection_confidence=0.5) as pose:
                    if framecount % Speedup == 0:
                        results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                        if results.pose_landmarks:
                            pose_result = results.pose_landmarks
                        else:
                            pose_result = None
                    # print(len(pose_result))
                    if pose_result:
                        mp_drawing.draw_landmarks(
                            frame,
                            pose_result,
                            mp_pose.POSE_CONNECTIONS,
                            landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style())
                    out.write(frame)
                    framecount += 1
    except KeyboardInterrupt:
        out.release()

class FibCalculatorServicer(fib_pb2_grpc.FibCalculatorServicer):

    def __init__(self, mode):
        self.q_mode = mode
        pass

    def Compute(self, request, context):
        mode = request.mode
        self.q_mode.put(mode)
        response = fib_pb2.FibResponse()
        response.value = mode
        print("received ", mode)

        return response

def gRPC_server(mode):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    servicer = FibCalculatorServicer(mode)
    fib_pb2_grpc.add_FibCalculatorServicer_to_server(servicer, server)
    # print(grpc.ChannelConnectivity(0))
    try:
        server.add_insecure_port(f"0.0.0.0:12345")
        server.start()
        print(f"Run gRPC Server at 0.0.0.0:12345")
        print(f"servicer.mode: ", servicer.q_mode)
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(0)
        # server.shutdown()
        # server.awaitTermination()

if __name__ == "__main__":
    queue = mp.Queue(maxsize=5)
    mode = mp.Queue(maxsize=1)
    camera = mp.Process(target=gstreamer_camera, args=(queue,))
    get_mode = mp.Process(target=gRPC_server, args=(mode,))
    stream = mp.Process(target=gstreamer_rtmpstream, args=(queue,mode,))
    try:    
        camera.start()
        get_mode.start()
        stream.start()
    except:
        camera.terminate()
        camera.join()
        get_mode.terminate()
        get_mode.join()
        stream.terminate()
        stream.join()
       




