"""ROS 2 node that receives remote Twist commands over WebSocket."""

import asyncio
import json
import time
from typing import Any

from geometry_msgs.msg import Twist
import rclpy
from rclpy.node import Node
import websockets

from .protocol import DEFAULT_REMOTE_TOPIC, ProtocolError, parse_twist_frame


DEFAULT_SERVER_URI = "ws://8.134.118.29:8771"


class RecvFromServerNode(Node):
    """Decode server frames and publish safe local cmd_vel messages."""

    def __init__(self) -> None:
        super().__init__("recv_from_server")
        self.declare_parameter("server_uri", DEFAULT_SERVER_URI)
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("remote_topic", DEFAULT_REMOTE_TOPIC)
        self.declare_parameter("reconnect_delay", 2.0)
        self.declare_parameter("command_timeout", 0.5)

        self.server_uri = str(self.get_parameter("server_uri").value)
        self.cmd_vel_topic = str(self.get_parameter("cmd_vel_topic").value)
        self.remote_topic = str(self.get_parameter("remote_topic").value)
        self.reconnect_delay = float(self.get_parameter("reconnect_delay").value)
        self.command_timeout = float(self.get_parameter("command_timeout").value)
        if not self.server_uri.startswith(("ws://", "wss://")):
            raise ValueError("server_uri must start with ws:// or wss://")
        if not self.cmd_vel_topic or not self.remote_topic:
            raise ValueError("cmd_vel_topic and remote_topic must not be empty")
        if self.reconnect_delay <= 0:
            raise ValueError("reconnect_delay must be greater than 0")
        if self.command_timeout < 0:
            raise ValueError("command_timeout must be non-negative")

        self.publisher = self.create_publisher(Twist, self.cmd_vel_topic, 10)
        self.last_receive_monotonic: float | None = None
        self._timed_out = False
        self.watchdog = self.create_timer(0.1, self._check_command_timeout)
        self.get_logger().info(
            f"接收 {self.server_uri} 的 {self.remote_topic}，发布到 {self.cmd_vel_topic}"
        )

    def publish_remote(self, frame: Any) -> None:
        """Validate one JSON object, then publish its Twist payload."""
        values = parse_twist_frame(frame, self.remote_topic)
        message = Twist()
        message.linear.x = values["linear.x"]
        message.linear.y = values["linear.y"]
        message.linear.z = values["linear.z"]
        message.angular.x = values["angular.x"]
        message.angular.y = values["angular.y"]
        message.angular.z = values["angular.z"]
        self.publisher.publish(message)
        self.last_receive_monotonic = time.monotonic()
        self._timed_out = False
        self.get_logger().debug(f"JSON -> {self.cmd_vel_topic}, seq={frame['seq']}")

    def publish_stop(self, reason: str) -> None:
        """Publish an explicit zero command when the link is unavailable."""
        self.publisher.publish(Twist())
        self._timed_out = True
        self.get_logger().warning(f"发布零速度 ({reason})")

    def _check_command_timeout(self) -> None:
        if (
            self.command_timeout > 0
            and self.last_receive_monotonic is not None
            and time.monotonic() - self.last_receive_monotonic > self.command_timeout
            and not self._timed_out
        ):
            self.publish_stop("command_timeout")

    def on_disconnect(self) -> None:
        """Stop the local command stream before reconnecting."""
        if self.last_receive_monotonic is not None and not self._timed_out:
            self.publish_stop("websocket_disconnected")


async def spin_ros(node: RecvFromServerNode) -> None:
    """Service ROS callbacks from the asyncio event loop."""
    while rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0)
        await asyncio.sleep(0.01)


async def receive_frames(websocket: Any, node: RecvFromServerNode) -> None:
    """Receive, decode, and publish all text frames from the relay."""
    async for raw in websocket:
        if isinstance(raw, bytes):
            node.get_logger().warning("忽略服务器二进制消息")
            continue
        try:
            node.publish_remote(json.loads(raw))
        except (json.JSONDecodeError, ProtocolError) as error:
            node.get_logger().warning(f"忽略无效服务器消息: {error}")


async def websocket_loop(node: RecvFromServerNode) -> None:
    """Keep the receive connection alive and reconnect after failures."""
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
                await receive_frames(websocket, node)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            node.on_disconnect()
            node.get_logger().warning(
                f"连接断开: {type(error).__name__}: {error}"
            )
        if rclpy.ok():
            await asyncio.sleep(node.reconnect_delay)


async def run() -> None:
    """Run ROS callbacks and the reconnecting WebSocket receiver."""
    node = RecvFromServerNode()
    try:
        await asyncio.gather(spin_ros(node), websocket_loop(node))
    finally:
        node.publish_stop("shutdown")
        node.destroy_node()


def main(args=None) -> None:
    """Run the receiver until interrupted."""
    rclpy.init(args=args)
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()
