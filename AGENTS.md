# AGENTS.md

本文档适用于整个 `/home/yilong/roscar_ws` 工作区，供后续自动化代理和开发者使用。快速入口见 `CLAUDE.md`。

## 工程定位

- 当前环境为树莓派 5（本机，RPi OS）上的 ROS 2 Jazzy，Python 版本为 3.12；同一工作区也可在 PC 上使用（`profile:=pc`）。
- 这是一个 ROS 2 工作区，不是单一软件包。源码位于 `src/`。
- 当前包含以下分层软件包：
  - `src/dm_imu`：达妙科技 DM-IMU-L1 的 Python/pyserial 驱动，构建类型为 `ament_python`。
  - `src/ldlidar_stl_ros2`：LDROBOT LD06/LD19/STL27L 雷达驱动，构建类型为 `ament_cmake`。
  - `src/realsense_r200_ros2`：Intel RealSense R200 相机驱动，构建类型为 `ament_cmake`，依赖系统级手工安装的 librealsense-r200 SDK。
  - `src/recv_from_server`：接收 WebSocket 中继下发的远程 `geometry_msgs/Twist` 遥控指令。
  - `src/roscar_base`：C30D 三轮全向底盘驱动和独立轮式里程计。
  - `src/roscar_description`：机器人 Xacro 和全部传感器静态 TF。
  - `src/roscar_slam`：Cartographer 建图、纯定位和地图保存。
  - `src/roscar_navigation`：Nav2 全向导航配置。
  - `src/roscar_bringup`：PC/RPi5 平台参数与组合启动。
  - `src/roscar_maps`：实机确认后的地图（2026-08-29 已移至工作区根目录 `roscar_maps/`）；`src/roscar_exploration` 仅为预留接口。
- 根目录是 Git 仓库（main 分支）；`build/`、`install/`、`log/` 等生成目录已被 `.gitignore` 忽略。

## 权威资料

- DM-IMU 通信协议以 `doc/达妙科技DM-IMU-L1六轴IMU模块使用说明书V1.2.pdf` 为准。
- LD LiDAR 通信和设备参数以 `doc/LD06（19）激光雷达开发手册_v2.5.pdf` 为准。
- 若源码、旧工程和 PDF 冲突，先按 PDF 核对协议，再结合实际设备输出判断；不要直接照搬旧实现。
- 旧开发机上曾存在 `/home/relog/roscar_old/roscar/src/dm_imu`（树莓派 5 上勉强运行的历史版本），仅供理解背景或对照功能；该路径在当前机器上不存在，不能作为当前实现的权威来源。
- 串口按平台由 profile 决定：PC 走 USB（IMU `/dev/ttyACM0`）；树莓派 5 走排针 UART（IMU `/dev/ttyAMA4`，即 uart4、GPIO12/13、物理 32/33 脚）。不要把某一平台的设备名硬编码进通用默认值，也不要为了与旧工程一致而修改 profile。

## 目录约束

- 只在 `src/` 中修改包源码，在 `doc/` 中维护人工文档。
- `build/`、`install/` 和 `log/` 是 colcon 生成目录，不要手工编辑其中的文件，也不要把其中内容复制回 `src/`。
- 不要在任何 `src/<package>/` 中留下 `build/`、`install/`、`log/`、`.git/`、`__pycache__/`、`*.pyc` 或 `*.egg-info`。
- 不要修改 PDF 手册，除非用户明确要求替换文档。
- 保留厂商代码的许可和版权信息。对 `ldlidar_stl_ros2/ldlidar_driver` 做改动时尽量小而明确。

## 环境和依赖

每个新终端先加载 Jazzy：

```bash
source /opt/ros/jazzy/setup.bash
```

构建后再加载工作区：

```bash
source /home/yilong/roscar_ws/install/local_setup.bash
```

Python 串口依赖应优先由系统包提供：

```bash
sudo apt install python3-serial
```

不要默认使用 `pip` 覆盖 ROS/Ubuntu 管理的 Python 包。新增 ROS 运行依赖时同步更新对应的 `package.xml`；新增 Python 包或数据文件时同步检查 `setup.py`。

## 构建命令

完整构建：

```bash
cd /home/yilong/roscar_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
```

只构建一个包：

```bash
colcon build --symlink-install --packages-select dm_imu
colcon build --symlink-install --packages-select ldlidar_stl_ros2
```

修改 Python 源码后仍应至少执行对应包构建，以验证安装元数据和入口点。不要以直接从 `src/` 导入成功代替 colcon 构建。

## 测试和验证

通用验证顺序：

1. 对改动文件做语法或静态检查。
2. 构建受影响的包。
3. 运行该包现有测试。
4. 解析 launch 文件或执行 `ros2 launch ... --show-args`。
5. 有对应硬件时再进行设备测试。

常用命令：

```bash
source /opt/ros/jazzy/setup.bash
source /home/yilong/roscar_ws/install/local_setup.bash
colcon test --packages-select roscar_base roscar_bringup
colcon test --packages-select dm_imu ldlidar_stl_ros2
colcon test-result --verbose
```

当前回归基线（2026-09-04）：

- Jazzy 依赖与 librealsense-r200 SDK 安装完成后，工作区 10 个包（含
  `recv_from_server`、`realsense_r200_ros2`）可用 `--symlink-install` 完整构建。
- `roscar_base` 有 9 个协议、里程计和安全测试；`roscar_bringup` 有 12 个平台配置与
  架构约束测试；`realsense_r200_ros2` 有 4 个 launch/配置断言测试。当前全部通过；
  相机链路已于 2026-09-04 实机验证（见下）。
- 当前 22 个 `*.launch.py` 均通过 `ros2 launch <包> <入口> --show-args`。
- 三份 Cartographer Lua 配置均已实际启动并成功添加 trajectory；Nav2 已在合成地图和
  合成 TF 下完成生命周期激活。这只证明软件编排可运行，不代表实机定位和导航通过。
- `roscar_description` 已实际确认发布 `base_footprint -> base_link`、
  `base_link -> imu_link` 和 `base_link -> base_laser`；雷达初始高度为 `0.18 m`。

实机进展（2026-08-29，树莓派 5）：

- LD06 经排针 uart0（`/dev/ttyAMA0`，GPIO14/15，物理 8/10 脚，230400 波特率）实测
  正常：`/scan` 稳定 10 Hz、完整 360°、含有效距离值。
- uart4（`/dev/ttyAMA4`，GPIO12/13，物理 32/33 脚）已由 `dtoverlay=uart4-pi5` 启用，
  内核控制台未占用串口；IMU 数据链路尚未实测。

实机进展（2026-09-04，树莓派 5）：

- R200 相机经 USB 3.0（实测 5000M）验证正常：序列号 2211006613（已写入
  `rpi5.yaml`），`use_presets: true` 的 best_quality 预设实测三路 60 Hz（彩色
  rgb8 640×480、深度 16UC1、红外 mono8），camera_info 为相机 SPI 标定值，
  `r200_link -> r200_*_optical_frame` 外参由节点正常发布；整机
  `hardware.launch.py use_camera:=true` 下 profile 的 camera 段覆盖生效
  （红外 2 与点云按配置关闭）。相机安装位姿仍为占位值。
- udev 权限依赖 video 组；`usermod` 后未重新登录的存量会话可用
  `sg video -c "bash -c '...'"` 过渡（sg 会清环境变量，须在其内部重新 source）。

注意：

- `dm_imu` 目前有节点发布与 launch 转发测试（`test/test_node.py`、`test/test_launch.py`），但 `dm_serial` 协议解析仍无自动化测试。协议解析改动必须增加或运行合成字节流测试，至少覆盖分包、粘包、噪声、坏 CRC、未知 RID 和所有有效 RID。
- `ldlidar_stl_ros2` 是厂商旧代码，现有 ament lint 可能因原始格式、版权检测或网络不可用的 XML schema 检查而失败。必须区分编译失败、行为测试失败和既有 lint 失败，不要用一句“测试失败”混为一谈。
- 当前已知 LiDAR 厂商代码失败项是 `copyright`、`cpplint`、`lint_cmake` 和
  `uncrustify`；其编译、`cppcheck`、`flake8`、`pep257` 和 `xmllint` 已通过。不要仅为
  消除这些既有格式告警而批量改写厂商 SDK。
- 没有连接硬件时，可以验证构建、导入、协议解析和 launch 加载，但必须明确说明“未进行硬件实测”。
- 不要为了让测试表面通过而禁用测试、吞掉异常或放宽协议校验。

## DM-IMU 协议约束

USB 主动输出帧为小端序：

```text
55 AA device_id RID payload CRC16(LE) 0A
```

当前手册定义：

- RID `0x01`：三轴加速度，3 个 `float32`，总帧长 19 字节。
- RID `0x02`：三轴角速度，3 个 `float32`，总帧长 19 字节。
- RID `0x03`：Roll/Pitch/Yaw，3 个 `float32`，单位为度，总帧长 19 字节。
- RID `0x04`：四元数 `W/X/Y/Z`，4 个 `float32`，总帧长 23 字节。

实现要求：

- 必须依据 RID 决定帧长，不能将所有帧固定为 19 字节。
- 必须按 RID 分别缓存数据，不能把“最后收到的一帧”直接当作欧拉角。
- 协议四元数顺序是 `W, X, Y, Z`，ROS 消息顺序是 `X, Y, Z, W`。
- 设备可能关闭任意一种输出，节点必须允许部分数据缺失，并按 ROS 约定设置相应 covariance 的首项为 `-1.0`。
- 修改 CRC 行为前必须以手册附录、实际帧样本和合成测试共同确认。
- `sensor_msgs/msg/Imu` 要求角速度使用 rad/s、线加速度使用 m/s^2。V1.2 手册的 USB
  章节说明设备直接发送校准后的原始小端 `float`；附录二给出的映射范围为加速度
  `±235.2`、角速度 `±34.88`，分别对应 `m/s^2` 和 `rad/s`。因此当前 USB 数据已经符合
  ROS SI 约定，`linear_acceleration_scale` 与 `angular_velocity_scale` 默认都必须为
  `1.0`，不要再乘 `9.80665` 或 `pi/180`。手册参数页的加速度量程 `±6G` 与附录协议
  映射上限并不相同；前者是设备指标，后者是传输映射范围，不能据此把 USB float 当成
  `g`。
- 设备输出四元数可用时优先使用设备四元数；缺失时才由欧拉角计算。
- 串口读取运行在后台线程，缓存访问必须保持线程安全；关闭节点时必须停止线程并关闭串口。

关键实现文件：

- `src/dm_imu/dm_imu/modules/dm_serial.py`：串口生命周期、缓冲区、协议解析和按 RID 缓存。
- `src/dm_imu/dm_imu/modules/dm_crc.py`：CRC16。
- `src/dm_imu/dm_imu/node.py`：ROS 参数、QoS 和消息发布。
- `src/dm_imu/config/params.yaml`：默认运行参数。
- `src/dm_imu/launch/dm_imu.launch.py`：无 RViz 启动入口。

## DM-IMU 运行约定

PC（USB）与树莓派 5（排针 uart4）分别启动：

```bash
source /opt/ros/jazzy/setup.bash
source /home/yilong/roscar_ws/install/local_setup.bash
ros2 launch dm_imu dm_imu.launch.py port:=/dev/ttyACM0   # PC
ros2 launch dm_imu dm_imu.launch.py port:=/dev/ttyAMA4   # 树莓派 5
```

如果 `/dev/serial/by-id/` 存在稳定链接，人工运行时优先传入该链接。不要把某一台设备的完整 by-id 字符串硬编码进通用配置。

串口通常属于 `root:dialout` 且权限为 `0660`。出现 `Permission denied` 时应将用户加入 `dialout` 并重新登录或使用 `newgrp dialout`；不要把 `sudo chmod 666 /dev/ttyACM0` 作为持久修复方案，也不要用 root 启动 ROS 节点规避权限问题。

主要话题：

- `/imu/data`：`sensor_msgs/msg/Imu`
- `/imu/rpy`：`geometry_msgs/msg/Vector3Stamped`
- `/imu/pose`：`geometry_msgs/msg/PoseStamped`

## LiDAR 约束

- 默认 LD06/LD19 串口为 `/dev/ttyUSB0`，波特率为 230400；STL27L 默认为 921600。
- 雷达节点发布 `/scan`，默认 frame 为 `base_laser`。
- 单独运行厂商 viewer 时可启用驱动 launch 的兼容 TF；整机启动时静态变换只能由 `roscar_description` 发布。
- 修改扫描角度、方向、裁剪或距离范围时，先核对设备型号和 PDF 手册。
- `ldlidar_driver` 是随 ROS 包带入的厂商 SDK。优先在 ROS 适配层修复问题；只有底层编译或协议问题确实位于 SDK 时才修改 SDK。

## R200 相机约束

- 驱动源码在 `src/realsense_r200_ros2`（ament_cmake），依赖 librealsense-r200 SDK
  （`~/src/r200_ubuntu24.04`，librealsense v1.12.1 的 R200 专用裁剪版，USB
  VID:PID `8086:0a80`）。SDK 以 Release 构建安装到 `/usr/local`（含 cmake CONFIG
  包与 udev 规则），`build/` 内的 Debug 产物仅供调试。安装步骤见 README。
- `librealsense-r200` 不是 rosdep key，不写进任何 package.xml；PC 复用工作区前需
  先安装同一 SDK。
- R200 是 USB 3.0 设备，必须接树莓派 5 的 USB 3.0 口；点云由 CPU 计算，两平台
  profile 默认 `publish_pointcloud: false`，需要时改 `camera:` 段。
- `use_presets: true` 时 SDK 的 best_quality 预设实测为三路 60 Hz，忽略 YAML 里的
  `*_fps` 字段；要限定帧率须 `use_presets: false` 后用 YAML 分辨率/帧率。
- 用户需在 `video` 组（udev 规则 GROUP=video；`TAG+=uaccess` 对 SSH 会话无效）。
- `hardware.launch.py` 的 `use_camera` 默认 `false`：无相机时 `r200_node` 构造即抛
  异常并以 `EXIT_FAILURE` 退出（不影响 launch 其他节点）。不要给该节点加
  `respawn=True`，否则无相机会变成崩溃循环。
- `base_link -> r200_link` 出自 URDF（当前为占位值，装车后实测改 profile）；
  `r200_link -> r200_*_optical_frame` 是相机 SPI 标定外参，由 `r200_node` 发布，
  禁止写进 URDF。

## 代码风格和改动范围

- Python 遵循现有 PEP 8 风格，使用明确类型和小型函数；涉及协议偏移、单位或字节顺序时写简短注释。
- C/C++ 延续包内现有风格。不要为了单个功能改动格式化整个厂商 SDK。
- 参数默认值应在 `node.py`、YAML 和 launch 参数之间保持一致。
- 新增 launch、config 或 RViz 文件时，确保它们被 `setup.py` 或 `CMakeLists.txt` 安装。
- 保持改动聚焦，不顺带重写厂商代码、生成目录或编辑器数据库。

## 整机架构约束

- TF 固定为 `map -> odom -> base_footprint -> base_link -> {imu_link, base_laser, r200_link}`。
  `r200_link -> r200_*_optical_frame` 由 `r200_node` 从相机外参发布，是整机静态 TF
  只出自 `roscar_description` 这一约定的唯一例外。
- `roscar_base` 必须从 STM32 上报的机体速度独立积分位姿并发布 `/odom` 和
  `odom -> base_footprint`，禁止从 Cartographer TF 读取位姿拼装 `/odom`。
- 使用轮式里程计时 Cartographer 配置为 `published_frame = "odom"`、
  `provide_odom_frame = false`、`use_odometry = true`，只发布 `map -> odom`。
- Nav2 控制器必须支持 `vx/vy/wz` 全向运动；不要恢复旧工程的差速或
  REEDS_SHEPP 配置。
- `roscar_navigation` 包含 Jazzy 特有兼容约束：传给上游
  `nav2_bringup/navigation_launch.py` 的 `use_composition` 必须是 Python 字面量字符串
  `"False"`，不能写成 ROS 常用的小写 `"false"`。Jazzy 上游会将它放入
  `PythonExpression` 求值；修改此处必须保留对应架构回归测试。
- Nav2 与遥控速度先进入 `twist_mux`，最终 `/cmd_vel` 才交给底盘。底盘节点自身仍须
  保留超时清零和退出前停车。
- 自动探索当前未实现，禁止把空包描述为可用功能，也不要直接复制旧 `explore_lite`。
  Jazzy 的 `launch.actions` 没有 `LogError`；当前探索入口通过 `OpaqueFunction` 调用
  `launch.logging` 记录错误，再主动发送 `Shutdown`。入口应继续明确拒绝启动，而不是
  静默退出或伪装成功。
- 地图先保存到显式指定的可写目录；只有确认后的 `.yaml`、图像和 `.pbstream` 成套
  文件才能放入 `src/roscar_maps/maps`。

## 交付要求

完成修改后应说明：

- 修改了哪些包和行为。
- 执行了哪些构建、测试或 launch 检查。
- 是否进行了真实硬件测试。
- 若未测试硬件，剩余风险具体是什么，例如串口权限、输出 RID、频率、坐标轴方向或物理单位。

不要把“能够编译”描述为“硬件驱动已经验证可用”。

截至 2026-08-24，仍待实机验收的项目包括：IMU 轴向与安装变换、真实雷达扫描方向、
底盘前进/横移/旋转与里程计方向、闭环建图、重定位、全向路径跟踪，以及拔掉底盘串口
后的安全停车。后续若完成其中任一项，应记录测试条件和结果，并更新这份清单。
