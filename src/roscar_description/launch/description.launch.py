from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    arguments = []
    defaults = {
        'use_sim_time': 'false',
        'laser_x': '0.0', 'laser_y': '0.0', 'laser_z': '0.18', 'laser_yaw': '0.0',
        'imu_x': '0.0', 'imu_y': '0.0', 'imu_z': '0.0', 'imu_yaw': '0.0',
        'camera_x': '0.0', 'camera_y': '0.0', 'camera_z': '0.20', 'camera_yaw': '0.0',
    }
    for name, value in defaults.items():
        arguments.append(DeclareLaunchArgument(name, default_value=value))
    model = PathJoinSubstitution([
        FindPackageShare('roscar_description'), 'urdf', 'roscar.urdf.xacro'
    ])
    command = ['xacro ', model]
    for name in defaults:
        if name != 'use_sim_time':
            command += [' ', name, ':=', LaunchConfiguration(name)]
    description = ParameterValue(Command(command), value_type=str)
    arguments.append(Node(
        package='robot_state_publisher', executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': description,
            'use_sim_time': LaunchConfiguration('use_sim_time'),
        }],
    ))
    return LaunchDescription(arguments)
