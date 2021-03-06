# NMlab Homework
### Contributors
- B08901159 周柏融
- B08901073 王維芯
### Requirement
- RTMP video streaming using Gstreamer & Nginx
    - Implement in `server.py`
- Implement control interface with gRPC protocol
    - Implement in `client.py`
- Provide different video processing algorithms
    - Object Detection (`server.py` line 104~115)
    - Hand Pose Tracking (`server.py` line 87~103)
    - Pose Estimation (`server.py` line 116~132)
- Record demo video with explaination
    - https://youtu.be/dpCrJ-UiC5U
 
### Install and compile gRPC-with-protobuf on Jetson nano
```bash
# Install protobuf compiler
$ sudo apt-get install protobuf-compiler
# Install buildtools
$ sudo apt-get install build-essential make
# Install packages
$ pip3 install -r requirements.txt
# Compile protobuf schema to python wrapper
$ make
```
## How to run

### On Jetson nano
- run gRPC server
- Default Port opened at 12345
```bash
$ python3 server.py
```
### On your device
- run ffplay and stream video through RTMP protocol
```bash
$ ffplay -fflags nobuffer rtmp://{Jetson IP}/rtmp/live
```
- send control signal thorugh gRPC 
```bash
$ python3 client --ip {Jetson IP} --port {Jetson port}--mode {mode}
```
### Different video processing algorithms

| Mode |  Video Processing  |
|:----:|:------------------:|
|  1   | Hand Pose Tracking |
|  2   |  Object Detection  |
|  3   |  Pose Estimation   |
