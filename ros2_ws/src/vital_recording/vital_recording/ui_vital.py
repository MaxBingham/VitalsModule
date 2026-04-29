#!/usr/bin/env python3
# filepath: /home/miti/Desktop/ros2-bag-recording/ros2_ws/src/vitalparam_recording/vitalparam_recording/ui_vital.py

import os
import json
import time
import threading
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
from .run_vscapture import VSCaptureManager
from .waveform_monitors import create_waveform_monitors

class VitalParamPlotter(Node):
    def __init__(self):
        super().__init__('vital_param_plotter')

        # ROS publisher
        #self.pub_numeric = self.create_publisher(Float32MultiArray, 'vital_numeric_data', 10)
        self.pub_ecg = self.create_publisher(Float32, 'numeric_ecg_hr', 10)
        self.pub_spo2 = self.create_publisher(Float32, 'numeric_spo2', 10)
        self.pub_nibp_sys = self.create_publisher(Float32, 'numeric_nibp_sys', 10)
        self.pub_nibp_dia = self.create_publisher(Float32, 'numeric_nibp_dia', 10)
        self.pub_nibp_mean = self.create_publisher(Float32, 'numeric_nibp_mean', 10)

        #self.pub_waveform = self.create_publisher(Float32MultiArray, 'vital_waveform_data', 10)
        self.pub_pleth = self.create_publisher(Float32, 'waveform_pleth', 10)
        self.pub_ecg1 = self.create_publisher(Float32, 'waveform_ecg1', 10)
        self.pub_resp = self.create_publisher(Float32, 'waveform_resp', 10)
        self.pub_invp1 = self.create_publisher(Float32, 'waveform_invp1', 10)

        # VSCapture manager
        self.vscapture_manager = VSCaptureManager()

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

        # GUI setup
        self.root = tk.Tk()
        self.root.title("Vital Parameters Monitor")
        self.root.geometry("1500x1200")
        self._setup_gui()
        self._setup_plot()
        self.root.protocol("WM_DELETE_WINDOW", self._on_exit)

        # Run ROS spin thread
        threading.Thread(target=rclpy.spin, args=(self,), daemon=True).start()
        self.root.after(200, self._update_plot)
        
        # Create timers to publish numeric and waveform data
        self.start_time = time.time()
        self.numeric_timer = self.create_timer(0.1, self._numeric_data_cb)
        self.waveform_timer = self.create_timer(0.01, self._wave_data_cb)

        self.get_logger().info("Initialized Vital Parameter Plotter")

#--------------------------------------------------------------
# setup GUI
# -------------------------------------------------------------    
    def _setup_gui(self):
        # Main control frame
        control_frame = ttk.LabelFrame(self.root, text="Vital Parameters Control", padding="10")
        control_frame.pack(pady=10, padx=10, fill="x")

        # Single start button (starts both VSCapture and monitoring)
        self.start_btn = ttk.Button(
            control_frame, text="Start Recording", 
            command=self._start_recording
        )
        self.start_btn.pack(side=tk.LEFT, padx=10)

        # Single stop button (stops both monitoring and VSCapture)
        self.stop_btn = ttk.Button(
            control_frame, text="Stop Recording", 
            command=self._stop_recording,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=10)

        # Clear data button
        self.clear_btn = ttk.Button(
            control_frame, text="Clear Data", 
            command=self._clear_data
        )
        self.clear_btn.pack(side=tk.LEFT, padx=10)

        # Exit button
        self.exit_btn = ttk.Button(
            control_frame, text="Exit", 
            command=self._on_exit
        )
        self.exit_btn.pack(side=tk.LEFT, padx=10)

        # Status display frame
        status_frame = ttk.Frame(self.root)
        status_frame.pack(pady=10)
        
        # Current values display
        values_frame = ttk.Frame(status_frame)
        values_frame.pack(side=tk.LEFT, padx=20)

        self.lbl_ecg = ttk.Label(values_frame, text="ECG HR: -- bpm", font=("Arial", 14, "bold"))
        self.lbl_ecg.pack(side=tk.LEFT, padx=15)

        self.lbl_spo2 = ttk.Label(values_frame, text="SpO2: -- %", font=("Arial", 14, "bold"))
        self.lbl_spo2.pack(side=tk.LEFT, padx=15)

        # NIBP display frame
        nibp_frame = ttk.Frame(values_frame)
        nibp_frame.pack(side=tk.LEFT, padx=20)
        
        # NIBP line 1: SYS (mmHg) DIA
        self.lbl_nibp_title = ttk.Label(nibp_frame, text="SYS (mmHg) DIA", font=("Arial", 12, "bold"))
        self.lbl_nibp_title.pack()
        
        # NIBP line 2: XXX / XXX
        self.lbl_nibp_values = ttk.Label(nibp_frame, text="-- / --", font=("Arial", 14, "bold"))
        self.lbl_nibp_values.pack()
        
        # NIBP line 3: Mean: XX
        self.lbl_nibp_mean = ttk.Label(nibp_frame, text="Mean: --", font=("Arial", 12, "bold"))
        self.lbl_nibp_mean.pack()

        # Status label
        self.lbl_status = ttk.Label(self.root, text="Status: Ready", foreground="blue", font=("Arial", 12))
        self.lbl_status.pack(pady=5)

    def _setup_plot(self):
        """Setup 4 subplot layout for waveforms only"""
        self.fig, (self.ax1, self.ax2, self.ax3, self.ax4) = plt.subplots(4, 1, figsize=(12, 10))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)


# ---------------- Recording Control (Button callbacks) ----------------
    def _start_recording(self):
        # Step 1: Start VSCapture
        self.lbl_status.config(text="Status: Starting VSCapture...", foreground="orange")
        self.root.update()
            
        self.vscapture_manager.start()
            
        if not self.vscapture_manager.is_running:
            self.lbl_status.config(text="Status: Failed to start VSCapture", foreground="red")
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

        # Step 5: Update UI
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.lbl_status.config(text="Status: Recording & Monitoring Active", foreground="green")

        self.get_logger().info("Started VSCapture and monitoring successfully")


    def _stop_recording(self):
        """Stop both data monitoring and VSCapture in one action"""
        # Step 1: Stop monitoring
        self.monitoring = False
            
        # Step 2: Stop VSCapture
        if self.vscapture_manager.is_running:
            self.vscapture_manager.stop()
            
        # Step 3: Update UI
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.lbl_status.config(text="Status: Recording Stopped", foreground="blue")
            
        self.get_logger().info("Stopped VSCapture and monitoring successfully")


    def _on_exit(self):
        """Clean shutdown"""
        self.get_logger().info("Shutting down...")
        
        # Stop monitoring first
        self.monitoring = False
        
        # Stop timers
        if hasattr(self, 'waveform_timer'):
            self.waveform_timer.cancel()
        if hasattr(self, 'numeric_timer'):
            self.numeric_timer.cancel()
        
        # Stop VSCapture if running
        if hasattr(self, 'vscapture_manager') and self.vscapture_manager.is_running:
            try:
                self.vscapture_manager.stop()
            except Exception as e:
                self.get_logger().error(f"Error stopping VSCapture: {e}")
        
        # Shutdown ROS
        try:
            self.destroy_node()
            rclpy.shutdown()
        except Exception as e:
            print(f"ROS shutdown warning: {e}")
        
        # Close GUI
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass


# ------------------ Clear Data helpers ----------------
    def _clear_data(self):
        """Clear all plotted data"""
        self._clear_plot_data()
        
        # Update display labels
        self.lbl_ecg.config(text="ECG HR: --")
        self.lbl_spo2.config(text="SpO2: --")
        self.lbl_nibp_values.config(text="-- / --")
        self.lbl_nibp_mean.config(text="Mean: --")

        self.get_logger().info("Cleared all plot data")

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

    def _wave_data_cb(self):
        try:
            monitor_publishers = [
                (self.pleth_monitor, self.pub_pleth),
                (self.ecg1_monitor, self.pub_ecg1),
                (self.resp_monitor, self.pub_resp),
                (self.invp1_monitor, self.pub_invp1),
            ]
            for monitor, publisher in monitor_publishers:
                while monitor.publish_queue:
                    value = monitor.publish_queue.popleft()
                    msg = Float32()
                    msg.data = value
                    publisher.publish(msg)
        except Exception as e:
            self.get_logger().error(f"Waveform callback error: {e}")


# ---------------- Plot Update ----------------
    def _update_plot(self):
        try:
            # Update latest waveform data from monitors
            self._update_latest_waveform_data()
            
            # Update labels
            if self.latest_numeric_data['ecg']['value'] is not None:
                self.lbl_ecg.config(text=f"ECG HR: {self.latest_numeric_data['ecg']['value']:.0f} BPM")
            if self.latest_numeric_data['spo2']['value'] is not None:
                self.lbl_spo2.config(text=f"SpO2: {self.latest_numeric_data['spo2']['value']:.0f}%")
            
            # Update NIBP display
            nibp_sys = self.latest_numeric_data['nibp_sys']['value']
            nibp_dia = self.latest_numeric_data['nibp_dia']['value']
            nibp_mean = self.latest_numeric_data['nibp_mean']['value']

            if nibp_sys is not None and nibp_dia is not None:
                self.lbl_nibp_values.config(text=f"{nibp_sys:.0f} / {nibp_dia:.0f}")
            elif nibp_sys is not None:
                self.lbl_nibp_values.config(text=f"{nibp_sys:.0f} / --")
            elif nibp_dia is not None:
                self.lbl_nibp_values.config(text=f"-- / {nibp_dia:.0f}")
            
            if nibp_mean is not None:
                self.lbl_nibp_mean.config(text=f"Mean: {nibp_mean:.0f}")

            # Waveform plots using monitor data (no ECG HR numeric plot)
            waveform_configs = [
                (self.ax1, self.pleth_monitor, "Plethysmography Waveform", "Amplitude", 'b-'),
                (self.ax2, self.ecg1_monitor, "ECG Waveform", "mV", 'g-'),
                (self.ax3, self.resp_monitor, "Respiration Waveform", "Amplitude", 'm-'),
                (self.ax4, self.invp1_monitor, "Invasive Pressure Waveform", "mmHg", 'c-')
            ]
            
            for ax, monitor, title, ylabel, color in waveform_configs:
                ax.clear()
                ax.set_title(title)
                ax.set_ylabel(ylabel)
                ax.grid(True)
                
                if monitor.time_buffer and monitor.value_buffer:
                    ax.plot(monitor.time_buffer, monitor.value_buffer, color, linewidth=1)
                    if len(monitor.time_buffer) > 1:
                        ax.set_xlim(max(0, monitor.time_buffer[-1] - 15), monitor.time_buffer[-1])
            
            # Add x-label to the last plot
            self.ax4.set_xlabel("Time (s)")

            self.fig.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            self.get_logger().error(f"Plot update error: {e}")

        # Continue updating if still running
        if hasattr(self, 'root'):
            self.root.after(200, self._update_plot)


def main(args=None):
    rclpy.init(args=args)
    node = VitalParamPlotter()
    try:
        node.root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        node.monitoring = False
        if hasattr(node, 'vscapture_manager') and node.vscapture_manager.is_running:
            node.vscapture_manager.stop()
        try:
            node.destroy_node()
            rclpy.shutdown()
        except:
            pass


if __name__ == "__main__":
    main()