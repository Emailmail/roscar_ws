from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    hardware = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('roscar_bringup'), 'launch', 'hardware.launch.py'
        ])), launch_arguments={
            'profile': LaunchConfiguration('profile'),
            'imu_port': LaunchConfiguration('imu_port'),
            'lidar_port': LaunchConfiguration('lidar_port'),
            'base_port': LaunchConfiguration('base_port'),
            'use_base': 'true',
        }.items())
    keyboard = ExecuteProcess(
        cmd=['ros2', 'run', 'teleop_twist_keyboard', 'teleop_twist_keyboard',
             '--ros-args', '-r', 'cmd_vel:=/cmd_vel_teleop'],
        output='screen', emulate_tty=True)
    return LaunchDescription([
        DeclareLaunchArgument('profile', default_value='pc'),
        DeclareLaunchArgument('imu_port', default_value=''),
        DeclareLaunchArgument('lidar_port', default_value=''),
        DeclareLaunchArgument('base_port', default_value=''),
        hardware, keyboard,
    ])
