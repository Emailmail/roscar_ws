from types import SimpleNamespace

from dm_imu.node import DmImuNode
from rclpy.time import Time


class FakePublisher:
    def __init__(self):
        self.messages = []

    def publish(self, message):
        self.messages.append(message)


class FakeSerial:
    def __init__(self):
        self.accel = (1.0, -2.0, 3.0)
        self.gyro = None
        self.accel_ts = 1.0
        self.gyro_ts = 0.0

    def get_latest_all(self):
        return self.accel, self.gyro, None, self.accel_ts, self.gyro_ts, 0.0

    def get_latest_quaternion(self):
        return None, 0.0, None


def test_accel_topic_only_publishes_new_acceleration_frames():
    publisher = FakePublisher()
    serial = FakeSerial()
    node = SimpleNamespace(
        ser=serial,
        verbose=False,
        _no_frame_ticks=0,
        _last_data_ts=0.0,
        _last_accel_ts=0.0,
        _last_gyro_ts=0.0,
        _last_rpy_ts=0.0,
        _pub_count=0,
        linear_acceleration_scale=2.0,
        frame_id='imu_link',
        pub_accel=publisher,
        pub_gyro=None,
        pub_rpy=None,
        pub_imu=None,
        pub_pose=None,
        get_clock=lambda: SimpleNamespace(now=lambda: Time(seconds=123)),
    )

    DmImuNode._on_timer_publish(node)

    assert len(publisher.messages) == 1
    message = publisher.messages[0]
    assert message.header.frame_id == 'imu_link'
    assert message.header.stamp == Time(seconds=123).to_msg()
    assert (message.vector.x, message.vector.y, message.vector.z) == (2.0, -4.0, 6.0)

    serial.gyro_ts = 2.0
    DmImuNode._on_timer_publish(node)
    assert len(publisher.messages) == 1

    serial.accel = (4.0, 5.0, 6.0)
    serial.accel_ts = 3.0
    DmImuNode._on_timer_publish(node)
    assert len(publisher.messages) == 2


def test_gyro_topic_only_publishes_new_angular_velocity_frames():
    publisher = FakePublisher()
    serial = FakeSerial()
    serial.accel = None
    serial.accel_ts = 0.0
    serial.gyro = (-0.5, 1.0, 2.0)
    serial.gyro_ts = 1.0
    node = SimpleNamespace(
        ser=serial,
        verbose=False,
        _no_frame_ticks=0,
        _last_data_ts=0.0,
        _last_accel_ts=0.0,
        _last_gyro_ts=0.0,
        _last_rpy_ts=0.0,
        _pub_count=0,
        angular_velocity_scale=2.0,
        frame_id='imu_link',
        pub_accel=None,
        pub_gyro=publisher,
        pub_rpy=None,
        pub_imu=None,
        pub_pose=None,
        get_clock=lambda: SimpleNamespace(now=lambda: Time(seconds=456)),
    )

    DmImuNode._on_timer_publish(node)

    assert len(publisher.messages) == 1
    message = publisher.messages[0]
    assert message.header.frame_id == 'imu_link'
    assert message.header.stamp == Time(seconds=456).to_msg()
    assert (message.vector.x, message.vector.y, message.vector.z) == (-1.0, 2.0, 4.0)

    serial.accel = (1.0, 2.0, 3.0)
    serial.accel_ts = 2.0
    DmImuNode._on_timer_publish(node)
    assert len(publisher.messages) == 1

    serial.gyro = (3.0, 4.0, 5.0)
    serial.gyro_ts = 3.0
    DmImuNode._on_timer_publish(node)
    assert len(publisher.messages) == 2
