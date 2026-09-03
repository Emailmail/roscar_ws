# recv_from_server

`recv_from_server` 是树莓派 5 上运行的 ROS 2 Jazzy 接收端。它连接云服务器
`8771` 端口，接收 PC 端 `send2server` 发来的 `geometry_msgs/msg/Twist` JSON，
校验后恢复为本机 ROS 2 `Twist` 消息。

服务器 JSON 中的 Topic 固定为 `/cmdvel_remote`。本机发布 Topic 通过
`cmd_vel_topic` 参数配置；代码默认值是 `/cmd_vel`，如果底盘接口尚未确认，
建议测试时显式使用 `/cmdvel_remote`，避免把指令直接接入未知底盘接口。

## 一、复制到树莓派 5

在 PC 上执行，将整个包目录复制到树莓派工作区的 `src/` 下：

```bash
scp -r /home/relog/Repo/sbgdut/src/recv_from_server \
  pi@<树莓派IP>:~/ros2_ws/src/
```

如果使用 U 盘或其他方式复制，最终目录结构必须是：

```text
~/ros2_ws/src/recv_from_server/package.xml
~/ros2_ws/src/recv_from_server/setup.py
```

下面命令中的 `~/ros2_ws` 替换为树莓派上实际的 ROS 2 工作区路径。

## 二、安装依赖

树莓派上执行：

```bash
sudo apt update
sudo apt install -y python3-colcon-common-extensions python3-websockets \
  ros-jazzy-ros-base ros-jazzy-geometry-msgs
```

确认 ROS 发行版和 Python WebSocket 库：

```bash
source /opt/ros/jazzy/setup.bash
echo "$ROS_DISTRO"
python3 -c 'import rclpy, websockets; print(websockets.__version__)'
```

`ROS_DISTRO` 应输出 `jazzy`。

## 三、构建接收包

树莓派上执行：

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select recv_from_server
source install/setup.bash
```

确认包已被 ROS 2 找到：

```bash
ros2 pkg prefix recv_from_server
ros2 launch recv_from_server recv_from_server.launch.py --show-args
```

## 四、启动接收服务

### 方案 A：恢复到 `/cmdvel_remote`（建议先用这个测试）

该命令不改变 Topic 名称，只验证服务器转发和树莓派接收解析：

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch recv_from_server recv_from_server.launch.py \
  server_uri:=ws://8.134.118.29:8771 \
  remote_topic:=/cmdvel_remote \
  cmd_vel_topic:=/cmdvel_remote
```

看到以下日志表示 WebSocket 已连接：

```text
服务器连接成功
```

### 方案 B：发布到实际底盘控制 Topic

只有确认底盘驱动订阅的 Topic 后才使用。例如底盘订阅 `/cmd_vel`：

```bash
ros2 launch recv_from_server recv_from_server.launch.py \
  server_uri:=ws://8.134.118.29:8771 \
  cmd_vel_topic:=/cmd_vel
```

也可以使用其他控制 Topic：

```bash
ros2 run recv_from_server recv_node --ros-args \
  -p cmd_vel_topic:=/cmdvel_remote \
  -p server_uri:=ws://8.134.118.29:8771
```

## 五、查看树莓派恢复的速度

如果按方案 A 启动：

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 topic echo /cmdvel_remote geometry_msgs/msg/Twist
```

如果按方案 B 启动，则将 Topic 换成实际的 `cmd_vel_topic`，例如：

```bash
ros2 topic echo /cmd_vel geometry_msgs/msg/Twist
```

检查节点连接和发布关系：

```bash
ros2 node info /recv_from_server
ros2 topic info /cmdvel_remote
```

## 六、PC 端发送测试指令

在 PC 端启动 `send2server`，并确认它连接服务器 `8770`：

```bash
cd /home/relog/ros2_controller
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch send2server send2server.launch.py \
  server_uri:=ws://8.134.118.29:8770
```

PC 另开一个终端发布一条测试 Twist：

```bash
source /opt/ros/jazzy/setup.bash
ros2 topic pub --once /cmdvel_remote geometry_msgs/msg/Twist \
  "{linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.1}}"
```

树莓派的 `ros2 topic echo` 应显示相同的六个分量。测试期间不要连接真实底盘，
或先抬起驱动轮并准备急停。

## 七、参数和安全行为

```text
server_uri       默认 ws://8.134.118.29:8771
remote_topic     默认 /cmdvel_remote
cmd_vel_topic    默认 /cmd_vel
reconnect_delay  默认 2.0 秒
command_timeout  默认 0.5 秒
```

超过 `command_timeout` 没有收到有效指令，或者 WebSocket 断开时，节点会发布零速度。
只有在下游控制器已经实现独立超时保护时，才建议设置：

```bash
ros2 launch recv_from_server recv_from_server.launch.py command_timeout:=0.0
```

停止服务使用 `Ctrl+C`。退出时节点同样会发布一次零速度。

## 八、故障排查

| 现象 | 检查 |
| --- | --- |
| `Package 'recv_from_server' not found` | 重新执行 `source /opt/ros/jazzy/setup.bash` 和 `source ~/ros2_ws/install/setup.bash`，确认包在工作区 `src/` 下后重新构建 |
| 一直没有 `服务器连接成功` | 检查云服务器 relay 是否运行、树莓派网络、服务器地址和端口 `8771` |
| `No module named websockets` | 安装 `python3-websockets`，再执行 `python3 -c 'import websockets'` |
| `ros2 topic echo` 没有输出 | 确认 PC 端 `send2server` 已连接 `8770`，发布的 Topic 是 `/cmdvel_remote`，且接收端 `remote_topic` 一致 |
| 收到后很快变成零速度 | 这是 `command_timeout` 的安全保护，持续发布指令或按实际链路调整超时时间 |
| 连接后出现“忽略无效服务器消息” | 检查发送端是否使用 `geometry_msgs/msg/Twist` 的标准 JSON 格式，不能发送旧的 String/Vector3 帧 |

接收端只接受以下协议帧：`source=pc`、`type=ros_topic`、
`topic=/cmdvel_remote`、`msg_type=geometry_msgs/msg/Twist`。无效 JSON、二进制消息、
错误元数据和非有限数值都会被忽略并记录 warning。
