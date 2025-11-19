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
            
    def start_recording(self):
        current_time = time.localtime()
        time_for_path = time.strftime("%Y-%m-%d_%H_%M_%S", current_time)
        bag_path = os.path.join(
            "/export", "rosbag", time_for_path
        )
        command = ["ros2", "bag", "record", "-a", "-o", bag_path]
        self.process = subprocess.Popen(command)
        self.get_logger().info("Started rosbag recording.")

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