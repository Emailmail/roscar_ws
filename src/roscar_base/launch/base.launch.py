from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('port', default_value='/dev/ttyACM0'),
        Node(
            package='roscar_base', executable='c30d_driver', output='screen',
            parameters=[
                PathJoinSubstitution([FindPackageShare('roscar_base'), 'config', 'c30d.yaml']),
                {'port': LaunchConfiguration('port')},
            ],
        ),
    ])
