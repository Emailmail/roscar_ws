from pathlib import Path

import pytest

from roscar_bringup.profile import load_profile, override


@pytest.mark.parametrize('name', ['pc', 'rpi5'])
def test_profiles_contain_required_devices(name):
    profile = load_profile(name)
    assert set(profile['devices']) == {'imu_port', 'lidar_port', 'base_port'}
    assert profile['lidar']['product_name'] == 'LDLiDAR_LD06'


def test_explicit_profile_path_and_override(tmp_path: Path):
    profile = tmp_path / 'custom.yaml'
    profile.write_text(
        'devices:\n  imu_port: /dev/i\n  lidar_port: /dev/l\n  base_port: /dev/b\n',
        encoding='utf-8',
    )
    assert load_profile(str(profile))['devices']['base_port'] == '/dev/b'
    assert override('/dev/from-profile', '') == '/dev/from-profile'
    assert override('/dev/from-profile', '/dev/explicit') == '/dev/explicit'


def test_invalid_profile_is_rejected(tmp_path: Path):
    profile = tmp_path / 'bad.yaml'
    profile.write_text('not_devices: true\n', encoding='utf-8')
    with pytest.raises(RuntimeError):
        load_profile(str(profile))
