from pathlib import Path
import xml.etree.ElementTree as ET

import yaml


WORKSPACE = Path(__file__).resolve().parents[3]


def test_robot_frames_have_single_static_parent():
    model = WORKSPACE / 'src/roscar_description/urdf/roscar.urdf.xacro'
    root = ET.parse(model).getroot()
    children = [joint.find('child').attrib['link'] for joint in root.findall('joint')]
    assert len(children) == len(set(children))
    assert set(children) == {'base_link', 'base_laser', 'imu_link'}


def test_system_hardware_launch_does_not_publish_manual_static_tf():
    launch = WORKSPACE / 'src/roscar_bringup/launch/hardware.launch.py'
    assert 'static_transform_publisher' not in launch.read_text(encoding='utf-8')


def test_cartographer_uses_external_odom_without_tf_cycle():
    config = WORKSPACE / 'src/roscar_slam/config/cartographer_2d_odom.lua'
    text = config.read_text(encoding='utf-8')
    assert 'published_frame = "odom"' in text
    assert 'provide_odom_frame = false' in text
    assert 'use_odometry = true' in text


def test_sensor_only_cartographer_publishes_base_footprint():
    config = WORKSPACE / 'src/roscar_slam/config/cartographer_2d_no_odom.lua'
    text = config.read_text(encoding='utf-8')
    assert 'published_frame = "base_footprint"' in text
    assert 'provide_odom_frame = true' in text
    assert 'use_odometry = false' in text


def test_nav2_controller_is_omnidirectional():
    config = WORKSPACE / 'src/roscar_navigation/config/nav2_omni.yaml'
    with config.open(encoding='utf-8') as stream:
        params = yaml.safe_load(stream)
    follow_path = params['controller_server']['ros__parameters']['FollowPath']
    assert follow_path['motion_model'] == 'Omni'
    assert follow_path['vy_max'] > 0.0


def test_nav2_composition_value_is_jazzy_python_literal():
    launch = WORKSPACE / 'src/roscar_navigation/launch/navigation.launch.py'
    text = launch.read_text(encoding='utf-8')
    # Jazzy nav2_bringup places this argument inside PythonExpression; the
    # lowercase ROS boolean spelling would be evaluated as an unknown name.
    assert "'use_composition': 'False'" in text
