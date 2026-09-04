"""Launch the vehicle status pusher towards the cloud WebSocket relay."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    config = os.path.join(
        get_package_share_directory("send2server"),
        "config",
        "send2server.yaml",
    )
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "server_uri",
                default_value="ws://8.134.118.29:8772",
                description="WebSocket relay URI for the status push port",
            ),
            DeclareLaunchArgument(
                "map_frame",
                default_value="map",
                description="Parent frame of the reported pose",
            ),
            DeclareLaunchArgument(
                "robot_frame",
                default_value="base_footprint",
                description="Child frame of the reported pose",
            ),
            DeclareLaunchArgument(
                "odom_topic",
                default_value="/odom",
                description="Odometry topic used only for the speed field",
            ),
            DeclareLaunchArgument(
                "status_period",
                default_value="0.1",
                description="Seconds between status frames",
            ),
            DeclareLaunchArgument(
                "reconnect_delay",
                default_value="2.0",
                description="Seconds between reconnect attempts",
            ),
            DeclareLaunchArgument(
                "battery",
                default_value="0.0",
                description="Battery voltage sent to the viewer (no onboard source)",
            ),
            DeclareLaunchArgument(
                "traffic",
                default_value="green",
                description="Traffic state reported to the viewer: green, red or stop",
            ),
            Node(
                package="send2server",
                executable="status_node",
                name="send2server",
                output="screen",
                parameters=[
                    config,
                    {
                        "server_uri": LaunchConfiguration("server_uri"),
                        "map_frame": LaunchConfiguration("map_frame"),
                        "robot_frame": LaunchConfiguration("robot_frame"),
                        "odom_topic": LaunchConfiguration("odom_topic"),
                        "status_period": LaunchConfiguration("status_period"),
                        "reconnect_delay": LaunchConfiguration("reconnect_delay"),
                        "battery": LaunchConfiguration("battery"),
                        "traffic": LaunchConfiguration("traffic"),
                    },
                ],
            )
        ]
    )
