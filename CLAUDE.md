# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

本仓库的详细工程约束以 [AGENTS.md](AGENTS.md) 为权威来源,修改驱动协议、TF 架构或导航配置前先读它。要点:

- 工作区根目录是 `/home/yilong/roscar_ws`,本机就是树莓派 5 部署目标(RPi OS + ROS 2 Jazzy,Python 3.12);同一工作区也可在 PC 上使用(`profile:=pc`)。
- 根目录是 git 仓库(main 分支),`build/ install/ log/` 已被 .gitignore 忽略。
- `dm_imu` 已有节点/launch 测试(`test/test_node.py`、`test/test_launch.py`),但缺 `dm_serial` 分包/粘包/坏 CRC 等协议级测试;改协议解析时必须补充。

## 常用命令

```bash
# 每个终端先加载环境
source /opt/ros/jazzy/setup.bash
source ~/roscar_ws/install/local_setup.bash

# 构建(完整 / 单包)
cd ~/roscar_ws && colcon build --symlink-install
colcon build --symlink-install --packages-select dm_imu

# 测试(包级 + 结果查看)
colcon test --packages-select roscar_base roscar_bringup dm_imu
colcon test-result --verbose

# 快速跑单个测试文件 / 单个用例
python3 -m pytest src/roscar_base/test/test_protocol.py -q
python3 -m pytest src/dm_imu/test/test_node.py -k accel -q

# launch 文件语法检查(不启硬件)
ros2 launch roscar_bringup hardware.launch.py --show-args
```

改 Python 源码后仍要执行对应包的 colcon build 验证安装元数据;不要以直接从 `src/` 导入成功代替构建。

## 架构

十个包分层(详见 README.md 表格):传感驱动(`dm_imu`、`ldlidar_stl_ros2`、`realsense_r200_ros2`——后者是 ament_cmake,依赖手工安装到 /usr/local 的 librealsense-r200 SDK)→ 底盘(`roscar_base`)→ 模型/TF(`roscar_description`)→ SLAM(`roscar_slam`,Cartographer)→ 导航(`roscar_navigation`,Nav2)→ 编排(`roscar_bringup`)→ 数据(`roscar_maps`)。`roscar_exploration` 是空壳预留,`use_exploration:=true` 会主动拒绝启动。

理解整机要看的关键设计(跨多文件):

- **TF 固定为** `map -> odom -> base_footprint -> base_link -> {imu_link, base_laser, r200_link}`。静态 TF 只由 `roscar_description` 发布;`r200_link -> r200_*_optical_frame` 是相机 SPI 标定外参,由 `r200_node` 发布,不进 URDF(这是唯一例外);`dm_imu_rviz.launch.py` 和雷达 viewer 里的兼容 TF 仅限独立查看(`publish_tf` 默认值就是为此设计的)。
- **里程计独立**:`roscar_base` 从 STM32 上报的机体速度自积分发布 `/odom` 和 `odom -> base_footprint`;Cartographer 配置为 `use_odometry = true`、只发 `map -> odom`。禁止从 Cartographer TF 反造 `/odom`。
- **速度安全链**:遥控与 Nav2 的速度都进 `twist_mux`,汇总为 `/cmd_vel` 给底盘;底盘节点自身保留超时清零和退出停车(`roscar_base` 的 watchdog)。
- **平台参数系统**:`roscar_bringup` 用 `config/{pc,rpi5}.yaml` 定义设备端口和传感器 TF,`launch/hardware.launch.py` 通过 `OpaqueFunction` + `profile.py:load_profile()` 读取,`imu_port/lidar_port/base_port` launch 参数可覆盖。启动命令默认用 `profile:=rpi5`(本机)。
- **Nav2 Jazzy 兼容坑**:传给上游 `navigation_launch.py` 的 `use_composition` 必须是 Python 字面量 `"False"`(不能小写 `"false"`),有 `test_architecture.py` 回归测试盯着。

## 本机(RPi5)硬件端口 — 已于 2026-08-29 实测

| 设备 | 设备名 | 波特率 | 接线(GPIO / 物理引脚) | 状态 |
|------|--------|--------|----------------------|------|
| DM-IMU-L1 | `/dev/ttyAMA4` | 921600 | GPIO12/13(=uart4),第 32/33 脚 | 串口已启用,待数据实测 |
| LD06 雷达 | `/dev/ttyAMA0` | 230400 | GPIO14/15(=uart0),第 8/10 脚 | ✅ 10 Hz /scan 正常 |
| R200 相机 | —(USB 枚举) | — | USB 3.0 口(实测 5000M),8086:0a80,序列号 2211006613 | ✅ 2026-09-04 实测:三路 60 Hz、标定与外参正常 |
| C30D 底盘 | `/dev/ttyACM0` | — | USB | — |

- uart4 由 `/boot/firmware/config.txt` 的 `dtoverlay=uart4-pi5` 启用;uart0 由 `enable_uart=1` 启用;内核控制台未占用任何串口。
- Pi 5 的 uart4 在 GPIO12/13,**不是** Pi 4 的 GPIO8/9(那是 Pi 5 的 uart3)。
- 单独测雷达:`ros2 launch ldlidar_stl_ros2 ld06.launch.py port:=/dev/ttyAMA0`(launch 默认 `/dev/ttyUSB0` 是 USB 接法,本机直连排针必须传 port)。
- `/etc/udev/rules.d/99-dm-imu-pm.rules` 解决 DM-IMU 的 USB 电源管理(仅 ttyACM 时生效,排针 UART 不涉及)。

## 关键约束(摘自 AGENTS.md,细节以原文为准)

- **DM-IMU 协议**:帧 `55 AA id RID payload CRC16(LE) 0A`,小端;按 RID 定帧长(0x01/02/03 为 19 字节,0x04 四元数为 23 字节);四元数设备序 WXYZ → ROS 序 XYZW;USB 原始 float 已是 SI 单位,`*_scale` 保持 1.0,不要乘 9.80665 或 π/180;数据可能部分缺失,缺失项 covariance 首元素置 -1.0;串口读线程与缓存访问须线程安全。
- **厂商 SDK**(`ldlidar_stl_ros2/ldlidar_driver`):已知 `copyright/cpplint/lint_cmake/uncrustify` lint 失败是既有的,不要为消告警批量重写;优先在 ROS 适配层修,保留版权信息。
- **目录纪律**:只在 `src/` 改源码、`doc/` 放人工文档;`build/ install/ log/` 是生成物,不编辑、不复制回 src,不提交(见 .gitignore)。
- **交付要求**:说明改了什么、跑了哪些构建/测试/launch 检查、是否实机验证;未实测硬件就明说"未实测",不把"能编译"说成"驱动已验证"。协议解析改动须附合成字节流测试(分包、粘包、噪声、坏 CRC、未知 RID)。
