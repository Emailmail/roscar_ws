"""Reserved launch for pushing the camera stream to the cloud via WebRTC."""

from launch import LaunchDescription
from launch.actions import EmitEvent, OpaqueFunction
from launch.events import Shutdown
from launch.logging import get_logger


def _report_unimplemented(_context):
    get_logger('send2server').error(
        'WebRTC 视频推流已预留但尚未实现；拒绝启动。')
    return []


def generate_launch_description():
    return LaunchDescription([
        OpaqueFunction(function=_report_unimplemented),
        EmitEvent(event=Shutdown(reason='WebRTC video streaming is not implemented')),
    ])
