from launch import LaunchDescription
from launch.actions import EmitEvent, OpaqueFunction
from launch.events import Shutdown
from launch.logging import get_logger


def _report_unimplemented(_context):
    get_logger('roscar_exploration').error(
        'Autonomous exploration is reserved but not implemented; refusing to start.')
    return []


def generate_launch_description():
    return LaunchDescription([
        OpaqueFunction(function=_report_unimplemented),
        EmitEvent(event=Shutdown(reason='Autonomous exploration is not implemented')),
    ])
