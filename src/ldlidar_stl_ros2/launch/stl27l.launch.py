#!/usr/bin/env python3
"""Launch the STL27L driver, optionally with its standalone compatibility TF."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    driver = Node(
        package='ldlidar_stl_ros2',
        executable='ldlidar_stl_ros2_node',
        name='STL27L',
        output='screen',
        parameters=[{
            'product_name': 'LDLiDAR_STL27L',
            'topic_name': 'scan',
            'frame_id': 'base_laser',
            'port_name': LaunchConfiguration('port'),
            'port_baudrate': 921600,
            'laser_scan_dir': False,
            'enable_angle_crop_func': False,
            'angle_crop_min': 0.0,
            'angle_crop_max': 0.0,
        }],
    )
    compatibility_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='base_link_to_base_laser_stl27l',
        arguments=['0', '0', '0.18', '0', '0', '0', 'base_link', 'base_laser'],
        condition=IfCondition(LaunchConfiguration('publish_tf')),
    )
    return LaunchDescription([
        DeclareLaunchArgument('port', default_value='/dev/ttyUSB0'),
        DeclareLaunchArgument('publish_tf', default_value='false'),
        driver,
        compatibility_tf,
    ])
