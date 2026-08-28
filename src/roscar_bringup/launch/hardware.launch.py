from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

from roscar_bringup.profile import load_profile, override


def _nodes(context):
    profile = load_profile(LaunchConfiguration('profile').perform(context))
    devices = profile['devices']
    transforms = profile.get('transforms', {})
    laser_tf = transforms.get('laser', {})
    imu_tf = transforms.get('imu', {})
    lidar = profile.get('lidar', {})
    imu_port = override(
        devices['imu_port'], LaunchConfiguration('imu_port').perform(context))
    lidar_port = override(
        devices['lidar_port'], LaunchConfiguration('lidar_port').perform(context))
    base_port = override(
        devices['base_port'], LaunchConfiguration('base_port').perform(context))

    description = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('roscar_description'), 'launch', 'description.launch.py'
        ])),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'laser_x': str(laser_tf.get('x', 0.0)),
            'laser_y': str(laser_tf.get('y', 0.0)),
            'laser_z': str(laser_tf.get('z', 0.18)),
            'laser_yaw': str(laser_tf.get('yaw', 0.0)),
            'imu_x': str(imu_tf.get('x', 0.0)),
            'imu_y': str(imu_tf.get('y', 0.0)),
            'imu_z': str(imu_tf.get('z', 0.0)),
            'imu_yaw': str(imu_tf.get('yaw', 0.0)),
        }.items(),
    )
    imu = Node(
        package='dm_imu', executable='dm_imu_node', name='dm_imu', output='screen',
        parameters=[
            PathJoinSubstitution([FindPackageShare('dm_imu'), 'config', 'params.yaml']),
            {'port': imu_port, 'frame_id': 'imu_link'},
        ],
    )
    laser = Node(
        package='ldlidar_stl_ros2', executable='ldlidar_stl_ros2_node',
        name='ldlidar', output='screen',
        parameters=[{
            'product_name': lidar.get('product_name', 'LDLiDAR_LD06'),
            'topic_name': 'scan', 'frame_id': 'base_laser',
            'port_name': lidar_port, 'port_baudrate': int(lidar.get('baudrate', 230400)),
            'laser_scan_dir': bool(lidar.get('scan_direction_counterclockwise', True)),
            'enable_angle_crop_func': False,
            'angle_crop_min': 135.0, 'angle_crop_max': 225.0,
        }],
    )
    base = Node(
        package='roscar_base', executable='c30d_driver', name='c30d_driver',
        output='screen', condition=IfCondition(LaunchConfiguration('use_base')),
        parameters=[
            PathJoinSubstitution([FindPackageShare('roscar_base'), 'config', 'c30d.yaml']),
            {'port': base_port, 'use_sim_time': LaunchConfiguration('use_sim_time')},
        ],
    )
    mux = Node(
        package='twist_mux', executable='twist_mux', name='twist_mux', output='screen',
        condition=IfCondition(LaunchConfiguration('use_base')),
        parameters=[PathJoinSubstitution([
            FindPackageShare('roscar_navigation'), 'config', 'twist_mux.yaml'
        ])],
        remappings=[('cmd_vel_out', '/cmd_vel')],
    )
    return [description, imu, laser, base, mux]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'profile', default_value='pc', description='pc, rpi5, or YAML path'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('use_base', default_value='true'),
        DeclareLaunchArgument(
            'imu_port', default_value='', description='Empty uses profile value'),
        DeclareLaunchArgument(
            'lidar_port', default_value='', description='Empty uses profile value'),
        DeclareLaunchArgument(
            'base_port', default_value='', description='Empty uses profile value'),
        OpaqueFunction(function=_nodes),
    ])
