from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('map_dir'),
        DeclareLaunchArgument('map_name', default_value='my_map'),
        ExecuteProcess(
            cmd=['ros2', 'run', 'roscar_slam', 'save_map',
                 '--map-dir', LaunchConfiguration('map_dir'),
                 '--map-name', LaunchConfiguration('map_name')],
            output='screen',
        ),
    ])
