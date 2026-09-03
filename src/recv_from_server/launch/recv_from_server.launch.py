"""Launch the Raspberry Pi WebSocket-to-cmd_vel receiver."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    config = os.path.join(
        get_package_share_directory("recv_from_server"),
        "config",
        "recv_from_server.yaml",
    )
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "server_uri",
                default_value="ws://8.134.118.29:8771",
                description="WebSocket relay URI for the vehicle-side port",
            ),
            DeclareLaunchArgument(
                "remote_topic",
                default_value="/cmdvel_remote",
                description="Topic name encoded in incoming frames",
            ),
            DeclareLaunchArgument(
                "cmd_vel_topic",
                default_value="/cmd_vel",
                description="Local ROS Twist output topic",
            ),
            DeclareLaunchArgument(
                "reconnect_delay",
                default_value="2.0",
                description="Seconds between reconnect attempts",
            ),
            DeclareLaunchArgument(
                "command_timeout",
                default_value="0.5",
                description="Seconds without a frame before publishing zero",
            ),
            Node(
                package="recv_from_server",
                executable="recv_node",
                name="recv_from_server",
                output="screen",
                parameters=[
                    config,
                    {
                        "server_uri": LaunchConfiguration("server_uri"),
                        "remote_topic": LaunchConfiguration("remote_topic"),
                        "cmd_vel_topic": LaunchConfiguration("cmd_vel_topic"),
                        "reconnect_delay": LaunchConfiguration("reconnect_delay"),
                        "command_timeout": LaunchConfiguration("command_timeout"),
                    },
                ],
            )
        ]
    )
