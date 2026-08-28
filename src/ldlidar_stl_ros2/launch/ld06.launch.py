#!/usr/bin/env python3
"""Launch the LD06 driver, optionally with its standalone compatibility TF."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    driver = Node(
        package='ldlidar_stl_ros2',
        executable='ldlidar_stl_ros2_node',
        name='LD06',
        output='screen',
        parameters=[{
            'product_name': 'LDLiDAR_LD06',
            'topic_name': 'scan',
            'frame_id': 'base_laser',
            'port_name': LaunchConfiguration('port'),
            'port_baudrate': 230400,
            'laser_scan_dir': True,
            'enable_angle_crop_func': False,
            'angle_crop_min': 135.0,
            'angle_crop_max': 225.0,
        }],
    )
    compatibility_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='base_link_to_base_laser_ld06',
        arguments=['0', '0', '0.18', '0', '0', '0', 'base_link', 'base_laser'],
        condition=IfCondition(LaunchConfiguration('publish_tf')),
    )
    return LaunchDescription([
        DeclareLaunchArgument('port', default_value='/dev/ttyUSB0'),
        DeclareLaunchArgument(
            'publish_tf', default_value='false',
            description='Enable only for standalone use without roscar_description.',
        ),
        driver,
        compatibility_tf,
    ])
