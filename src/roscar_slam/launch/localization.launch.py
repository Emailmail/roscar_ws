import math

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def _cartographer(context):
    map_dir = LaunchConfiguration('map_dir').perform(context)
    map_name = LaunchConfiguration('map_name').perform(context)
    x = float(LaunchConfiguration('initial_x').perform(context))
    y = float(LaunchConfiguration('initial_y').perform(context))
    yaw = math.radians(float(LaunchConfiguration('initial_yaw_deg').perform(context)))
    arguments = [
        '-configuration_directory',
        PathJoinSubstitution([FindPackageShare('roscar_slam'), 'config']).perform(context),
        '-configuration_basename',
        LaunchConfiguration('configuration_basename').perform(context),
        '-load_state_filename', f'{map_dir}/{map_name}.pbstream',
    ]
    if x != 0.0 or y != 0.0 or yaw != 0.0:
        pose = (
            '{to_trajectory_id = 0, relative_pose = {translation = {'
            f'{x}, {y}, 0.}}, rotation = {{0., 0., {math.sin(yaw / 2.0)}, '
            f'{math.cos(yaw / 2.0)}}}}}}}'
        )
        arguments += ['-initial_trajectory_pose', pose]
    return [Node(
        package='cartographer_ros', executable='cartographer_node',
        name='cartographer_node', output='screen',
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}],
        arguments=arguments,
        remappings=[('scan', '/scan'), ('imu', '/imu/data'), ('odom', '/odom')],
    )]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('map_dir'),
        DeclareLaunchArgument('map_name', default_value='my_map'),
        DeclareLaunchArgument(
            'configuration_basename', default_value='cartographer_localization.lua'),
        DeclareLaunchArgument('initial_x', default_value='0.0'),
        DeclareLaunchArgument('initial_y', default_value='0.0'),
        DeclareLaunchArgument('initial_yaw_deg', default_value='0.0'),
        OpaqueFunction(function=_cartographer),
    ])
