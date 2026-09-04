# realsense_r200_ros2

这是基于 `librealsense-r200` 的 ROS 2 Jazzy 独立驱动包。核心采集库不依赖 ROS 2；本包负责将 R200 原生流转换为 ROS 消息。

使用本 ROS 驱动包前，需要安装好 R200 的 Ubuntu24.04 版本的驱动。
驱动仓库：
https://github.com/Emailmail/r200_ubuntu24.04.git

## 依赖和构建

先构建并安装核心库。没有系统安装权限时，可以安装到用户目录：

```bash
cd /home/relog/src/librealsense-r200
cmake --build build --parallel
cmake --install build --prefix /home/relog/.local/librealsense-r200
```

然后构建 ROS 2 包：

```bash
source /opt/ros/jazzy/setup.bash
cd /home/relog/roscar_ws
export CMAKE_PREFIX_PATH=/home/relog/.local/librealsense-r200:$CMAKE_PREFIX_PATH
colcon build --symlink-install --packages-select realsense_r200_ros2
source install/local_setup.bash
```

如果核心库已用 `sudo cmake --install build` 安装到 `/usr/local`，可以不设置用户目录的 `CMAKE_PREFIX_PATH`。

## 启动

```bash
source /opt/ros/jazzy/setup.bash
source /home/relog/roscar_ws/install/local_setup.bash
ros2 launch realsense_r200_ros2 r200.launch.py
```

只捕获 RGB 彩色图像（同时发布彩色 `CameraInfo`）：

```bash
ros2 launch realsense_r200_ros2 r200_rgb_.only.launch.py
```

默认发布：

```text
/r200/color/image_raw       rgb8
/r200/depth/image_raw       16UC1
/r200/infrared/image_raw    mono8
/r200/infrared2/image_raw   mono8
/r200/*/camera_info         sensor_msgs/CameraInfo
/r200/depth/points          sensor_msgs/PointCloud2 (XYZ32F，单位米)
```

Depth 原始值乘以设备读取的 `depth_scale` 后为米。节点同时发布从 `r200_link` 到各 optical frame 的静态 TF：`r200_link` 采用深度 optical 坐标作为父坐标，深度到彩色/双 IR 的平移和旋转来自相机 SPI 标定数据。使用 `q` 不能退出 ROS 节点；请在启动终端按 `Ctrl+C`。

## 常用参数

```bash
ros2 launch realsense_r200_ros2 r200.launch.py serial:=2211006613
ros2 launch realsense_r200_ros2 r200.launch.py use_presets:=false
```

RGB-only 入口也支持 `serial:=...` 和 `use_presets:=false` 参数；深度、双 IR、点云及其
对应话题不会启动。

默认 `use_presets:=true` 使用 R200 的 `best_quality` 模式组合。需要严格指定分辨率和帧率时设置为 `false`，并修改 `config/r200.yaml`。

检查数据：

```bash
ros2 topic list
ros2 topic hz /r200/depth/image_raw
ros2 topic echo /r200/depth/camera_info --once
ros2 run rviz2 rviz2
```

当前发布原生图像、CameraInfo、基于 SDK 标定的 PointCloud2 和静态 TF；暂不发布 aligned image。点云可通过参数 `publish_pointcloud:=false` 关闭。
