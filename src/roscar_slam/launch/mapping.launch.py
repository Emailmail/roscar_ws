from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    config_basename = LaunchConfiguration('configuration_basename')
    config_dir = PathJoinSubstitution([FindPackageShare('roscar_slam'), 'config'])
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument(
            'configuration_basename', default_value='cartographer_2d_odom.lua',
            description='Use cartographer_2d_no_odom.lua for sensor-only tests.',
        ),
        Node(
            package='cartographer_ros', executable='cartographer_node',
            name='cartographer_node', output='screen',
            parameters=[{'use_sim_time': use_sim_time}],
            arguments=['-configuration_directory', config_dir,
                       '-configuration_basename', config_basename],
            remappings=[('scan', '/scan'), ('imu', '/imu/data'), ('odom', '/odom')],
        ),
        Node(
            package='cartographer_ros', executable='cartographer_occupancy_grid_node',
            name='cartographer_occupancy_grid_node', output='screen',
            parameters=[{'use_sim_time': use_sim_time, 'resolution': 0.05}],
        ),
    ])
