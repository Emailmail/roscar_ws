# AGENTS.md

本文档适用于整个 `/home/relog/roscar_ws` 工作区，供后续自动化代理和开发者使用。

## 工程定位

- 当前环境为 Ubuntu 上的 ROS 2 Jazzy，Python 版本为 3.12。
- 这是一个 ROS 2 工作区，不是单一软件包。源码位于 `src/`。
- 当前包含两个硬件驱动包：
  - `src/dm_imu`：达妙科技 DM-IMU-L1 的 Python/pyserial 驱动，构建类型为 `ament_python`。
  - `src/ldlidar_stl_ros2`：LDROBOT LD06/LD19/STL27L 雷达驱动，构建类型为 `ament_cmake`。
- 根目录当前不一定是 Git 仓库。执行 Git 操作前先用 `git rev-parse --show-toplevel` 确认，不要假定版本控制可用。

## 权威资料

- DM-IMU 通信协议以 `doc/达妙科技DM-IMU-L1六轴IMU模块使用说明书V1.2.pdf` 为准。
- LD LiDAR 通信和设备参数以 `doc/LD06（19）激光雷达开发手册_v2.5.pdf` 为准。
- 若源码、旧工程和 PDF 冲突，先按 PDF 核对协议，再结合实际设备输出判断；不要直接照搬旧实现。
- `/home/relog/roscar_old/roscar/src/dm_imu` 是树莓派 5 上经过多轮修改后勉强运行的历史版本，只能用于理解背景或对照功能，不能作为当前实现的权威来源。
- 历史工程使用 `/dev/ttyAMA4`，因为它运行在树莓派 5；当前 PC 通过 USB 使用 `/dev/ttyACM0`。不要为了与旧工程一致而修改当前默认串口。

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
source /home/relog/roscar_ws/install/local_setup.bash
```

Python 串口依赖应优先由系统包提供：

```bash
sudo apt install python3-serial
```

不要默认使用 `pip` 覆盖 ROS/Ubuntu 管理的 Python 包。新增 ROS 运行依赖时同步更新对应的 `package.xml`；新增 Python 包或数据文件时同步检查 `setup.py`。

## 构建命令

完整构建：

```bash
cd /home/relog/roscar_ws
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
colcon test --packages-select dm_imu
colcon test --packages-select ldlidar_stl_ros2
colcon test-result --verbose
```

注意：

- `dm_imu` 当前没有完整的自动化测试套件。协议解析改动必须增加或运行合成字节流测试，至少覆盖分包、粘包、噪声、坏 CRC、未知 RID 和所有有效 RID。
- `ldlidar_stl_ros2` 是厂商旧代码，现有 ament lint 可能因原始格式、版权检测或网络不可用的 XML schema 检查而失败。必须区分编译失败、行为测试失败和既有 lint 失败，不要用一句“测试失败”混为一谈。
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
- `sensor_msgs/msg/Imu` 要求角速度使用 rad/s、线加速度使用 m/s^2。若设备 USB 输出单位尚未由手册或实测明确，不能擅自添加转换，也不能声称已经符合 SI；应在代码或交付说明中明确这一待确认项。
- 设备输出四元数可用时优先使用设备四元数；缺失时才由欧拉角计算。
- 串口读取运行在后台线程，缓存访问必须保持线程安全；关闭节点时必须停止线程并关闭串口。

关键实现文件：

- `src/dm_imu/dm_imu/modules/dm_serial.py`：串口生命周期、缓冲区、协议解析和按 RID 缓存。
- `src/dm_imu/dm_imu/modules/dm_crc.py`：CRC16。
- `src/dm_imu/dm_imu/node.py`：ROS 参数、QoS 和消息发布。
- `src/dm_imu/config/params.yaml`：默认运行参数。
- `src/dm_imu/launch/dm_imu.launch.py`：无 RViz 启动入口。

## DM-IMU 运行约定

PC 上默认启动：

```bash
source /opt/ros/jazzy/setup.bash
source /home/relog/roscar_ws/install/local_setup.bash
ros2 launch dm_imu dm_imu.launch.py port:=/dev/ttyACM0
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
- launch 文件还发布 `base_link -> base_laser` 静态变换。修改安装位置时应更新变换参数，不要只改 RViz。
- 修改扫描角度、方向、裁剪或距离范围时，先核对设备型号和 PDF 手册。
- `ldlidar_driver` 是随 ROS 包带入的厂商 SDK。优先在 ROS 适配层修复问题；只有底层编译或协议问题确实位于 SDK 时才修改 SDK。

## 代码风格和改动范围

- Python 遵循现有 PEP 8 风格，使用明确类型和小型函数；涉及协议偏移、单位或字节顺序时写简短注释。
- C/C++ 延续包内现有风格。不要为了单个功能改动格式化整个厂商 SDK。
- 参数默认值应在 `node.py`、YAML 和 launch 参数之间保持一致。
- 新增 launch、config 或 RViz 文件时，确保它们被 `setup.py` 或 `CMakeLists.txt` 安装。
- 保持改动聚焦，不顺带重写厂商代码、生成目录或编辑器数据库。

## 交付要求

完成修改后应说明：

- 修改了哪些包和行为。
- 执行了哪些构建、测试或 launch 检查。
- 是否进行了真实硬件测试。
- 若未测试硬件，剩余风险具体是什么，例如串口权限、输出 RID、频率、坐标轴方向或物理单位。

不要把“能够编译”描述为“硬件驱动已经验证可用”。
