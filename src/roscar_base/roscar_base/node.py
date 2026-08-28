import math
import threading
import time
from typing import Optional

from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from tf2_ros import TransformBroadcaster

from .odometry import PlanarOdometry
from .protocol import encode_velocity_command, Telemetry, TelemetryParser
from .safety import safe_velocity


def yaw_to_quaternion(yaw: float) -> tuple[float, float, float, float]:
    return 0.0, 0.0, math.sin(yaw * 0.5), math.cos(yaw * 0.5)


class C30dDriver(Node):
    def __init__(self) -> None:
        super().__init__('c30d_driver')
        defaults = {
            'port': '/dev/ttyACM0', 'baudrate': 115200, 'send_rate': 50.0,
            'telemetry_rate': 20.0,
            'cmd_timeout': 0.3, 'reconnect_interval': 2.0,
            'max_linear_speed': 0.5, 'max_angular_speed': 1.5,
            'odom_frame': 'odom', 'base_frame': 'base_footprint',
            'publish_tf': True,
        }
        for name, value in defaults.items():
            self.declare_parameter(name, value)

        self._port = str(self.get_parameter('port').value)
        self._baudrate = int(self.get_parameter('baudrate').value)
        self._cmd_timeout = float(self.get_parameter('cmd_timeout').value)
        self._telemetry_period = 1.0 / max(
            1.0, float(self.get_parameter('telemetry_rate').value))
        self._reconnect_interval = float(self.get_parameter('reconnect_interval').value)
        self._max_linear = float(self.get_parameter('max_linear_speed').value)
        self._max_angular = float(self.get_parameter('max_angular_speed').value)
        self._odom_frame = str(self.get_parameter('odom_frame').value)
        self._base_frame = str(self.get_parameter('base_frame').value)
        self._publish_tf = bool(self.get_parameter('publish_tf').value)

        self._serial = None
        self._last_open_attempt = 0.0
        self._parser = TelemetryParser()
        self._pose = PlanarOdometry()
        self._last_telemetry_time: Optional[float] = None
        self._latest_telemetry: Optional[Telemetry] = None
        self._cmd = Twist()
        self._last_cmd_time: Optional[float] = None
        self._lock = threading.Lock()

        self.create_subscription(Twist, 'cmd_vel', self._on_cmd, 10)
        self._odom_pub = self.create_publisher(Odometry, 'odom', 20)
        self._tf = TransformBroadcaster(self)
        rate = max(1.0, float(self.get_parameter('send_rate').value))
        self.create_timer(1.0 / rate, self._tick)
        self.get_logger().info(f'C30D driver configured for {self._port} @ {self._baudrate}')

    def _on_cmd(self, msg: Twist) -> None:
        with self._lock:
            self._cmd = msg
            self._last_cmd_time = time.monotonic()

    def _connect_if_due(self, now: float) -> None:
        if self._serial is not None or now - self._last_open_attempt < self._reconnect_interval:
            return
        self._last_open_attempt = now
        try:
            import serial
            self._serial = serial.Serial(
                self._port, self._baudrate, timeout=0, write_timeout=0.05
            )
            self._parser = TelemetryParser()
            self.get_logger().info(f'Opened chassis serial {self._port}')
        except Exception as exc:
            self.get_logger().warning(f'Chassis serial unavailable: {exc}')

    def _disconnect(self, reason: Exception) -> None:
        self.get_logger().warning(f'Chassis serial disconnected: {reason}')
        try:
            if self._serial is not None:
                self._serial.close()
        except Exception:
            pass
        self._serial = None
        with self._lock:
            # A reconnected controller must receive a fresh command.
            self._last_cmd_time = None

    def _safe_command(self, now: float) -> tuple[float, float, float]:
        with self._lock:
            msg, stamp = self._cmd, self._last_cmd_time
        if stamp is None:
            return 0.0, 0.0, 0.0
        return safe_velocity(
            msg.linear.x, msg.linear.y, msg.angular.z,
            now - stamp, self._cmd_timeout, self._max_linear, self._max_angular,
        )

    def _tick(self) -> None:
        now = time.monotonic()
        self._connect_if_due(now)
        if self._serial is None:
            return
        try:
            waiting = self._serial.in_waiting
            if waiting:
                messages = self._parser.feed(self._serial.read(waiting))
                received_at = time.monotonic()
                for index, telemetry in enumerate(messages):
                    age = (len(messages) - index - 1) * self._telemetry_period
                    self._accept_telemetry(telemetry, received_at - age)
            self._serial.write(encode_velocity_command(*self._safe_command(now)))
        except Exception as exc:
            self._disconnect(exc)

    def _accept_telemetry(self, telemetry: Telemetry, now: float) -> None:
        if self._last_telemetry_time is not None:
            dt = now - self._last_telemetry_time
            if 0.0 < dt <= 0.5:
                self._pose.integrate(telemetry.vx, telemetry.vy, telemetry.wz, dt)
        self._last_telemetry_time = now
        self._latest_telemetry = telemetry
        self._publish_odometry(telemetry)

    def _publish_odometry(self, telemetry: Telemetry) -> None:
        stamp = self.get_clock().now().to_msg()
        qx, qy, qz, qw = yaw_to_quaternion(self._pose.yaw)
        msg = Odometry()
        msg.header.stamp = stamp
        msg.header.frame_id = self._odom_frame
        msg.child_frame_id = self._base_frame
        msg.pose.pose.position.x = self._pose.x
        msg.pose.pose.position.y = self._pose.y
        msg.pose.pose.orientation.x = qx
        msg.pose.pose.orientation.y = qy
        msg.pose.pose.orientation.z = qz
        msg.pose.pose.orientation.w = qw
        msg.pose.covariance[0] = 0.05
        msg.pose.covariance[7] = 0.05
        msg.pose.covariance[35] = 0.10
        msg.twist.twist.linear.x = telemetry.vx
        msg.twist.twist.linear.y = telemetry.vy
        msg.twist.twist.angular.z = telemetry.wz
        msg.twist.covariance[0] = 0.02
        msg.twist.covariance[7] = 0.02
        msg.twist.covariance[35] = 0.05
        self._odom_pub.publish(msg)
        if self._publish_tf:
            transform = TransformStamped()
            transform.header = msg.header
            transform.child_frame_id = self._base_frame
            transform.transform.translation.x = self._pose.x
            transform.transform.translation.y = self._pose.y
            transform.transform.rotation = msg.pose.pose.orientation
            self._tf.sendTransform(transform)

    def destroy_node(self):
        try:
            if self._serial is not None:
                self._serial.write(encode_velocity_command(0.0, 0.0, 0.0))
                self._serial.close()
        except Exception:
            pass
        return super().destroy_node()


def main() -> None:
    rclpy.init()
    node = C30dDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
