# Docker for ros2 bag recording with vital parameter monitor

## 1. Requirements
- GE medical Monitor Bx50 or Datex S/5 or Dash (tested with GE b450)
- 2 ATEN UC232A-USB adapters connected with Null Modem F/F cable. 
- VitalSignsCapture (appended in this repository)
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

You can get an overview of the nodes and topics in the workspace `ros2_ws` from this rosgraph:
![Rosgraph of the whole system](docs/rosgraph_vital.png)

### Running the entire System
Run the home console to get access to the vital recording and rosbag recording.
```shell
ros2 run user_interface ui_home
```
![The GUI home window](docs/ui_window_all.png)

### Recording vital signals from Monitor GE Carescape b450
This package uses VSCapture to record data from medical monitor. To connect to the medical monitor, read the hardware connection guide by [vital recorder](https://vitaldb.net/docs/). To get an overview of the available sensors for vital signals on GE Bx50. Read this [catalog](https://www.gehealthcare.de/-/media/global/dach/files/lcs/mini-catalogues-lcs_b450_b650_b850_de_jb63920xeb.pdf?rev=-1). If you just want to run VSCapture with your own configuration arguments, run:
```shell
run_vscapture.sh \
  --devices 1 \
  --device1type 1 \
  --device1model 2 \
  --device1arg "-port /dev/ttyUSB0 -interval 1 -export 4 -waveset 2"
```

When VSCapture running, it will save all vital signal in .json and .csv files. There are 2 kinds of vital signal. If a vital parameter is shown as label in monitor, it will be recognized as numeric data and all numeric data are saved in one file. If a vital parameter can be plotted as live diagram in monitor, it is recognized as waveform and each waveform data is saved in its own .csv file. Then the ros2 node `/vital_param_plotter`will read latest data from these files and plot them in GUI. So it is more recommended to run VSCapture in GUI. Also you can see the plotting of the vital parameters in realtime:
```shell
ros2 run vital_recording ui_vital
```
![The GUI window for vital signal from medical monitor.](docs/ui_window_vital.png)


## 4. Export files from the container to outside

### 4.1 Exported data
You can check all exported data from sensors at `/export`. Check rosbag data for all topics at `/export/rosbag`.

### 4.2 Manuelly export dats
Run the command outside the container to export files generated inside the container.
```shell
docker cp <container_name>:/path/in/container /path/on/host
```
For example, if you have exported a rosgraph using rqt_graph, you can save it to the specific folder `/ros2_ws/outputs` and export it to the Desktop. 
```shell
docker cp vital-param-recorder:/export/rosgraph.png ~/Desktop/
```
