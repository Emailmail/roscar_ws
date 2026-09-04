# send2server

`send2server` 是树莓派 5 上运行的 ROS 2 Jazzy 上报端。它作为 WebSocket 客户端连接
云服务器中转，把车辆状态按 `doc/通信格式.md` 的 `status` JSON 推给 Qt 远程驾驶上位机，
并应答上位机的 `ping` 心跳（回 `pong`，用于单向延迟显示）。

两个 launch 入口：

- `status.launch.py`：坐标等数据上报（本包当前唯一实现的功能）。
- `webrtc.launch.py`：视频流经 WebRTC 推送到云端，**已预留但尚未实现**，启动即拒绝退出。

## 数据来源

| 上位机字段 | 来源 |
| --- | --- |
| `x`、`y`、`yaw` | TF `map -> base_footprint`（Cartographer 建图/定位发布）。TF 不可用时跳过上报并每 5 s 警告一次，不发假数据 |
| `speed` | `/odom` 的 `twist.twist.linear.x`（roscar_base 发布的机体前向速度，仅取速度，不取坐标） |
| `battery` | 无车载电压源，固定参数 `battery`（默认 `0.0`） |
| `traffic` | 固定参数 `traffic`（默认 `green`，可选 `red`/`stop`） |

上位机发来的 `control` 指令本包**不处理**（控制链路由 `recv_from_server` 承担），
收到时每 10 s 警告一次；其余未知消息按 debug 忽略。

## 构建与启动

```bash
cd ~/roscar_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select send2server
source install/local_setup.bash

# 默认连 ws://8.134.118.29:8772
ros2 launch send2server status.launch.py

# 覆盖服务器地址或周期
ros2 launch send2server status.launch.py \
  server_uri:=ws://8.134.118.29:8772 status_period:=0.2
```

前置条件：Cartographer 建图或定位已在运行（否则只有心跳、没有位置）；
`roscar_base` 已在发布 `/odom`。

## 参数

```text
server_uri       默认 ws://8.134.118.29:8772（status 推送端口，与 8770/8771 控制链路分离）
map_frame        默认 map
robot_frame      默认 base_footprint
odom_topic       默认 /odom（仅取速度）
status_period    默认 0.1 s（10 Hz 上报）
reconnect_delay  默认 2.0 s
battery          默认 0.0（上报给上位机的固定电压，单位 V）
traffic          默认 green（green / red / stop）
```

## 验证

```bash
# 语法与参数检查
ros2 launch send2server status.launch.py --show-args

# 协议单元测试
python3 -m pytest src/send2server/test -q
```

实机验证要点：启动后看到 `服务器连接成功`；SLAM 运行时上位机轨迹随车移动、
单向延迟有数值（说明 `ping`/`pong` 通）；SLAM 停止时出现周期性 TF 警告且上位机
位置冻结（而不是跳回原点）。

## 故障排查

| 现象 | 检查 |
| --- | --- |
| 一直 `连接 ws://...` 后断开 | 云服务器 8772 端口的 status 中转是否开启、网络与防火墙 |
| 连接正常但上位机无位置 | Cartographer 是否在发布 `map -> odom`；`ros2 run tf2_ros tf2_echo map base_footprint` |
| 上位机速度恒为 0 | `ros2 topic echo /odom --field twist.twist.linear.x` 是否有值 |
| 单向延迟一直 `-- ms` | 中转是否把上位机的 `ping` 转发到本连接（本节点会回 `pong`） |
| 上位机弹交通灯红灯 | `traffic` 参数是否被改过 |
