# Vital Parameter Recording

## Start

First Step - Clone

```bash
git clone https://gitlab.lrz.de/centre-of-clinical-robotics/templates/vital-parameter-recording
cd vital-paramter-recording

```

The quickest way to start the system is to run the launcher script from the `docker` folder:

```bash
cd docker
./run.sh
```

The script starts the containers, launches the recording workflow, and opens Foxglove when it is ready.

Note: First startup can take around 15-20 min. The next one (cached docker images) should be significantly quicker. 

## Requirements

- Docker
- Docker Compose
- The monitor and serial hardware used by the recording setup

## Foxglove Setup
```
Foxglove Studio will open automatically - Once your inside the web application follow these steps. 

**Result:** Plots will render with interpolated points between real samples, eliminating visible jumps on low-rate signals.

---

## 5. Starting the vital recorder

`./run.sh` (section 2) starts `ui_vital` automatically inside the container with `ROS_DOMAIN_ID=42` already set (via `docker-compose.yml`), so it is visible to the Foxglove bridge (domain 42). No manual start is needed.

If you disabled autostart (`AUTOSTART=0`) and want to start the node by hand, keep the domain explicit:

```bash
sudo docker exec -it vital-param-recorder bash -c "export ROS_DOMAIN_ID=42 && ros2 run vital_recording ui_vital"
```

---

## 6. Export files from the container to outside

### 6.1 Exported data
You can check all exported data from sensors at `/export`. Check rosbag data for all topics at `/export/rosbag`.

### 6.2 Manually export data
Run the command outside the container to export files generated inside the container.
```shell
docker cp <container_name>:/path/in/container /path/on/host
```
For example, if you have exported a rosgraph using rqt_graph, you can save it to the specific folder `/ros2_ws/outputs` and export it to the Desktop. 
```shell
docker cp vital-param-recorder:/export/rosgraph.png ~/Desktop/
```
