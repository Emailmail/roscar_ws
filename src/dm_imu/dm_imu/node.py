import math
import threading
from typing import Tuple

from geometry_msgs.msg import PoseStamped, Vector3Stamped
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu

from .modules.dm_serial import DM_Serial


def euler_rpy_to_quat(roll: float, pitch: float, yaw: float) -> Tuple[float, float, float, float]:
    """Convert roll, pitch and yaw in radians to an (x, y, z, w) quaternion."""
    cy, sy = math.cos(yaw * 0.5), math.sin(yaw * 0.5)
    cp, sp = math.cos(pitch * 0.5), math.sin(pitch * 0.5)
    cr, sr = math.cos(roll * 0.5), math.sin(roll * 0.5)
    return (
        sr * cp * cy - cr * sp * sy,
        cr * sp * cy + sr * cp * sy,
        cr * cp * sy - sr * sp * cy,
        cr * cp * cy + sr * sp * sy,
    )


def normalize_quat(
    qx: float, qy: float, qz: float, qw: float
) -> Tuple[float, float, float, float]:
    values = (qx, qy, qz, qw)
    if not all(math.isfinite(value) for value in values):
        return 0.0, 0.0, 0.0, 1.0
    norm = math.sqrt(sum(value * value for value in values))
    if norm < 1e-6:
        return 0.0, 0.0, 0.0, 1.0
    return tuple(value / norm for value in values)


class DmImuNode(Node):
    def __init__(self):
        super().__init__('dm_imu')

        self.declare_parameter('port', '/dev/ttyACM0')
        self.declare_parameter('baudrate', 921600)
        self.declare_parameter('frame_id', 'imu_link')
        self.declare_parameter('publish_rpy_in_degree', True)
        self.declare_parameter('verbose', True)
        self.declare_parameter('qos_reliable', True)
        self.declare_parameter('publish_imu_data', False)
        self.declare_parameter('publish_accel', True)
        self.declare_parameter('publish_gyro', True)
        self.declare_parameter('publish_rpy', True)
        self.declare_parameter('publish_pose', False)
        # The manual's mapping ranges identify USB float values as ROS SI:
        # acceleration in m/s^2 and angular velocity in rad/s.
        self.declare_parameter('angular_velocity_scale', 1.0)
        self.declare_parameter('linear_acceleration_scale', 1.0)

        self.port = str(self.get_parameter('port').value or '/dev/ttyACM0')
        self.frame_id = str(self.get_parameter('frame_id').value or 'imu_link')
        self.publish_rpy_in_degree = bool(self.get_parameter('publish_rpy_in_degree').value)
        self.verbose = bool(self.get_parameter('verbose').value)
        self.publish_imu_data = bool(self.get_parameter('publish_imu_data').value)
        self.publish_accel = bool(self.get_parameter('publish_accel').value)
        self.publish_gyro = bool(self.get_parameter('publish_gyro').value)
        self.publish_rpy = bool(self.get_parameter('publish_rpy').value)
        self.publish_pose = bool(self.get_parameter('publish_pose').value)
        self.angular_velocity_scale = float(
            self.get_parameter('angular_velocity_scale').value)
        self.linear_acceleration_scale = float(
            self.get_parameter('linear_acceleration_scale').value)

        try:
            self.baudrate = int(self.get_parameter('baudrate').value)
        except (TypeError, ValueError):
            self.get_logger().warning('Invalid baudrate, falling back to 921600')
            self.baudrate = 921600

        if bool(self.get_parameter('qos_reliable').value):
            from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
            qos = QoSProfile(
                reliability=ReliabilityPolicy.RELIABLE,
                history=HistoryPolicy.KEEP_LAST,
                depth=50,
                durability=DurabilityPolicy.VOLATILE,
            )
        else:
            from rclpy.qos import qos_profile_sensor_data
            qos = qos_profile_sensor_data

        self.pub_imu = (
            self.create_publisher(Imu, 'imu/data', qos)
            if self.publish_imu_data else None
        )
        self.pub_accel = (
            self.create_publisher(Vector3Stamped, 'imu/accel', qos)
            if self.publish_accel else None
        )
        self.pub_gyro = (
            self.create_publisher(Vector3Stamped, 'imu/gyro', qos)
            if self.publish_gyro else None
        )
        self.pub_rpy = (
            self.create_publisher(Vector3Stamped, 'imu/rpy', qos)
            if self.publish_rpy else None
        )
        self.pub_pose = (
            self.create_publisher(PoseStamped, 'imu/pose', qos)
            if self.publish_pose else None
        )

        self.ser = DM_Serial(self.port, baudrate=self.baudrate)
        if not self.ser.start_reader():
            raise RuntimeError(f'Unable to open serial {self.port}: {self.ser.last_error()}')
        self.get_logger().info(f'Opened serial {self.port} @ {self.baudrate}')

        self._last_data_ts = 0.0
        self._last_stamp = None
        self._last_accel_ts = 0.0
        self._last_gyro_ts = 0.0
        self._last_rpy_ts = 0.0
        self._closing = threading.Event()
        self._no_frame_ticks = 0
        self._pub_count = 0

        self.timer_pub = self.create_timer(0.005, self._on_timer_publish)
        self.timer_stat = self.create_timer(2.0, self._on_timer_stats)

    def _on_timer_publish(self):
        try:
            accel, gyro, rpy, accel_ts, gyro_ts, rpy_ts, *_ = self.ser.get_latest_all()
            quaternion, quaternion_ts, _ = self.ser.get_latest_quaternion()
        except Exception as exc:
            if self.verbose:
                self.get_logger().warning(f'Unable to read IMU cache: {exc}')
            return

        newest_ts = max(accel_ts, gyro_ts, rpy_ts, quaternion_ts)
        if newest_ts <= 0.0:
            self._no_frame_ticks += 1
            if self._no_frame_ticks % 200 == 0 and self.verbose:
                self.get_logger().warning(
                    'No valid IMU frames yet; check streaming, baudrate and CRC'
                )
            return
        if newest_ts <= self._last_data_ts:
            return
        self._last_data_ts = newest_ts
        self._no_frame_ticks = 0

        r_deg = p_deg = y_deg = None
        if rpy is not None and len(rpy) == 3:
            r_deg, p_deg, y_deg = (float(value) for value in rpy)

        if quaternion is not None and len(quaternion) == 4:
            # Protocol order is W, X, Y, Z; ROS messages use X, Y, Z, W.
            qw, qx, qy, qz = (float(value) for value in quaternion)
            qx, qy, qz, qw = normalize_quat(qx, qy, qz, qw)
        elif r_deg is not None:
            qx, qy, qz, qw = euler_rpy_to_quat(
                math.radians(r_deg), math.radians(p_deg), math.radians(y_deg)
            )
        else:
            qx, qy, qz, qw = 0.0, 0.0, 0.0, 1.0

        stamp = self.get_clock().now().to_msg()
        # NTP corrections can step the wall clock backwards on RTC-less
        # boards; Cartographer aborts on non-monotonic sensor stamps, so
        # clamp every published stamp to be strictly increasing.
        if self._last_stamp is not None and (
                stamp.sec, stamp.nanosec) <= self._last_stamp:
            sec, nanosec = self._last_stamp
            nanosec += 1
            if nanosec >= 1_000_000_000:
                sec, nanosec = sec + 1, 0
            stamp.sec, stamp.nanosec = sec, nanosec
        self._last_stamp = (stamp.sec, stamp.nanosec)

        if (
            self.pub_accel is not None
            and accel is not None
            and len(accel) == 3
            and accel_ts > self._last_accel_ts
        ):
            accel_msg = Vector3Stamped()
            accel_msg.header.stamp = stamp
            accel_msg.header.frame_id = self.frame_id
            accel_msg.vector.x = accel[0] * self.linear_acceleration_scale
            accel_msg.vector.y = accel[1] * self.linear_acceleration_scale
            accel_msg.vector.z = accel[2] * self.linear_acceleration_scale
            self.pub_accel.publish(accel_msg)
            self._last_accel_ts = accel_ts

        if (
            self.pub_gyro is not None
            and gyro is not None
            and len(gyro) == 3
            and gyro_ts > self._last_gyro_ts
        ):
            gyro_msg = Vector3Stamped()
            gyro_msg.header.stamp = stamp
            gyro_msg.header.frame_id = self.frame_id
            gyro_msg.vector.x = gyro[0] * self.angular_velocity_scale
            gyro_msg.vector.y = gyro[1] * self.angular_velocity_scale
            gyro_msg.vector.z = gyro[2] * self.angular_velocity_scale
            self.pub_gyro.publish(gyro_msg)
            self._last_gyro_ts = gyro_ts

        if self.pub_rpy is not None and r_deg is not None and rpy_ts > self._last_rpy_ts:
            rpy_msg = Vector3Stamped()
            rpy_msg.header.stamp = stamp
            rpy_msg.header.frame_id = self.frame_id
            if self.publish_rpy_in_degree:
                rpy_msg.vector.x, rpy_msg.vector.y, rpy_msg.vector.z = r_deg, p_deg, y_deg
            else:
                rpy_msg.vector.x = math.radians(r_deg)
                rpy_msg.vector.y = math.radians(p_deg)
                rpy_msg.vector.z = math.radians(y_deg)
            self.pub_rpy.publish(rpy_msg)
            self._last_rpy_ts = rpy_ts

        if self.pub_imu is not None:
            imu = Imu()
            imu.header.stamp = stamp
            imu.header.frame_id = self.frame_id
            imu.orientation.x, imu.orientation.y = qx, qy
            imu.orientation.z, imu.orientation.w = qz, qw
            if quaternion is not None or rpy is not None:
                imu.orientation_covariance[0] = 0.02
                imu.orientation_covariance[4] = 0.02
                imu.orientation_covariance[8] = 0.02
            else:
                imu.orientation_covariance[0] = -1.0

            if gyro is not None and len(gyro) == 3:
                imu.angular_velocity.x = gyro[0] * self.angular_velocity_scale
                imu.angular_velocity.y = gyro[1] * self.angular_velocity_scale
                imu.angular_velocity.z = gyro[2] * self.angular_velocity_scale
                imu.angular_velocity_covariance[0] = 0.02
                imu.angular_velocity_covariance[4] = 0.02
                imu.angular_velocity_covariance[8] = 0.02
            else:
                imu.angular_velocity_covariance[0] = -1.0

            if accel is not None and len(accel) == 3:
                imu.linear_acceleration.x = accel[0] * self.linear_acceleration_scale
                imu.linear_acceleration.y = accel[1] * self.linear_acceleration_scale
                imu.linear_acceleration.z = accel[2] * self.linear_acceleration_scale
                imu.linear_acceleration_covariance[0] = 0.02
                imu.linear_acceleration_covariance[4] = 0.02
                imu.linear_acceleration_covariance[8] = 0.02
            else:
                imu.linear_acceleration_covariance[0] = -1.0
            self.pub_imu.publish(imu)

        if self.pub_pose is not None:
            pose = PoseStamped()
            pose.header.stamp = stamp
            pose.header.frame_id = self.frame_id
            pose.pose.orientation.x, pose.pose.orientation.y = qx, qy
            pose.pose.orientation.z, pose.pose.orientation.w = qz, qw
            self.pub_pose.publish(pose)

        self._pub_count += 1
        if self.verbose and r_deg is not None:
            self.get_logger().info(
                f'#{self._pub_count} RPY(deg)=({r_deg:.2f}, {p_deg:.2f}, {y_deg:.2f})'
            )

    def _on_timer_stats(self):
        if self.verbose:
            try:
                self.get_logger().info(f'[stats] {self.ser.get_stats()}')
            except Exception:
                pass

    def destroy_node(self):
        if getattr(self, '_closing', None) is None or self._closing.is_set():
            return super().destroy_node()
        self._closing.set()
        try:
            self.ser.close()
        except Exception:
            pass
        return super().destroy_node()


def main():
    rclpy.init()
    node = DmImuNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
