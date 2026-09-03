# ROSCar

ROS 2 Jazzy 三轮全向轮机器人工作区。工程将硬件驱动、机器人模型、SLAM、导航、
自动探索预留接口和整机启动分层管理。

## 软件包

| 包 | 职责 |
|---|---|
| `dm_imu` | DM-IMU-L1 串口驱动，发布 `/imu/data`、`/imu/accel`、`/imu/gyro`、`/imu/rpy` 和 `/imu/pose` |
| `ldlidar_stl_ros2` | LD06/LD19/STL27L 驱动，发布 `/scan` |
| `roscar_base` | C30D 协议、全向底盘控制、独立 `/odom` |
| `roscar_description` | Xacro 模型以及唯一的传感器静态 TF |
| `roscar_slam` | Cartographer 建图、纯定位和地图保存 |
| `roscar_navigation` | Nav2 全向规划、MPPI 控制和速度安全链路 |
| `roscar_bringup` | PC/RPi5 参数与整机启动入口 |
| `roscar_maps` | 经过实机确认的地图集合 |
| `roscar_exploration` | 自动探索预留接口，当前未实现 |

TF 约定：

```text
map -> odom -> base_footprint -> base_link
                                  |-> imu_link
                                  `-> base_laser
```

底盘发布 `odom -> base_footprint`；使用轮式里程计时 Cartographer 只发布
`map -> odom`。不要重新加入旧工程中“从 Cartographer TF 反造 `/odom`”的逻辑。

## 安装依赖与构建

```bash
sudo apt update
sudo apt install \
  ros-jazzy-cartographer-ros \
  ros-jazzy-navigation2 \
  ros-jazzy-nav2-bringup \
  ros-jazzy-robot-state-publisher \
  ros-jazzy-teleop-twist-keyboard \
  ros-jazzy-twist-mux \
  ros-jazzy-xacro \
  python3-serial python3-yaml

cd ~/roscar_ws
source /opt/ros/jazzy/setup.bash
# 首次使用 rosdep 的系统需先执行：sudo rosdep init && rosdep update
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/local_setup.bash
```

## 启动入口

只启动硬件和机器人模型：

```bash
ros2 launch roscar_bringup hardware.launch.py profile:=pc
```

PC 上无底盘手推建图：

```bash
ros2 launch roscar_bringup mapping.launch.py \
  profile:=pc use_base:=false
```

树莓派整车建图：

```bash
ros2 launch roscar_bringup mapping.launch.py profile:=rpi5 use_base:=false
```

地图统一保存在 `~/roscar_ws/roscar_maps/maps/`，navigation 默认读取该目录，
保存后即可直接启动，无需复制或重建：

```bash
mkdir -p ~/roscar_ws/roscar_maps/maps
ros2 launch roscar_slam save_map.launch.py \
  map_dir:=~/roscar_ws/roscar_maps/maps/ map_name:=my_map
```

定位与导航（无底盘加 `use_base:=false`：Cartographer 接管
`odom -> base_footprint`，Nav2 可完整启动，但 `/cmd_vel` 无底盘执行）：

```bash
ros2 launch roscar_bringup navigation.launch.py \
  profile:=rpi5 map_name:=my_map use_base:=false use_rviz:=false
```

参数 `imu_port`、`lidar_port` 和 `base_port` 均可覆盖平台配置。PC 默认 IMU 为
`/dev/ttyACM0`、雷达为 `/dev/ttyUSB0`、底盘为 `/dev/ttyACM1`；RPi5 默认值分别为
`/dev/ttyAMA4`、`/dev/ttyAMA0` 和 `/dev/ttyACM0`。

单独检查 IMU 和 RViz：

```bash
ros2 launch dm_imu dm_imu_rviz.launch.py port:=/dev/ttyACM0
```

该入口默认发布仅用于独立查看的 `base_link -> imu_link` 兼容 TF。已启动
`roscar_description` 时必须传入 `publish_tf:=false`，避免重复发布静态 TF。

## 当前限制

- 自动探索尚未实现，`use_exploration:=true` 会明确停止启动，避免误认为可用。
- DM-IMU V1.2 手册附录给出的 `±34.88` 和 `±235.2` 范围表明 USB 原始 float 分别为
  rad/s 和 m/s²，当前 `/imu/data`、`/imu/gyro` 和 `/imu/accel` 不做额外缩放；
  正式建图前仍需用静置重力和定轴旋转检查实际输出及轴向是否符合 REP-103。
- 底盘 `wz` 上行字段按旧协议的 `/1000` 比例解释为 rad/s，需用原地旋转实测校准。
- `roscar_description` 中雷达高度暂取 0.18 m，IMU 位姿暂取单位变换，安装后应测量。

## 验证

```bash
source /opt/ros/jazzy/setup.bash
source install/local_setup.bash
colcon test --packages-select roscar_base roscar_bringup
colcon test-result --verbose
```

没有实机时只能验证协议、构建、配置和 launch 加载；不能据此认定传感器轴向、单位、
定位精度或底盘安全停车已经通过实机验证。
