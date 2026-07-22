from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    
    return LaunchDescription([
        Node(
            package='rgbd_recording',
            executable='ui_rgbd',
            name='ui_rgbd_node',
            output='screen',
            respawn=True,
        ),
        Node(
            package='gsr_recording',
            executable='ui_gsr',
            name='ui_gsr_node',
            output='screen',
            respawn=True,
        )
    ])