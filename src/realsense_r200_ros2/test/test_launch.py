from pathlib import Path

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def test_launch_declares_and_forwards_serial():
    text = (PACKAGE_ROOT / 'launch/r200.launch.py').read_text(encoding='utf-8')
    assert "DeclareLaunchArgument(" in text
    assert "'serial'," in text
    assert "'serial': LaunchConfiguration('serial')" in text
    assert "'use_presets': LaunchConfiguration('use_presets')" in text


def test_launch_loads_package_yaml_before_overrides():
    text = (PACKAGE_ROOT / 'launch/r200.launch.py').read_text(encoding='utf-8')
    assert "'config', 'r200.yaml'" in text
    assert text.index("'config', 'r200.yaml'") < text.index("'serial': LaunchConfiguration")


def test_default_yaml_disables_pointcloud_and_pins_frames():
    with (PACKAGE_ROOT / 'config/r200.yaml').open(encoding='utf-8') as stream:
        params = yaml.safe_load(stream)['r200_node']['ros__parameters']
    assert params['publish_pointcloud'] is False
    assert params['frame_id'] == 'r200_link'
    assert params['depth_frame_id'] == 'r200_depth_optical_frame'


def test_rgb_only_launch_disables_depth_infrared_and_pointcloud():
    text = (PACKAGE_ROOT / 'launch/r200_rgb_only.launch.py').read_text(encoding='utf-8')
    assert "'depth_enabled': False" in text
    assert "'infrared_enabled': False" in text
    assert "'infrared2_enabled': False" in text
    assert "'publish_pointcloud': False" in text
