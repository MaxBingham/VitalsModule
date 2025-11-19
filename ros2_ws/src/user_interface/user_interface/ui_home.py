# dummy node
import rclpy
from rclpy.node import Node 
from std_msgs.msg import String
from typing import List, Optional
import threading
import tkinter as tk
from tkinter import ttk
import os
import subprocess
import signal
from .rosbag_recorder import RosbagRecorder


class HomeConsole(Node):
    def __init__(self) -> None:
        super().__init__('home_console')
        self.get_logger().info("Home Console Node started.")
        

        # Subprocess to launch other ui nodes
        self.ui_vital_process: Optional[subprocess.Popen] = None
        self.rosbag_recorder = RosbagRecorder()
        self.recording = False

        # Create GUI
        self.root = tk.Tk()
        self.root.title("Home Console")
        self.root.geometry("400x300")

        self._create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self._on_exit)

        self.ui_vital_process = None

        self.create_timer(0.1, self.update_subprocess_status)

        # Start ROS spinning in a separate thread
        self.ros_thread = threading.Thread(target=self._spin_ros, daemon=True)
        self.ros_thread.start()

    def _spin_ros(self):
        """Spin ROS in a separate thread"""
        try:
            rclpy.spin(self)
        except Exception as e:
            self.get_logger().error(f"Error in ROS spin: {e}")   

    def _create_widgets(self):
        """Create the main GUI widgets."""
        self.label = ttk.Label(self.root, text="Home Console of ROS2 Bag Recording by Miti(TUM)")
        self.label.pack(pady=20)

        self.launch_vital_button = ttk.Button(self.root, text="Open Vital Console", command=self._on_launch_vital_ui)
        self.launch_vital_button.pack(pady=10)

        self.record_button = ttk.Button(self.root, text="Start Rosbag Recording", command=self._toggle_rosbag_recording)
        self.record_button.pack(pady=10)

        self.status_label = ttk.Label(self.root, text="Status: Ready", foreground="blue")
        self.status_label.pack(pady=10)

        self.quit_button = ttk.Button(self.root, text="Quit", command=self._on_exit)
        self.quit_button.pack(pady=10)

    def _toggle_rosbag_recording(self):
        if not self.recording:
            self.rosbag_recorder.start_recording()
            self.record_button.config(text="Stop Rosbag Recording")
            self.recording = True
        else:
            self.rosbag_recorder.stop_recording()
            self.record_button.config(text="Start Rosbag Recording")
            self.recording = False

    def _on_launch_vital_ui(self):
        """Launch the Vital UI in a new process."""
        if self.ui_vital_process and self.ui_vital_process.poll() is None:
            self.get_logger().info("Vital UI is already running.")
            return

        self.get_logger().info("Launching Vital UI...")
        self.ui_vital_process = subprocess.Popen(['ros2', 'run', 'vital_recording', 'ui_vital'], preexec_fn=os.setsid)
        self.get_logger().info("Vital UI launched.")

    def _on_exit(self):
        """Handle the window close event."""
        if self.recording:
            self.rosbag_recorder.stop_recording()

        if self.ui_vital_process:
            try:
                os.killpg(os.getpgid(self.ui_vital_process.pid), signal.SIGTERM)  # Send SIGTERM to the process group
                try:
                    self.ui_vital_process.wait(timeout=3.0)
                    self.get_logger().info("Vital UI process terminated gracefully")
                except subprocess.TimeoutExpired:
                    # If it doesn't terminate gracefully, force kill
                    self.get_logger().warning("Vital UI subprocess did not terminate gracefully, force killing")
                    os.killpg(os.getpgid(self.ui_vital_process.pid), signal.SIGKILL)
                    self.ui_vital_process.wait()
            except (ProcessLookupError, OSError) as e:
                # Process might already be dead
                self.get_logger().info(f"Vital UI process already terminated: {e}")
            self.get_logger().info("Vital UI process terminated.")
                
        self.destroy_node()
        rclpy.shutdown()
        self.root.quit()
        self.root.destroy()

    def update_subprocess_status(self):
        """Update the status of the subprocesses."""
        vital_running = self.ui_vital_process is not None and self.ui_vital_process.poll() is None
        
        # Check if recording is actually running
        recording_alive = self.rosbag_recorder.is_recording()
        if self.recording and not recording_alive:
             self.recording = False
             self.record_button.config(text="Start Rosbag Recording")

        active_processes = int(vital_running) + int(self.recording)

        self.launch_vital_button.config(state=tk.DISABLED if vital_running else tk.NORMAL)
        self.quit_button.config(state=tk.DISABLED if active_processes > 0 else tk.NORMAL)
        
        # Update status message
        if active_processes == 0:
            self.status_label.config(text="Status: Ready", foreground="blue")
        elif self.recording and vital_running:
             self.status_label.config(text="Status: Vital UI & Recording Running", foreground="green")
        elif self.recording:
             self.status_label.config(text="Status: Recording Running", foreground="green")
        else:
            self.status_label.config(text="Status: Vital UI Running", foreground="green")



def main(args=None):
    rclpy.init(args=args)
    home_console = HomeConsole()
    try:
        home_console.root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        home_console._on_exit()


if __name__ == "__main__":
    main()