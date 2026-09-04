"""Text-level checks for the send2server launch files."""

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def test_status_launch_forwards_all_parameters():
    launch_file = PACKAGE_ROOT / 'launch/status.launch.py'
    text = launch_file.read_text(encoding='utf-8')

    for argument in (
        'server_uri',
        'map_frame',
        'robot_frame',
        'odom_topic',
        'status_period',
        'reconnect_delay',
        'battery',
        'traffic',
    ):
        assert f'"{argument}",' in text
        assert f'"{argument}": LaunchConfiguration("{argument}")' in text
    assert 'default_value="ws://8.134.118.29:8772"' in text
    assert 'executable="status_node"' in text


def test_webrtc_launch_refuses_to_start_until_implemented():
    launch_file = PACKAGE_ROOT / 'launch/webrtc.launch.py'
    text = launch_file.read_text(encoding='utf-8')

    assert '尚未实现' in text
    assert 'Shutdown' in text
    assert 'Node(' not in text
