# 验收一

建图：
```bash
ros2 launch roscar_bringup mapping.launch.py profile:=rpi5 use_base:=false
```

保存地图：
```bash
ros2 launch roscar_slam save_map.launch.py \
  map_dir:=~/roscar_ws/roscar_maps/maps/ map_name:=my_map
```

开启定位与导航(需要已经建好地图)：
```bash
ros2 launch roscar_bringup navigation.launch.py \
  profile:=rpi5 map_name:=my_map use_base:=false use_rviz:=false
```

# 验收二

先打开PC端的ros控制任务(连接xbox/g923)

打开云服务器的监听(接收来自xbox/g923的控制数据)：
```bash
ros2 run recv_from_server recv_node --ros-args \
  -p cmd_vel_topic:=/cmdvel_remote \
  -p server_uri:=ws://8.134.118.29:8771
```

打开c30d底盘控制器：
```bash
ros2 run roscar_base c30d_driver --ros-args -p cmd_vel_topic:=/cmdvel_remote
```

打开导航：
```bash
ros2 launch roscar_bringup navigation.launch.py \
  profile:=rpi5 map_name:=my_map use_base:=false use_rviz:=false
```

经服务器转发坐标到上位机：
```bash
ros2 launch send2server status.launch.py
```