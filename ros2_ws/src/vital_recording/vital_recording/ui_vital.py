#!/usr/bin/env python3
# filepath: /home/miti/Desktop/ros2-bag-recording/ros2_ws/src/vitalparam_recording/vitalparam_recording/ui_vital.py

import os
import json
import time
import threading
import subprocess
import signal

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, String
from .run_vscapture import VSCaptureManager
from .waveform_monitors import create_waveform_monitors

class VitalParamPlotter(Node):
    def __init__(self):
        super().__init__('vital_param_plotter')
        self._shutting_down = False

        # ROS publisher
        #self.pub_numeric = self.create_publisher(Float32MultiArray, 'vital_numeric_data', 10)
        self.pub_ecg = self.create_publisher(Float32, 'numeric_ecg_hr', 10)
        self.pub_spo2 = self.create_publisher(Float32, 'numeric_spo2', 10)
        self.pub_nibp_sys = self.create_publisher(Float32, 'numeric_nibp_sys', 10)
        self.pub_nibp_dia = self.create_publisher(Float32, 'numeric_nibp_dia', 10)
        self.pub_nibp_mean = self.create_publisher(Float32, 'numeric_nibp_mean', 10)
        self.pub_nibp_combined = self.create_publisher(String, 'numeric_nibp', 10)

        #self.pub_waveform = self.create_publisher(Float32MultiArray, 'vital_waveform_data', 10)
        self.pub_pleth = self.create_publisher(Float32, 'waveform_pleth', 10)
        self.pub_ecg1 = self.create_publisher(Float32, 'waveform_ecg1', 10)
        self.pub_resp = self.create_publisher(Float32, 'waveform_resp', 10)
        self.pub_invp1 = self.create_publisher(Float32, 'waveform_invp1', 10)

        # VSCapture manager
        self.vscapture_manager = VSCaptureManager()

        # Rosbag recording
        self.rosbag_process = None
        self.rosbag_topic_list = [
            '/camera/camera/color/image_raw',
            '/camera/camera/depth/image_rect_raw',
            '/camera/camera/color/camera_info',
            '/tf',
            '/tf_static',
            '/audio',
            '/gsr_data',
            # Vital topics actually published by this node:
            '/numeric_ecg_hr',
            '/numeric_spo2',
            '/numeric_nibp_sys',
            '/numeric_nibp_dia',
            '/numeric_nibp_mean',
            '/numeric_nibp',
            '/waveform_pleth',
            '/waveform_ecg1',
            '/waveform_resp',
            '/waveform_invp1',
        ]

        # File paths
        self.json_file = "/opt/vscapture/VSCaptureCLIv1.006Binary/DataExportVSC.json"
        self.pleth_file = "/opt/vscapture/VSCaptureCLIv1.006Binary/DRI_WF_PLETHWaveExport.csv"
        self.ecg1_file = "/opt/vscapture/VSCaptureCLIv1.006Binary/DRI_WF_ECGWaveExport.csv"
        self.resp_file = "/opt/vscapture/VSCaptureCLIv1.006Binary/DRI_WF_RESPWaveExport.csv"
        self.invp1_file = "/opt/vscapture/VSCaptureCLIv1.006Binary/DRI_WF_INVP1WaveExport.csv"
        
        self.last_size = 0
        self.monitoring = False
        
        # Waveform monitors (replacing individual buffer variables)
        file_paths = {
            'pleth': self.pleth_file,
            'ecg1': self.ecg1_file, 
            'resp': self.resp_file,
            'invp1': self.invp1_file
        }
        self.waveform_monitors = create_waveform_monitors(file_paths, self.get_logger())
        
        # Individual monitor references for convenience
        self.pleth_monitor = self.waveform_monitors[0]
        self.ecg1_monitor = self.waveform_monitors[1] 
        self.resp_monitor = self.waveform_monitors[2]
        self.invp1_monitor = self.waveform_monitors[3]

        # Latest numeric data indexed by parameter name
        self.latest_numeric_data = {
            'ecg': {'value': None},
            'spo2': {'value': None},
            'nibp_sys': {'value': None},
            'nibp_dia': {'value': None},
            'nibp_mean': {'value': None}
        }

        # Latest waveform data arrays indexed by parameter name
        self.latest_waveform_data = {
            'pleth': {'value': None, 'timestamp': None},
            'ecg1': {'value': None, 'timestamp': None},
            'resp': {'value': None, 'timestamp': None},
            'invp1': {'value': None, 'timestamp': None}
        }

        
        # Create timers to publish numeric and waveform data
        self.start_time = time.time()
        self.numeric_timer = self.create_timer(0.1, self._numeric_data_cb)
        # --- PER-MONITOR TIMERS (replaces single waveform_timer) ---
        self.waveform_timers = [
            self.create_timer(1.0 / 100.0,  lambda m=self.pleth_monitor,  p=self.pub_pleth:  self._publish_waveform(m, p)),
            self.create_timer(1.0 / 250.0,  lambda m=self.ecg1_monitor,   p=self.pub_ecg1:   self._publish_waveform(m, p)),
            self.create_timer(1.0 / 25.0,   lambda m=self.resp_monitor,   p=self.pub_resp:   self._publish_waveform(m, p)),
            self.create_timer(1.0 / 125.0,  lambda m=self.invp1_monitor,  p=self.pub_invp1:  self._publish_waveform(m, p)),
        ]
        # --- END PER-MONITOR TIMERS ---

        self.get_logger().info("Initialized Vital Parameter Plotter")

        # --- Auto-start ---

        self._auto_start()

# ---------------- Recording Control (Button callbacks) ----------------
    def _auto_start(self):
        # Step 1: Start VSCapture
            
        self.vscapture_manager.start()
            
        if not self.vscapture_manager.is_running:
            self.get_logger().error("Failed to start VSCapture")
            return

        # Step 2: Clear old data files
        self._clear_data_files()
        time.sleep(0.1)
            
        # Step 3: Reset monitoring state
        self.start_time = time.time()
        self._clear_plot_data()
        self.last_size = 0
        self.monitoring = True

        # Step 4: Start monitoring threads
        threading.Thread(target=self._monitor_json, daemon=True).start() # Start numeric monitoring thread
        for monitor in self.waveform_monitors: # Start waveform monitoring threads
            threading.Thread(
                target=monitor.monitor_file, 
                args=(lambda: self.monitoring,),  # Pass monitoring flag function
                daemon=True
            ).start()

        self.get_logger().info("VSCapture and monitoring started")

        self._start_rosbag()

    def _start_rosbag(self):
        current_time = time.localtime()
        time_for_path = time.strftime("%Y-%m-%d_%H_%M_%S", current_time)
        base_dir = "/export/rosbag"

        if not os.path.exists(base_dir):
            try:
                os.makedirs(base_dir, exist_ok=True)
                self.get_logger().info(f"Created directory: {base_dir}")
            except OSError as e:
                self.get_logger().error(f"Failed to create directory {base_dir}: {e}")
                return

        bag_path = os.path.join(base_dir, time_for_path)
        command = ["ros2", "bag", "record", "-o", bag_path]
        for topic in self.rosbag_topic_list:
            command.append(topic)
        self.rosbag_process = subprocess.Popen(command)
        self.get_logger().info(f"Started rosbag recording at {bag_path}")

    def _stop_rosbag(self):
        if self.rosbag_process and self.rosbag_process.poll() is None:
            self.rosbag_process.terminate()
            self.rosbag_process.wait()
            self.get_logger().info("Stopped rosbag recording.")
        self.rosbag_process = None

    def _shutdown(self):
        if self._shutting_down:
            return
        self._shutting_down = True

        self.get_logger().info("Shutting down...")
        self.monitoring = False
        for timer in getattr(self, 'waveform_timers', []):
            timer.cancel()
        if hasattr(self, 'numeric_timer'):
            self.numeric_timer.cancel()
        if hasattr(self, 'vscapture_manager') and self.vscapture_manager.is_running:
            try:
                self.vscapture_manager.stop()
            except Exception as e:
                self.get_logger().error(f"Error stopping VSCapture: {e}")
        self._stop_rosbag()


# ------------------ Clear Data helpers ----------------

    def _clear_plot_data(self):
        """Clear plot data arrays"""
        # Reset all waveform monitors
        for monitor in self.waveform_monitors:
            monitor.reset()
        
        for param in self.latest_numeric_data:
            self.latest_numeric_data[param]['value'] = None
        
        # Reset latest waveform data
        for param in ['pleth', 'ecg1', 'resp', 'invp1']:
            self.latest_waveform_data[param]['value'] = None
            self.latest_waveform_data[param]['timestamp'] = None
        
        # Reset file positions and sample counters
        self.last_size = 0  # JSON file size tracking

    def _clear_data_files(self):
        """Clear the JSON and CSV data files"""
        for path in (self.json_file, self.pleth_file, self.ecg1_file, self.resp_file, self.invp1_file):
            if os.path.exists(path):
                try:
                    with open(path, 'w') as f:
                        f.truncate(0)  # Explicitly truncate to size 0
                        f.flush()      # Force write to disk
                    os.fsync(os.open(path, os.O_RDONLY))  # Force filesystem sync
                    self.get_logger().info(f"Cleared data file: {path}")
                except Exception as e:
                    self.get_logger().error(f"Error clearing file {path}: {e}")



# ---------------------------------------------------------------------
# Numeric data monitor
# ---------------------------------------------------------------------
    def _monitor_json(self):
        """Continuously watch the JSON file for new lines"""
        while self.monitoring:
            try:
                if os.path.exists(self.json_file):
                    size = os.path.getsize(self.json_file)
                    if size > self.last_size:
                        with open(self.json_file, 'r') as f:
                            f.seek(self.last_size)
                            new_data = f.read()
                        self.last_size = size

                        for line in new_data.strip().splitlines():
                            if line.strip():
                                try:
                                    arr = json.loads(line)
                                    self._process_numeric_data(arr)
                                except json.JSONDecodeError:
                                    continue
                time.sleep(0.5)
            except Exception as e:
                if self.monitoring:  # Only log if we're still supposed to be monitoring
                    self.get_logger().error(f"Error reading JSON file: {e}")
                time.sleep(1)

    def _process_numeric_data(self, data):
        """Process numeric data from JSON"""
        t_now = time.time() - self.start_time
        ecg, spo2, nibp_sys, nibp_dia, nibp_mean = None, None, None, None, None

        for item in data:
            pid, val = item.get("PhysioID"), item.get("Value")
            if not val or val == "-":
                continue
            if pid == "ECG_HR":
                try: 
                    ecg = float(val)
                except ValueError: 
                    pass
            elif pid == "SpO2":
                try: 
                    spo2 = float(val)
                except ValueError: 
                    pass
            elif pid == "NIBP_Systolic":
                try:
                    nibp_sys = float(val)
                except ValueError:
                    pass
            elif pid == "NIBP_Diastolic":
                try:
                    nibp_dia = float(val)
                except ValueError:
                    pass
            elif pid == "NIBP_Mean":
                try:
                    nibp_mean = float(val)
                except ValueError:
                    pass

        if ecg is not None:
            self.latest_numeric_data['ecg']['value'] = ecg
        if spo2 is not None:
            self.latest_numeric_data['spo2']['value'] = spo2
        if nibp_sys is not None:
            self.latest_numeric_data['nibp_sys']['value'] = nibp_sys
        if nibp_dia is not None:
            self.latest_numeric_data['nibp_dia']['value'] = nibp_dia
        if nibp_mean is not None:
            self.latest_numeric_data['nibp_mean']['value'] = nibp_mean


    def _numeric_data_cb(self):
        """Publish latest numeric data without timestamps"""


        numeric_publishers = {
            'ecg': self.pub_ecg,
            'spo2': self.pub_spo2,
            'nibp_sys': self.pub_nibp_sys,
            'nibp_dia': self.pub_nibp_dia,
            'nibp_mean': self.pub_nibp_mean,
        }

        for key, publisher in numeric_publishers.items():
            msg = Float32()
            value = self.latest_numeric_data[key]['value']
            msg.data = value if value is not None else -1.0
            publisher.publish(msg)

        nibp_sys = self.latest_numeric_data['nibp_sys']['value']
        nibp_dia = self.latest_numeric_data['nibp_dia']['value']
        sys_str = f"{nibp_sys:.0f}" if nibp_sys is not None else "--"
        dia_str = f"{nibp_dia:.0f}" if nibp_dia is not None else "--"
        combined_msg = String()
        combined_msg.data = f"{sys_str}/{dia_str}"
        self.pub_nibp_combined.publish(combined_msg)

        # Each message carries one value - no array indexing to manage.
# ---------------------------------------------------------------------
# Waveform data update method
# ---------------------------------------------------------------------
    def _update_latest_waveform_data(self):
        """Update latest waveform data from monitors"""
        monitor_names = ['pleth', 'ecg1', 'resp', 'invp1']
        for i, monitor in enumerate(self.waveform_monitors):
            param_name = monitor_names[i]
            if monitor.latest_value is not None:
                self.latest_waveform_data[param_name]['value'] = monitor.latest_value
                self.latest_waveform_data[param_name]['timestamp'] = monitor.latest_timestamp

    # --- PER-MONITOR PUBLISH (replaces _wave_data_cb) ---
    def _publish_waveform(self, monitor, publisher):
        try:
            msg = Float32()
            msg.data = monitor.publish_queue.popleft() if monitor.publish_queue else -1.0
            publisher.publish(msg)
        except Exception as e:
            self.get_logger().error(f"Waveform publish error: {e}")
    # --- END PER-MONITOR PUBLISH ---


def main(args=None):
    rclpy.init(args=args)
    node = VitalParamPlotter()

    def signal_handler(sig, frame):
        node._shutdown()
        node.destroy_node()
        rclpy.shutdown()
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node._shutdown()
        try: 
            node.destroy_node()
            rclpy.shutdown()
        except Exception:
            pass
        


if __name__ == "__main__":
    main()