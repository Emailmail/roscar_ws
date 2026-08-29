#!/usr/bin/env python3
import argparse
from pathlib import Path
import re
import subprocess


def main():
    parser = argparse.ArgumentParser(description='Save Cartographer and occupancy maps.')
    parser.add_argument('--map-dir', required=True)
    parser.add_argument('--map-name', default='my_map')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', args.map_name):
        raise SystemExit('map-name may contain only letters, numbers, dot, underscore and dash')
    directory = Path(args.map_dir).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    base = directory / args.map_name
    subprocess.run([
        'ros2', 'service', 'call', '/write_state',
        'cartographer_ros_msgs/srv/WriteState',
        f'{{filename: "{base}.pbstream"}}',
    ], check=True)
    subprocess.run(
        ['ros2', 'run', 'nav2_map_server', 'map_saver_cli', '-f', str(base),
         # The default 2s subscription timeout races DDS discovery when the
         # machine is busy (e.g. cartographer under load) and aborts the save.
         '--ros-args', '-p', 'save_map_timeout:=15.0'],
        check=True,
    )
    print(f'Saved {base}.pbstream, {base}.yaml and map image')


if __name__ == '__main__':
    main()
