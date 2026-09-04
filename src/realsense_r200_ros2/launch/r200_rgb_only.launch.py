from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'serial', default_value='',
            description='R200 序列号；留空时使用检测到的第一台 R200'),
        DeclareLaunchArgument(
            'use_presets', default_value='true',
            description='使用 SDK 的 R200 best_quality 彩色模式；设为 false 时读取 YAML 中的彩色参数'),
        Node(
            package='realsense_r200_ros2',
            executable='r200_node',
            name='r200_node',
            output='screen',
            parameters=[
                PathJoinSubstitution([
                    FindPackageShare('realsense_r200_ros2'), 'config', 'r200.yaml'
                ]),
                {
                    'serial': LaunchConfiguration('serial'),
                    'use_presets': LaunchConfiguration('use_presets'),
                    'depth_enabled': False,
                    'infrared_enabled': False,
                    'infrared2_enabled': False,
                    'publish_pointcloud': False,
                },
            ],
        ),
    ])
