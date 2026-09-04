"""ROS 2 node that pushes vehicle status to the cloud relay over WebSocket."""

import asyncio
import json
from typing import Any

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from nav_msgs.msg import Odometry
import tf2_ros
import websockets

from .protocol import (
    ProtocolError,
    build_pong_frame,
    build_status_frame,
    normalize_traffic,
    yaw_from_quaternion,
)


DEFAULT_SERVER_URI = "ws://8.134.118.29:8772"


class SendToServerNode(Node):
    """Sample the map-frame pose and push status JSON to the relay."""

    def __init__(self) -> None:
        super().__init__("send2server")
        self.declare_parameter("server_uri", DEFAULT_SERVER_URI)
        self.declare_parameter("map_frame", "map")
        self.declare_parameter("robot_frame", "base_footprint")
        self.declare_parameter("odom_topic", "/odom")
        self.declare_parameter("status_period", 0.1)
        self.declare_parameter("reconnect_delay", 2.0)
        self.declare_parameter("battery", 0.0)
        self.declare_parameter("traffic", "green")

        self.server_uri = str(self.get_parameter("server_uri").value)
        self.map_frame = str(self.get_parameter("map_frame").value)
        self.robot_frame = str(self.get_parameter("robot_frame").value)
        self.odom_topic = str(self.get_parameter("odom_topic").value)
        self.status_period = float(self.get_parameter("status_period").value)
        self.reconnect_delay = float(self.get_parameter("reconnect_delay").value)
        self.battery = float(self.get_parameter("battery").value)
        try:
            self.traffic = normalize_traffic(self.get_parameter("traffic").value)
        except ProtocolError as error:
            raise ValueError(str(error)) from error
        if not self.server_uri.startswith(("ws://", "wss://")):
            raise ValueError("server_uri must start with ws:// or wss://")
        if not self.map_frame or not self.robot_frame or not self.odom_topic:
            raise ValueError("map_frame, robot_frame and odom_topic must not be empty")
        if self.status_period <= 0:
            raise ValueError("status_period must be greater than 0")
        if self.reconnect_delay <= 0:
            raise ValueError("reconnect_delay must be greater than 0")

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        self.speed = 0.0
        self.create_subscription(Odometry, self.odom_topic, self._on_odom, 20)
        self.get_logger().info(
            f"推送 {self.map_frame}->{self.robot_frame} 状态到 {self.server_uri}，"
            f"周期 {self.status_period}s，速度取自 {self.odom_topic}"
        )

    def _on_odom(self, message: Odometry) -> None:
        self.speed = message.twist.twist.linear.x

    def build_status(self) -> dict | None:
        """Return one status frame, or None while the map TF is unavailable."""
        try:
            transform = self.tf_buffer.lookup_transform(
                self.map_frame, self.robot_frame, Time()
            )
        except tf2_ros.TransformException as error:
            self.get_logger().warning(
                f"等待 {self.map_frame}->{self.robot_frame} TF（SLAM 未运行？），跳过状态上报: "
                f"{type(error).__name__}",
                throttle_duration_sec=5.0,
            )
            return None
        translation = transform.transform.translation
        rotation = transform.transform.rotation
        return build_status_frame(
            x=translation.x,
            y=translation.y,
            yaw=yaw_from_quaternion(rotation),
            speed=self.speed,
            battery=self.battery,
            traffic=self.traffic,
        )


async def spin_ros(node: SendToServerNode) -> None:
    """Service ROS callbacks from the asyncio event loop."""
    while rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0)
        await asyncio.sleep(0.01)


async def stream_status(websocket: Any, node: SendToServerNode) -> None:
    """Periodically push the latest status frame while connected."""
    while True:
        await asyncio.sleep(node.status_period)
        frame = node.build_status()
        if frame is None:
            continue
        await websocket.send(json.dumps(frame, allow_nan=False, separators=(",", ":")))
        node.get_logger().debug(f"status 已上报: {frame}")


async def answer_pings(websocket: Any, node: SendToServerNode) -> None:
    """Echo viewer pings and log everything else without acting on it."""
    async for raw in websocket:
        if isinstance(raw, bytes):
            node.get_logger().warning("忽略服务器二进制消息")
            continue
        try:
            frame = json.loads(raw)
        except json.JSONDecodeError as error:
            node.get_logger().warning(f"忽略无效 JSON 消息: {error}")
            continue
        try:
            pong = build_pong_frame(frame)
        except ProtocolError as error:
            if isinstance(frame, dict) and frame.get("type") == "control":
                node.get_logger().warning(
                    "收到 control 指令；本包只上报状态，控制由 recv_from_server 链路承担",
                    throttle_duration_sec=10.0,
                )
            else:
                node.get_logger().debug(f"忽略服务器消息: {error}")
            continue
        await websocket.send(json.dumps(pong, separators=(",", ":")))
        node.get_logger().debug(f"ping -> pong, timestamp={pong['timestamp']}")


async def serve_connection(websocket: Any, node: SendToServerNode) -> None:
    """Run the sender and the ping responder until the connection drops."""
    tasks = [
        asyncio.create_task(answer_pings(websocket, node)),
        asyncio.create_task(stream_status(websocket, node)),
    ]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    for task in done:
        task.result()


async def websocket_loop(node: SendToServerNode) -> None:
    """Keep the push connection alive and reconnect after failures."""
    while rclpy.ok():
        try:
            node.get_logger().info(f"连接 {node.server_uri}")
            async with websockets.connect(
                node.server_uri,
                open_timeout=10,
                ping_interval=20,
                ping_timeout=10,
                max_size=1024 * 1024,
            ) as websocket:
                node.get_logger().info("服务器连接成功")
                await serve_connection(websocket, node)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            node.get_logger().warning(f"连接断开: {type(error).__name__}: {error}")
        if rclpy.ok():
            await asyncio.sleep(node.reconnect_delay)


async def run() -> None:
    """Run ROS callbacks and the reconnecting WebSocket pusher."""
    node = SendToServerNode()
    try:
        await asyncio.gather(spin_ros(node), websocket_loop(node))
    finally:
        node.get_logger().info("已停止状态上报")
        node.destroy_node()


def main(args=None) -> None:
    """Run the pusher until interrupted."""
    rclpy.init(args=args)
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()
