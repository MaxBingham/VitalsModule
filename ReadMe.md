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

2. **Run everything with one command:**
Navigate to the `docker` directory and run the start script:
```bash
cd docker
chmod +x run.sh
./run.sh
```
This single command does everything:
- builds the image and starts **both** containers (`vital-param-recorder` and `foxglove-bridge`),
- the recorder container **auto-starts `ui_vital`**, which in turn starts VSCapture, live monitoring, and rosbag recording (no manual node launch needed),
- waits for the Foxglove bridge, then **opens Foxglove Studio auto-connected** to `ws://localhost:8765`,
- streams the container logs to the terminal.

Press `Ctrl-C` to detach from the logs — the containers keep running. To stop the whole system:
```bash
docker compose -f docker-compose.yml down
```

> **First run on the Pi 5:** the initial build (rosdep + colcon) takes several minutes and is mostly silent — this is expected, not a hang.

### Manual / debugging

If you need a shell instead of the auto-started node, start with autostart disabled and attach:
```bash
AUTOSTART=0 docker compose -f docker-compose.yml up --build -d
docker exec -it vital-param-recorder bash
```
Inside the container you have the full ROS 2 Humble environment (`root@USER:/ros2_ws#`) and can run nodes by hand, e.g. `ros2 run vital_recording ui_vital`. `docker exec ... bash` works even while the node is auto-running.

## 3. Launching Sensor Nodes

You can get an overview of the nodes and topics in the workspace `ros2_ws` from this rosgraph:
![Rosgraph of the whole system](docs/rosgraph_vital.png)

### Running the entire System
`./run.sh` (section 2) already launches the full system automatically. The commands below are only needed if you are running things by hand (see **Manual / debugging** above).

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


## 4. Foxglove Bridge — Live Visualisation

The Foxglove Bridge streams all ROS 2 topics to [Foxglove Studio](https://foxglove.dev) over WebSocket, allowing live visualisation without entering the container.

Each signal is published on its own named topic (e.g. `/numeric_ecg_hr`, `/waveform_pleth`) as a `Float32` message. This makes Foxglove panel subscription straightforward — subscribe to the topic you want by name, no array indexing required.

### 4.1 Starting the bridge

```bash
cd ~/Documents/vitals-module/docker
sudo docker compose up -d foxglove-bridge
```

### 4.2 Connecting Foxglove Studio

`./run.sh` opens Foxglove Studio for you, auto-connected to `ws://localhost:8765` (desktop app via `foxglove://` deep-link if installed, otherwise the hosted web app in your browser). No manual connection step is needed.

If you ever need to connect by hand:
1. Open Foxglove Studio
2. Click **Open connection**
3. Select **Foxglove WebSocket**
4. Enter URL: `ws://localhost:8765`

> **Layout:** the auto-connect does not load a layout. Import `Vital_Monitor.json` (repo root) once via **Layouts → Import** to get the pre-built vital-monitor dashboard.

> **Note:** Topics appear once `ui_vital` is running (which `./run.sh` starts automatically). Since the node auto-starts recording on launch, no button press is required.

### 4.3 Available topics

**Numeric Vitals (10 Hz):**

| Topic | Type | Description |
|---|---|---|
| `/numeric_ecg_hr` | `Float32` | ECG heart rate in bpm |
| `/numeric_spo2` | `Float32` | Oxygen saturation in % |
| `/numeric_nibp_sys` | `Float32` | Systolic blood pressure in mmHg |
| `/numeric_nibp_dia` | `Float32` | Diastolic blood pressure in mmHg |
| `/numeric_nibp_mean` | `Float32` | Mean blood pressure in mmHg |

**Waveforms (100-250 Hz depending on sensor):**

| Topic | Type | Description |
|---|---|---|
| `/waveform_pleth` | `Float32` | Plethysmography waveform sample |
| `/waveform_ecg1` | `Float32` | ECG waveform sample (mV) |
| `/waveform_resp` | `Float32` | Respiration waveform sample |
| `/waveform_invp1` | `Float32` | Invasive pressure waveform sample (mmHg) |

> **Note:** All topics publish individual `Float32` messages. A value of `-1.0` indicates no data is available for that signal.

### 4.4 Viewing data in Foxglove Studio

**Numeric Vitals (scalars):**
- Add a **Gauge** or **State** panel → subscribe to any `/numeric_*` topic

**Waveforms (time-series with lines):**
- Add a **Plot** panel → subscribe to any `/waveform_*` topic
- Enable "Show lines" in the panel settings for sparse low-frequency data to appear connected
- Example: `/waveform_pleth` for plethysmography, `/waveform_ecg1` for ECG waveform

**All topics with raw values:**
- Add a **Raw Messages** panel → subscribe to any topic to see the latest Float32 value

> **Tip:** Each topic name is self-documenting — you always know exactly which signal you're looking at.

### 4.5 Troubleshooting

**Check bridge is healthy:**
```bash
sudo docker inspect foxglove_bridge --format='{{.State.Health.Status}}'
```

**Check topics are publishing:**
```bash
sudo docker exec vital-param-recorder bash -c "source /opt/ros/humble/setup.bash && ROS_DOMAIN_ID=42 ros2 topic list"
```

**Watch bridge logs live:**
```bash
sudo docker logs foxglove_bridge -f
```

**No data in Foxglove despite topics being visible:**
Both containers must have `ipc: host` set in `docker-compose.yml`. Without it, FastDDS shared memory is blocked between containers and no messages are delivered even though topics are discoverable.

### 4.6 Smooth Continuous Plots with User Scripts

Waveform topics publish every sample at the sensor's natural rate (100–250 Hz), so they render as continuous curves in Foxglove without any extra processing. Numeric vitals are sparse (10 Hz) and will show visible jumps between updates.

To smooth either signal type in Foxglove, use a **User Script** for linear interpolation between samples.

**Setup in Foxglove Studio:**

1. Click **User Scripts** in the left sidebar
2. Click **"+"** to add a new script
3. Name it: `waveform_interpolator`
4. Paste the script below
5. Add **Plot** panels and subscribe to the output topics:
   - `/foxglove/waveform_pleth_smooth`
   - `/foxglove/waveform_ecg1_smooth`
   - `/foxglove/waveform_resp_smooth`
   - `/foxglove/waveform_invp1_smooth`

**Foxglove User Script (TypeScript):**

```typescript
import { Message } from "@foxglove/studio";

interface WaveformState {
  lastValue: number | null;
  lastTimestamp: number | null;
  secondLastValue: number | null;
  secondLastTimestamp: number | null;
}

// Maintain state for each waveform
const waveforms: Record<string, WaveformState> = {
  pleth: { lastValue: null, lastTimestamp: null, secondLastValue: null, secondLastTimestamp: null },
  ecg1: { lastValue: null, lastTimestamp: null, secondLastValue: null, secondLastTimestamp: null },
  resp: { lastValue: null, lastTimestamp: null, secondLastValue: null, secondLastTimestamp: null },
  invp1: { lastValue: null, lastTimestamp: null, secondLastValue: null, secondLastTimestamp: null },
};

const topics = [
  { input: "/waveform_pleth", key: "pleth", output: "waveform_pleth_smooth" },
  { input: "/waveform_ecg1", key: "ecg1", output: "waveform_ecg1_smooth" },
  { input: "/waveform_resp", key: "resp", output: "waveform_resp_smooth" },
  { input: "/waveform_invp1", key: "invp1", output: "waveform_invp1_smooth" },
];

export const inputs = topics.map((t) => t.input);
export const output = "visualization";

export function activate(ctx: any) {
  // Watch each waveform topic
  topics.forEach(({ input, key, output }) => {
    ctx.watch(input, (msg: any) => {
      const value = msg.message.data;
      const timestamp = msg.receiveTime.sec + msg.receiveTime.nsec / 1e9;

      // Skip invalid data
      if (value === -1.0 || isNaN(value)) {
        return;
      }

      const state = waveforms[key];

      // Shift: move current to "previous"
      state.secondLastValue = state.lastValue;
      state.secondLastTimestamp = state.lastTimestamp;
      state.lastValue = value;
      state.lastTimestamp = timestamp;

      // Only interpolate if we have two samples
      if (state.secondLastValue !== null && state.secondLastTimestamp !== null) {
        const timeDiff = state.lastTimestamp - state.secondLastTimestamp;
        const valueDiff = state.lastValue - state.secondLastValue;

        // Generate points at 100 Hz between the two samples
        const interpolationRate = 100;
        const numPoints = Math.max(1, Math.ceil(timeDiff * interpolationRate));

        for (let i = 0; i <= numPoints; i++) {
          // t goes from 0 to 1 as we move from old sample to new sample
          const t = i / numPoints;

          // Linear interpolation
          const interpolatedTime = state.secondLastTimestamp + t * timeDiff;
          const interpolatedValue = state.secondLastValue + t * valueDiff;

          // Publish the fake point
          ctx.publish(output, {
            timestamp: interpolatedTime,
            value: interpolatedValue,
          });
        }
      }
    });
  });
}
```

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
