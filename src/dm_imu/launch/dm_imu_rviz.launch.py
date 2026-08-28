import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('dm_imu')
    params_file = os.path.join(pkg_share, 'config', 'params.yaml')
    rviz_config = os.path.join(pkg_share, 'rviz', 'imu.rviz')

    return LaunchDescription([
        DeclareLaunchArgument(
            'port',
            default_value='/dev/ttyACM0',
            description='DM-IMU serial device',
        ),
        DeclareLaunchArgument(
            'publish_tf',
            default_value='true',
            description='Enable only for standalone use without roscar_description.',
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='base_link_to_imu_link_dm_imu_viewer',
            arguments=[
                '--frame-id', 'base_link',
                '--child-frame-id', 'imu_link',
            ],
            condition=IfCondition(LaunchConfiguration('publish_tf')),
        ),
        Node(
            package='dm_imu',
            executable='dm_imu_node',
            name='dm_imu',
            output='screen',
            parameters=[params_file, {'port': LaunchConfiguration('port')}],
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config] if os.path.exists(rviz_config) else [],
        ),
    ])
