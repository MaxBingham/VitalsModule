#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool

import subprocess

import os
import time

class RosbagRecorder(Node):
    def __init__(self):
        super().__init__('rosbag_recorder')
        self.process = None
        self.topic_list = [
            '/camera/camera/color/image_raw',
            '/camera/camera/depth/image_rect_raw',
            "/camera/camera/color/camera_info",
            "/tf",
            "/tf_static",
            "/audio",
            "/gsr_data",
            "/vital_waveform_data",
            "/vital_numeric_data",
        ]
            
    def start_recording(self):
            current_time = time.localtime()
            time_for_path = time.strftime("%Y-%m-%d_%H_%M_%S", current_time)
            
            # === CHANGED SECTION START ===
            # 1. Define the directory where bags live
            base_dir = "/export/rosbag"

            # 2. Create it if it doesn't exist
            if not os.path.exists(base_dir):
                try:
                    os.makedirs(base_dir, exist_ok=True)
                    self.get_logger().info(f"Created directory: {base_dir}")
                except OSError as e:
                    self.get_logger().error(f"Failed to create directory {base_dir}: {e}")
                    return
            
            # 3. Define the full path for this specific recording
            bag_path = os.path.join(base_dir, time_for_path)
            # === CHANGED SECTION END ===

            command = ["ros2", "bag", "record", "-o", bag_path]
            for topic in self.topic_list:
                command.append(topic)
            self.process = subprocess.Popen(command)

            self.get_logger().info(f"Started rosbag recording at {bag_path}")

    def stop_recording(self):
        if self.process:
            if self.process.poll() is None:
                self.process.terminate()
                self.process.wait()
            self.get_logger().info("Stopped rosbag recording.")
            self.process = None

    def is_recording(self):
        return self.process is not None and self.process.poll() is None


def main(args=None):
    rclpy.init(args=args)

    rosbag_recorder = RosbagRecorder()
    rclpy.spin(rosbag_recorder)

    rosbag_recorder.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()