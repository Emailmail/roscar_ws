from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    params = LaunchConfiguration('params_file')
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('nav2_bringup'), 'launch', 'navigation_launch.py'
        ])),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'params_file': params,
            'autostart': 'true',
            # Upstream Jazzy evaluates this value in a PythonExpression.
            'use_composition': 'False',
        }.items(),
    )
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument(
            'params_file',
            default_value=PathJoinSubstitution([
                FindPackageShare('roscar_navigation'), 'config', 'nav2_omni.yaml'
            ]),
        ),
        nav2,
    ])
