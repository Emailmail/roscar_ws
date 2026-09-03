# roscar_base

C30D 底盘驱动包:与 STM32 上的 C30D 底盘驱动器通过串口通信,下发速度指令、
上报遥测并独立发布轮式里程计。

## 节点

`c30d_driver`(可执行文件 `roscar_base/c30d_driver`,纯 Python)

### 订阅

| 话题 | 类型 | 说明 |
|---|---|---|
| `cmd_vel`(参数 `cmd_vel_topic` 可改) | `geometry_msgs/msg/Twist` | 机体坐标系速度指令,上游应为 `twist_mux` 汇总输出 |

### 发布

| 话题 | 类型 | 说明 |
|---|---|---|
| `odom` | `nav_msgs/msg/Odometry` | 由 C30D 上报的机体速度自积分得到 |
| TF `odom -> base_footprint` | — | 与 `/odom` 同步发布,`publish_tf: false` 可关闭 |

按整机约定,轮式里程计独立于 Cartographer:本包从 STM32 遥测自积分发布
`/odom` 和 `odom -> base_footprint`,Cartographer 只发布 `map -> odom`。
禁止从 Cartographer TF 反造 `/odom`。

## 参数

完整默认值见 [config/c30d.yaml](config/c30d.yaml),`port` 可被 launch 参数
`base_port` / profile(`roscar_bringup` 的 `config/{pc,rpi5}.yaml`)覆盖。

| 参数 | 默认值 | 说明 |
|---|---|---|
| `port` | `/dev/ttyACM0` | C30D 串口设备(RPi5 实测为 USB `/dev/ttyACM0`) |
| `baudrate` | `115200` | 串口波特率 |
| `send_rate` | `50.0` | 速度指令下发频率 Hz |
| `telemetry_rate` | `20.0` | 遥测帧期望频率 Hz,用于批量解帧的时间戳摊算 |
| `cmd_timeout` | `0.3` | 速度指令超时秒数,超时后清零停车 |
| `reconnect_interval` | `2.0` | 串口打开失败后的重试间隔秒数 |
| `max_linear_speed` | `0.5` | 线速度限幅 m/s |
| `max_angular_speed` | `1.5` | 角速度限幅 rad/s |
| `odom_frame` | `odom` | 里程计父坐标系 |
| `base_frame` | `base_footprint` | 里程计子坐标系 |
| `cmd_vel_topic` | `cmd_vel` | 速度指令订阅话题;如遥控链路直连底盘可改为 `/cmdvel_remote` |
| `publish_tf` | `true` | 是否发布 `odom -> base_footprint` |

示例(不改 twist_mux,直接订阅遥控话题):

```bash
ros2 run roscar_base c30d_driver --ros-args -p cmd_vel_topic:=/cmdvel_remote
```

## C30D 串口协议

实现见 [roscar_base/protocol.py](roscar_base/protocol.py),无 ROS / 串口依赖,可离线测试。

- 帧头 `0x7B`,帧尾 `0x7D`,校验为除帧尾外字节的 XOR;多字节字段为**大端**。
- 下行(主机 → C30D)11 字节:命令字节 + 保留 + `int16` ×3
  (vx、vy、wz,缩放 1000,即 mm/s、mrad/s)+ 校验。
- 上行(C30D → 主机)24 字节:急停标志 + `int16` ×9(vx、vy、wz、加速度 ×3、
  陀螺仪 ×3、电压,缩放 1000)+ 校验。
- 解析器容忍分包、粘包、噪声前导和坏帧(丢弃后从下一个 `0x7B` 重新同步)。

## 安全链

- 速度指令超过 `cmd_timeout` 未更新 → 自动清零下发。
- 所有指令经 `max_linear_speed` / `max_angular_speed` 限幅。
- 节点退出时先下发零速再关闭串口。
- 串口异常自动断开重连;重连后要求收到新指令才会再次运动。

## 构建 / 测试 / 启动

```bash
cd ~/roscar_ws
colcon build --symlink-install --packages-select roscar_base
colcon test --packages-select roscar_base && colcon test-result --verbose
python3 -m pytest src/roscar_base/test -q          # 快速单跑

source install/local_setup.bash
ros2 launch roscar_bringup hardware.launch.py profile:=rpi5   # 整机
ros2 launch roscar_base base.launch.py port:=/dev/ttyACM0     # 单包
```

测试覆盖协议编解码、里程计积分和限速逻辑(合成字节流,无需硬件)。

## 硬件状态

截至 2026-08-29,C30D 底盘(USB `/dev/ttyACM0`)**未实测**:本包仅有离线
协议/逻辑测试,帧格式未经真机确认。实机联调前请先用
`ros2 topic echo /odom` 和低速指令验证。
