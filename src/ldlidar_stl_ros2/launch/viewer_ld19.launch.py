#!/usr/bin/env python3
"""Launch LD19 with its standalone RViz view."""

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    package = get_package_share_directory('ldlidar_stl_ros2')
    driver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(package + '/launch/ld19.launch.py'),
        launch_arguments={'publish_tf': 'true'}.items(),
    )
    rviz = Node(
        package='rviz2', executable='rviz2', name='rviz2_show_ld19',
        arguments=['-d', package + '/rviz2/ldlidar.rviz'], output='screen',
    )
    return LaunchDescription([driver, rviz])
