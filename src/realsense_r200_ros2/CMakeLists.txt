cmake_minimum_required(VERSION 3.16)
project(realsense_r200_ros2 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(librealsense-r200 CONFIG REQUIRED)

add_executable(r200_node src/r200_node.cpp)
target_include_directories(r200_node PRIVATE include)
ament_target_dependencies(r200_node
  rclcpp
  sensor_msgs
  geometry_msgs
  tf2
  tf2_ros
)
target_link_libraries(r200_node realsense::realsense)

install(TARGETS r200_node
  DESTINATION lib/${PROJECT_NAME}
)
install(DIRECTORY launch config rviz
  DESTINATION share/${PROJECT_NAME}
)
install(DIRECTORY include/
  DESTINATION include
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_launch test/test_launch.py)
endif()

ament_package()
