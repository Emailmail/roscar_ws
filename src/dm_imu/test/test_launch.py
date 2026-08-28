from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def test_rviz_launch_forwards_serial_port():
    launch_file = PACKAGE_ROOT / 'launch/dm_imu_rviz.launch.py'
    text = launch_file.read_text(encoding='utf-8')

    assert "DeclareLaunchArgument(\n            'port'," in text
    assert "{'port': LaunchConfiguration('port')}" in text
    assert "'publish_tf',\n            default_value='true'" in text
    assert "'--frame-id', 'base_link'" in text
    assert "'--child-frame-id', 'imu_link'" in text


def test_rviz_uses_compatibility_tf_parent_as_fixed_frame():
    rviz_config = PACKAGE_ROOT / 'rviz/imu.rviz'
    text = rviz_config.read_text(encoding='utf-8')

    assert 'Fixed Frame: base_link' in text
