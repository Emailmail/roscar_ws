from pathlib import Path
from typing import Any

from ament_index_python.packages import get_package_share_directory
import yaml


def load_profile(value: str) -> dict[str, Any]:
    candidate = Path(value).expanduser()
    if not candidate.is_file():
        candidate = (
            Path(get_package_share_directory('roscar_bringup'))
            / 'config' / f'{value}.yaml'
        )
    if not candidate.is_file():
        raise RuntimeError(f'ROSCar profile not found: {value}')
    with candidate.open(encoding='utf-8') as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict) or not isinstance(data.get('devices'), dict):
        raise RuntimeError(f'Invalid ROSCar profile: {candidate}')
    return data


def override(configured: str, explicit: str) -> str:
    return explicit if explicit else configured
