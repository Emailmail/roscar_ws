import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_share = get_package_share_directory('dm_imu')
    params_file = os.path.join(pkg_share, 'config', 'params.yaml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'port',
            default_value='/dev/ttyACM0',
            description='DM-IMU serial device',
        ),
        Node(
            package='dm_imu',
            executable='dm_imu_node',
            name='dm_imu',
            output='screen',
            parameters=[params_file, {'port': LaunchConfiguration('port')}]
        )
    ])
