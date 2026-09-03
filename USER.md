# 验收一



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