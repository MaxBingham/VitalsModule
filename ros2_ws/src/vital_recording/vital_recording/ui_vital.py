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
from std_msgs.msg import Float32MultiArray

from .run_vscapture import VSCaptureManager

class VitalParamPlotter(Node):
    def __init__(self):
        super().__init__('vital_param_plotter')

        # ROS publisher
        self.pub_numeric = self.create_publisher(Float32MultiArray, 'vital_params_data', 10)
        self.pub_waveform = self.create_publisher(Float32MultiArray, 'pleth_waveform_data', 10)

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

        # Plot data
        self.start_time = time.time()
        self.ecg_t, self.ecg_v = [], []
        self.spo2_t, self.spo2_v = [], []
        self.pleth_t, self.pleth_v = [], []
        self.ecg1_t, self.ecg1_v = [], []
        self.resp_t, self.resp_v = [], []
        self.invp1_t, self.invp1_v = [], []

        self.latest_ecg, self.latest_spo2, self.latest_pleth, self.latest_ecg1, self.latest_resp, self.latest_inv = None, None, None, None, None, None

        # Sample counters for each waveform type
        self.pleth_sample_idx = 0
        self.ecg1_sample_idx = 0
        self.resp_sample_idx = 0
        self.invp1_sample_idx = 0

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

        self.get_logger().info("Initialized Vital Parameter Plotter")

    def _setup_gui(self):
        """Create simplified GUI with merged controls"""
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

        # Status label
        self.lbl_status = ttk.Label(self.root, text="Status: Ready", foreground="blue", font=("Arial", 12))
        self.lbl_status.pack(pady=5)

    def _setup_plot(self):
        """Setup 5 subplot layout"""
        self.fig, (self.ax1, self.ax2, self.ax3, self.ax4, self.ax5) = plt.subplots(5, 1, figsize=(12, 10))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)

    def _start_recording(self):
        """Start both VSCapture and data monitoring in one action"""
        try:
            # Step 1: Start VSCapture
            self.lbl_status.config(text="Status: Starting VSCapture...", foreground="orange")
            self.root.update()
            
            self.vscapture_manager.start()
            
            if not self.vscapture_manager.is_running:
                self.lbl_status.config(text="Status: Failed to start VSCapture", foreground="red")
                return
            
            # Step 2: Clear old data files
            self._clear_data_files()
            
            # Step 3: Reset monitoring state
            self.start_time = time.time()
            self._clear_plot_data()
            self.last_size = 0
            self.monitoring = True

            # Reset sample counters
            self.pleth_sample_idx = 0
            self.ecg1_sample_idx = 0
            self.resp_sample_idx = 0
            self.invp1_sample_idx = 0

            # Step 4: Start monitoring threads - FIXED: Use lambda to create proper thread targets
            threading.Thread(target=self._monitor_json, daemon=True).start()
            threading.Thread(target=self._monitor_pleth_wave, daemon=True).start()
            threading.Thread(target=self._monitor_ecg1_wave, daemon=True).start()
            threading.Thread(target=self._monitor_resp_wave, daemon=True).start()
            threading.Thread(target=self._monitor_invp1_wave, daemon=True).start()

            # Step 5: Update UI - FIXED: Make sure buttons are properly updated
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.lbl_status.config(text="Status: Recording & Monitoring Active", foreground="green")
            
            self.get_logger().info("Started VSCapture and monitoring successfully")
            
        except Exception as e:
            self.lbl_status.config(text=f"Status: Error - {str(e)}", foreground="red")
            self.get_logger().error(f"Error starting recording: {e}")
            # Reset button states on error
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

    def _stop_recording(self):
        """Stop both data monitoring and VSCapture in one action"""
        try:
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
            
        except Exception as e:
            self.lbl_status.config(text=f"Status: Error stopping - {str(e)}", foreground="red")
            self.get_logger().error(f"Error stopping recording: {e}")

    def _clear_data(self):
        """Clear all plotted data"""
        self._clear_plot_data()
        
        # Update display labels
        self.lbl_ecg.config(text="ECG HR: --")
        self.lbl_spo2.config(text="SpO2: --")

        self.get_logger().info("Cleared all plot data")

    def _clear_plot_data(self):
        """Clear plot data arrays"""
        self.ecg_t.clear()
        self.ecg_v.clear()
        self.spo2_t.clear()
        self.spo2_v.clear()
        self.pleth_t.clear()
        self.pleth_v.clear()
        self.ecg1_t.clear()
        self.ecg1_v.clear()
        self.resp_t.clear()
        self.resp_v.clear()
        self.invp1_t.clear()
        self.invp1_v.clear()
        self.latest_ecg, self.latest_spo2, self.latest_pleth, self.latest_ecg1, self.latest_resp, self.latest_inv = None, None, None, None, None, None

    def _clear_data_files(self):
        """Clear the JSON and CSV data files"""
        for path in (self.json_file, self.pleth_file, self.ecg1_file, self.resp_file, self.invp1_file):
            if os.path.exists(path):
                try:
                    open(path, 'w').close()  # Clear file
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
        ecg, spo2 = None, None

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

        if ecg is not None:
            self.ecg_t.append(t_now)
            self.ecg_v.append(ecg)
            self.latest_ecg = ecg
            # Keep only last 300 points
            if len(self.ecg_t) > 300:
                self.ecg_t = self.ecg_t[-300:]
                self.ecg_v = self.ecg_v[-300:]

        if spo2 is not None:
            self.spo2_t.append(t_now)
            self.spo2_v.append(spo2)
            self.latest_spo2 = spo2
            # Keep only last 300 points  
            if len(self.spo2_t) > 300:
                self.spo2_t = self.spo2_t[-300:]
                self.spo2_v = self.spo2_v[-300:]

        if ecg is not None or spo2 is not None:
            msg = Float32MultiArray()
            msg.data = [t_now, ecg or -1.0, spo2 or -1.0]
            self.pub_numeric.publish(msg)

    # ---------------------------------------------------------------------
    # Waveform monitors - FIXED: Separate methods for each waveform type
    # ---------------------------------------------------------------------
    def _monitor_pleth_wave(self):
        """Monitor Pleth waveform file"""
        last_pos = 0
        while self.monitoring:
            try:
                if os.path.exists(self.pleth_file):
                    with open(self.pleth_file, 'r') as f:
                        f.seek(last_pos)
                        lines = f.readlines()
                        last_pos = f.tell()

                    for line in lines:
                        if not self.monitoring:
                            break
                        parts = line.strip().split(',')
                        if len(parts) >= 2:
                            try:
                                val = float(parts[1])
                                t_rel = self.pleth_sample_idx * 0.01  # 100 Hz
                                self.pleth_sample_idx += 1

                                self.pleth_t.append(t_rel)
                                self.pleth_v.append(val)

                                # Keep only last 1500 points (15 seconds at 100Hz)
                                if len(self.pleth_t) > 1500:
                                    self.pleth_t = self.pleth_t[-1500:]
                                    self.pleth_v = self.pleth_v[-1500:]

                            except ValueError:
                                continue
                time.sleep(0.01)
            except Exception as e:
                if self.monitoring:
                    self.get_logger().error(f"Pleth waveform monitor error: {e}")
                time.sleep(0.1)

    def _monitor_ecg1_wave(self):
        """Monitor ECG1 waveform file"""
        last_pos = 0
        while self.monitoring:
            try:
                if os.path.exists(self.ecg1_file):
                    with open(self.ecg1_file, 'r') as f:
                        f.seek(last_pos)
                        lines = f.readlines()
                        last_pos = f.tell()

                    for line in lines:
                        if not self.monitoring:
                            break
                        parts = line.strip().split(',')
                        if len(parts) >= 2:
                            try:
                                val = float(parts[1])
                                t_rel = self.ecg1_sample_idx * 0.004  # 250 Hz
                                self.ecg1_sample_idx += 1

                                self.ecg1_t.append(t_rel)
                                self.ecg1_v.append(val)

                                # Keep only last 3750 points (15 seconds at 250Hz)
                                if len(self.ecg1_t) > 3750:
                                    self.ecg1_t = self.ecg1_t[-3750:]
                                    self.ecg1_v = self.ecg1_v[-3750:]

                            except ValueError:
                                continue
                time.sleep(0.004)
            except Exception as e:
                if self.monitoring:
                    self.get_logger().error(f"ECG1 waveform monitor error: {e}")
                time.sleep(0.1)

    def _monitor_resp_wave(self):
        """Monitor Respiration waveform file"""
        last_pos = 0
        while self.monitoring:
            try:
                if os.path.exists(self.resp_file):
                    with open(self.resp_file, 'r') as f:
                        f.seek(last_pos)
                        lines = f.readlines()
                        last_pos = f.tell()

                    for line in lines:
                        if not self.monitoring:
                            break
                        parts = line.strip().split(',')
                        if len(parts) >= 2:
                            try:
                                val = float(parts[1])
                                t_rel = self.resp_sample_idx * 0.04  # 25 Hz
                                self.resp_sample_idx += 1

                                self.resp_t.append(t_rel)
                                self.resp_v.append(val)

                                # Keep only last 375 points (15 seconds at 25Hz)
                                if len(self.resp_t) > 375:
                                    self.resp_t = self.resp_t[-375:]
                                    self.resp_v = self.resp_v[-375:]

                            except ValueError:
                                continue
                time.sleep(0.04)
            except Exception as e:
                if self.monitoring:
                    self.get_logger().error(f"Resp waveform monitor error: {e}")
                time.sleep(0.1)

    def _monitor_invp1_wave(self):
        """Monitor INVP1 waveform file"""
        last_pos = 0
        while self.monitoring:
            try:
                if os.path.exists(self.invp1_file):
                    with open(self.invp1_file, 'r') as f:
                        f.seek(last_pos)
                        lines = f.readlines()
                        last_pos = f.tell()

                    for line in lines:
                        if not self.monitoring:
                            break
                        parts = line.strip().split(',')
                        if len(parts) >= 2:
                            try:
                                val = float(parts[1])
                                t_rel = self.invp1_sample_idx * 0.008  # 125 Hz
                                self.invp1_sample_idx += 1

                                self.invp1_t.append(t_rel)
                                self.invp1_v.append(val)

                                # Keep only last 1875 points (15 seconds at 125Hz)
                                if len(self.invp1_t) > 1875:
                                    self.invp1_t = self.invp1_t[-1875:]
                                    self.invp1_v = self.invp1_v[-1875:]

                            except ValueError:
                                continue
                time.sleep(0.008)
            except Exception as e:
                if self.monitoring:
                    self.get_logger().error(f"INVP1 waveform monitor error: {e}")
                time.sleep(0.1)

    # ---------------- Plot Update ----------------
    def _update_plot(self):
        """Update all plots"""
        try:
            # Update labels
            if self.latest_ecg is not None:
                self.lbl_ecg.config(text=f"ECG HR: {self.latest_ecg:.0f} BPM")
            if self.latest_spo2 is not None:
                self.lbl_spo2.config(text=f"SpO2: {self.latest_spo2:.0f}%")

            # ECG HR (numeric plot)
            self.ax1.clear()
            self.ax1.set_title("ECG Heart Rate (BPM)")
            self.ax1.set_ylabel("Heart Rate")
            self.ax1.grid(True)
            if self.ecg_t and self.ecg_v:
                self.ax1.plot(self.ecg_t, self.ecg_v, 'r-', linewidth=2)
                self.ax1.set_ylim(max(30, min(self.ecg_v) - 10), min(200, max(self.ecg_v) + 10))

            # Pleth Waveform
            self.ax2.clear()
            self.ax2.set_title("Plethysmography Waveform")
            self.ax2.set_ylabel("Amplitude")
            self.ax2.grid(True)
            if self.pleth_t and self.pleth_v:
                self.ax2.plot(self.pleth_t, self.pleth_v, 'b-', linewidth=1)
                if len(self.pleth_t) > 1:
                    self.ax2.set_xlim(max(0, self.pleth_t[-1] - 15), self.pleth_t[-1])

            # ECG1 Waveform
            self.ax3.clear()
            self.ax3.set_title("ECG Waveform")
            self.ax3.set_ylabel("mV")
            self.ax3.grid(True)
            if self.ecg1_t and self.ecg1_v:
                self.ax3.plot(self.ecg1_t, self.ecg1_v, 'g-', linewidth=1)
                if len(self.ecg1_t) > 1:
                    self.ax3.set_xlim(max(0, self.ecg1_t[-1] - 15), self.ecg1_t[-1])

            # Respiration Waveform
            self.ax4.clear()
            self.ax4.set_title("Respiration Waveform")
            self.ax4.set_ylabel("Amplitude")
            self.ax4.grid(True)
            if self.resp_t and self.resp_v:
                self.ax4.plot(self.resp_t, self.resp_v, 'm-', linewidth=1)
                if len(self.resp_t) > 1:
                    self.ax4.set_xlim(max(0, self.resp_t[-1] - 15), self.resp_t[-1])

            # INVP1 Waveform
            self.ax5.clear()
            self.ax5.set_title("Invasive Pressure Waveform")
            self.ax5.set_xlabel("Time (s)")
            self.ax5.set_ylabel("mmHg")
            self.ax5.grid(True)
            if self.invp1_t and self.invp1_v:
                self.ax5.plot(self.invp1_t, self.invp1_v, 'c-', linewidth=1)
                if len(self.invp1_t) > 1:
                    self.ax5.set_xlim(max(0, self.invp1_t[-1] - 15), self.invp1_t[-1])

            self.fig.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            self.get_logger().error(f"Plot update error: {e}")

        # Continue updating if still running
        if hasattr(self, 'root'):
            self.root.after(200, self._update_plot)

    # ---------------- Exit ----------------
    def _on_exit(self):
        """Clean shutdown"""
        self.get_logger().info("Shutting down...")
        
        # Stop monitoring first
        self.monitoring = False
        
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