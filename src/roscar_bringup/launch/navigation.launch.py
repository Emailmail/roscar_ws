from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    map_dir = LaunchConfiguration('map_dir')
    map_name = LaunchConfiguration('map_name')
    map_yaml = PythonExpression(["'", map_dir, '/', map_name, ".yaml'"])
    hardware_args = {
        name: LaunchConfiguration(name)
        for name in ('profile', 'use_sim_time', 'imu_port', 'lidar_port', 'base_port')
    }
    hardware_args['use_base'] = 'true'
    hardware = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('roscar_bringup'), 'launch', 'hardware.launch.py'
        ])), launch_arguments=hardware_args.items())
    localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('roscar_slam'), 'launch', 'localization.launch.py'
        ])), launch_arguments={
            'use_sim_time': use_sim_time, 'map_dir': map_dir, 'map_name': map_name,
            'initial_x': LaunchConfiguration('initial_x'),
            'initial_y': LaunchConfiguration('initial_y'),
            'initial_yaw_deg': LaunchConfiguration('initial_yaw_deg'),
        }.items())
    map_server = Node(
        package='nav2_map_server', executable='map_server',
        name='map_server', output='screen',
        parameters=[
            PathJoinSubstitution([
                FindPackageShare('roscar_navigation'), 'config', 'nav2_omni.yaml'
            ]),
            {'yaml_filename': map_yaml, 'use_sim_time': use_sim_time},
        ])
    map_lifecycle = Node(
        package='nav2_lifecycle_manager', executable='lifecycle_manager',
        name='lifecycle_manager_map', output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'autostart': True,
            'node_names': ['map_server'],
        }])
    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('roscar_navigation'), 'launch', 'navigation.launch.py'
        ])), launch_arguments={'use_sim_time': use_sim_time}.items())
    rviz = Node(
        package='rviz2', executable='rviz2', name='rviz2', output='screen',
        arguments=['-d', PathJoinSubstitution([
            FindPackageShare('roscar_navigation'), 'rviz', 'navigation.rviz'
        ])], condition=IfCondition(LaunchConfiguration('use_rviz')))
    exploration = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('roscar_exploration'), 'launch', 'exploration.launch.py'
        ])), condition=IfCondition(LaunchConfiguration('use_exploration')))
    return LaunchDescription([
        DeclareLaunchArgument('profile', default_value='pc'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('imu_port', default_value=''),
        DeclareLaunchArgument('lidar_port', default_value=''),
        DeclareLaunchArgument('base_port', default_value=''),
        DeclareLaunchArgument('map_dir', default_value=PathJoinSubstitution([
            FindPackageShare('roscar_maps'), 'maps'
        ])),
        DeclareLaunchArgument('map_name', default_value='my_map'),
        DeclareLaunchArgument('initial_x', default_value='0.0'),
        DeclareLaunchArgument('initial_y', default_value='0.0'),
        DeclareLaunchArgument('initial_yaw_deg', default_value='0.0'),
        DeclareLaunchArgument('use_rviz', default_value='true'),
        DeclareLaunchArgument('use_exploration', default_value='false'),
        hardware, localization, map_server, map_lifecycle, navigation, rviz, exploration,
    ])
