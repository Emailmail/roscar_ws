from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    forwarded = {
        name: LaunchConfiguration(name)
        for name in ('profile', 'use_sim_time', 'use_base', 'imu_port', 'lidar_port', 'base_port')
    }
    hardware = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('roscar_bringup'), 'launch', 'hardware.launch.py'
        ])), launch_arguments=forwarded.items())
    config = PythonExpression([
        "'cartographer_2d_odom.lua' if '", LaunchConfiguration('use_base'),
        "'.lower() == 'true' else 'cartographer_2d_no_odom.lua'",
    ])
    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('roscar_slam'), 'launch', 'mapping.launch.py'
        ])),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'configuration_basename': config,
        }.items())
    return LaunchDescription([
        DeclareLaunchArgument('profile', default_value='pc'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('use_base', default_value='true'),
        DeclareLaunchArgument('imu_port', default_value=''),
        DeclareLaunchArgument('lidar_port', default_value=''),
        DeclareLaunchArgument('base_port', default_value=''),
        hardware, slam,
    ])
