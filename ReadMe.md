# Docker for ros2 bag recording with vital parameter monitor

## 1. Requirements
- Docker
- Docker Compose

## 2. Get started

1. **Clone the repository:**
```bash
git clone https://gitlab.lrz.de/centre-of-clinical-robotics/templates/vital-parameter-recording
cd vital-paramter-recording
```

2. **Run the container:**
Navigate to the `docker` directory and run the start script:
```bash
cd docker
chmod +x run.sh
./run.sh
```
This will build the Docker image and start the container. The GUI for the GSR recorder should appear.
Keep this terminal and open a new one to enter the container:
```shell
docker exec -it vital-param-recorder bash
```
Then you have entered the container environment with root path:`root@USER:/ros2_ws# ` You can now get access to all about ROS2 Humble now.

## 3. Launching Sensor Nodes

### Running the entire System
Run the home console to get access to the vital recording and rosbag recording.
```shell
ros2 run user_interface ui_home
```
![The GUI home window](docs/ui_window_new.png)

### Recording vital signals from Monitor GE Carescape b450
VSCapture is added in this respository. If you just want to run VSCapture with your own configuration arguments, run:
```shell
run_vscapture.sh \
  --devices 1 \
  --device1type 1 \
  --device1model 2 \
  --device1arg "-port /dev/ttyUSB0 -interval 1 -export 4 -waveset 2"
```

But it is more recommended to run VSCapture in GUI. Also you can see the plotting of the vital parameters in realtime:
```shell
ros2 run vital_recording ui_vital
```
![The GUI window for vital signal from medical monitor.](docs/ui_window_vital.png)


## 4. Export files from the container to outside

### 4.1 Exported data
You can check all exported data from sensors at `/export`. Check rosbag data for all topics at `/export/rosbag`. Check GSR data with tiemstamps in table at `/export/gar_csv`.

### 4.2 Manuelly export dats
Run the command outside the container to export files generated inside the container.
```shell
docker cp <container_name>:/path/in/container /path/on/host
```
For example, if you have exported a rosgraph using rqt_graph, you can save it to the specific folder `/ros2_ws/outputs` and export it to the Desktop. 
```shell
docker cp gsr-recorder:/export/rosgraph.png ~/Desktop/
```
