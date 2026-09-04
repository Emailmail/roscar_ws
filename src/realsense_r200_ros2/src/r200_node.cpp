#include "realsense_r200_ros2/r200_node.hpp"

#include <builtin_interfaces/msg/time.hpp>
#include <geometry_msgs/msg/transform_stamped.hpp>
#include <sensor_msgs/msg/point_field.hpp>
#include <tf2/LinearMath/Matrix3x3.h>
#include <tf2/LinearMath/Quaternion.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <iostream>
#include <utility>

namespace realsense_r200_ros2
{

namespace
{

void assign_stamp(const rclcpp::Time & time, builtin_interfaces::msg::Time & stamp)
{
  const int64_t nanoseconds = time.nanoseconds();
  stamp.sec = static_cast<int32_t>(nanoseconds / 1000000000LL);
  stamp.nanosec = static_cast<uint32_t>(nanoseconds % 1000000000LL);
}

std::string distortion_name(rs::distortion model)
{
  switch (model) {
    case rs::distortion::modified_brown_conrady:
      return "plumb_bob";
    case rs::distortion::inverse_brown_conrady:
      return "plumb_bob";
    case rs::distortion::none:
    default:
      return "plumb_bob";
  }
}

}  // namespace

R200Node::R200Node()
: Node("r200_node")
{
  topic_prefix_ = declare_parameter<std::string>("topic_prefix", "r200");
  frame_id_ = declare_parameter<std::string>("frame_id", "r200_link");
  color_frame_id_ = declare_parameter<std::string>("color_frame_id", "r200_color_optical_frame");
  depth_frame_id_ = declare_parameter<std::string>("depth_frame_id", "r200_depth_optical_frame");
  infrared_frame_id_ = declare_parameter<std::string>("infrared_frame_id", "r200_infrared_optical_frame");
  infrared2_frame_id_ = declare_parameter<std::string>("infrared2_frame_id", "r200_infrared2_optical_frame");
  serial_ = declare_parameter<std::string>("serial", "");
  use_presets_ = declare_parameter<bool>("use_presets", true);
  enable_depth_ = declare_parameter<bool>("depth_enabled", true);
  enable_infrared_ = declare_parameter<bool>("infrared_enabled", true);
  enable_infrared2_ = declare_parameter<bool>("infrared2_enabled", true);
  publish_camera_info_ = declare_parameter<bool>("publish_camera_info", true);
  publish_pointcloud_ = declare_parameter<bool>("publish_pointcloud", true);
  depth_width_ = declare_parameter<int>("depth_width", 480);
  depth_height_ = declare_parameter<int>("depth_height", 360);
  depth_fps_ = declare_parameter<int>("depth_fps", 30);
  color_width_ = declare_parameter<int>("color_width", 640);
  color_height_ = declare_parameter<int>("color_height", 480);
  color_fps_ = declare_parameter<int>("color_fps", 30);
  infrared_width_ = declare_parameter<int>("infrared_width", 480);
  infrared_height_ = declare_parameter<int>("infrared_height", 360);
  infrared_fps_ = declare_parameter<int>("infrared_fps", 30);

  context_ = std::make_unique<rs::context>();
  const int device_count = context_->get_device_count();
  if (device_count == 0) {
    throw std::runtime_error("未检测到 Intel RealSense R200");
  }

  for (int index = 0; index < device_count; ++index) {
    rs::device * candidate = context_->get_device(index);
    if (serial_.empty() || serial_ == candidate->get_serial()) {
      device_ = candidate;
      break;
    }
  }
  if (device_ == nullptr) {
    throw std::runtime_error("未找到参数 serial 指定的 R200");
  }
  if (std::string(device_->get_name()).find("R200") == std::string::npos) {
    throw std::runtime_error("连接的设备不是 Intel RealSense R200");
  }

  if (use_presets_) {
    if (enable_depth_) {
      device_->enable_stream(rs::stream::depth, rs::preset::best_quality);
    }
    device_->enable_stream(rs::stream::color, rs::preset::best_quality);
    if (enable_infrared_) {
      device_->enable_stream(rs::stream::infrared, rs::preset::best_quality);
    }
    if (enable_infrared2_) {
      device_->enable_stream(rs::stream::infrared2, rs::preset::best_quality);
    }
  } else {
    if (enable_depth_) {
      device_->enable_stream(rs::stream::depth, depth_width_, depth_height_, rs::format::z16, depth_fps_);
    }
    device_->enable_stream(rs::stream::color, color_width_, color_height_, rs::format::rgb8, color_fps_);
    if (enable_infrared_) {
      device_->enable_stream(
        rs::stream::infrared, infrared_width_, infrared_height_, rs::format::y8, infrared_fps_);
    }
    if (enable_infrared2_) {
      device_->enable_stream(
        rs::stream::infrared2, infrared_width_, infrared_height_, rs::format::y8, infrared_fps_);
    }
  }

  // RViz 默认使用 RELIABLE；短队列可避免慢订阅者无限积压图像/点云。
  const auto stream_qos = rclcpp::QoS(rclcpp::KeepLast(5)).reliable();
  color_publisher_ = create_publisher<sensor_msgs::msg::Image>(topic("color/image_raw"), stream_qos);
  if (enable_depth_) {
    depth_publisher_ = create_publisher<sensor_msgs::msg::Image>(topic("depth/image_raw"), stream_qos);
  }
  if (enable_infrared_) {
    infrared_publisher_ = create_publisher<sensor_msgs::msg::Image>(topic("infrared/image_raw"), stream_qos);
  }
  if (enable_infrared2_) {
    infrared2_publisher_ = create_publisher<sensor_msgs::msg::Image>(topic("infrared2/image_raw"), stream_qos);
  }
  if (publish_camera_info_) {
    color_info_publisher_ = create_publisher<sensor_msgs::msg::CameraInfo>(topic("color/camera_info"), stream_qos);
    if (enable_depth_) {
      depth_info_publisher_ = create_publisher<sensor_msgs::msg::CameraInfo>(topic("depth/camera_info"), stream_qos);
    }
    if (enable_infrared_) {
      infrared_info_publisher_ = create_publisher<sensor_msgs::msg::CameraInfo>(topic("infrared/camera_info"), stream_qos);
    }
    if (enable_infrared2_) {
      infrared2_info_publisher_ = create_publisher<sensor_msgs::msg::CameraInfo>(topic("infrared2/camera_info"), stream_qos);
    }
  }
  if (publish_pointcloud_ && enable_depth_) {
    pointcloud_publisher_ = create_publisher<sensor_msgs::msg::PointCloud2>(
      topic("depth/points"), stream_qos);
  }

  device_->start();
  static_tf_broadcaster_.reset(new tf2_ros::StaticTransformBroadcaster(*this));
  publish_static_transforms();
  RCLCPP_INFO(get_logger(), "已启动 R200: %s, 序列号 %s", device_->get_name(), device_->get_serial());
  capture_thread_ = std::thread(&R200Node::capture_loop, this);
}

R200Node::~R200Node()
{
  stop_requested_ = true;
  RCLCPP_INFO(get_logger(), "正在停止 R200 视频流");
  if (capture_thread_.joinable()) {
    capture_thread_.join();
  }
  if (device_ != nullptr) {
    try {
      device_->stop();
    } catch (...) {
      RCLCPP_WARN(get_logger(), "停止 R200 视频流时发生异常");
    }
  }
  RCLCPP_INFO(get_logger(), "R200 视频流已停止");
}

std::string R200Node::topic(const std::string & suffix) const
{
  if (topic_prefix_.empty()) {
    return suffix;
  }
  return topic_prefix_ + "/" + suffix;
}

sensor_msgs::msg::CameraInfo R200Node::make_camera_info(
  rs::stream stream, const std::string & frame_id) const
{
  const rs::intrinsics intrinsics = device_->get_stream_intrinsics(stream);
  sensor_msgs::msg::CameraInfo info;
  info.header.frame_id = frame_id;
  info.width = static_cast<uint32_t>(intrinsics.width);
  info.height = static_cast<uint32_t>(intrinsics.height);
  info.distortion_model = distortion_name(intrinsics.model());
  info.d.resize(5, 0.0);
  info.d[0] = intrinsics.coeffs[0];
  info.d[1] = intrinsics.coeffs[1];
  info.d[2] = intrinsics.coeffs[2];
  info.d[3] = intrinsics.coeffs[3];
  info.d[4] = intrinsics.coeffs[4];
  info.k[0] = intrinsics.fx;
  info.k[2] = intrinsics.ppx;
  info.k[4] = intrinsics.fy;
  info.k[5] = intrinsics.ppy;
  info.k[8] = 1.0;
  info.r[0] = info.r[4] = info.r[8] = 1.0;
  info.p[0] = intrinsics.fx;
  info.p[2] = intrinsics.ppx;
  info.p[3] = 0.0;
  info.p[5] = intrinsics.fy;
  info.p[6] = intrinsics.ppy;
  info.p[10] = 1.0;
  return info;
}

rclcpp::Time R200Node::camera_stamp(double timestamp_ms)
{
  if (!have_camera_time_base_) {
    first_camera_timestamp_ms_ = timestamp_ms;
    first_ros_time_ = now();
    have_camera_time_base_ = true;
  }
  const double delta_ns = (timestamp_ms - first_camera_timestamp_ms_) * 1000000.0;
  return first_ros_time_ + rclcpp::Duration::from_nanoseconds(static_cast<int64_t>(std::max(0.0, delta_ns)));
}

void R200Node::publish_image(
  const rs::stream stream, const std::string & encoding, int width, int height,
  int bytes_per_pixel, const rclcpp::Time & stamp,
  const std::shared_ptr<rclcpp::Publisher<sensor_msgs::msg::Image>> & publisher,
  const std::shared_ptr<rclcpp::Publisher<sensor_msgs::msg::CameraInfo>> & info_publisher,
  const sensor_msgs::msg::CameraInfo & camera_info)
{
  if (!publisher) {
    return;
  }
  const auto * data = static_cast<const uint8_t *>(device_->get_frame_data(stream));
  if (data == nullptr) {
    return;
  }
  sensor_msgs::msg::Image message;
  assign_stamp(stamp, message.header.stamp);
  message.header.frame_id = camera_info.header.frame_id;
  message.height = static_cast<uint32_t>(height);
  message.width = static_cast<uint32_t>(width);
  message.encoding = encoding;
  message.is_bigendian = false;
  message.step = static_cast<sensor_msgs::msg::Image::_step_type>(width * bytes_per_pixel);
  message.data.assign(data, data + static_cast<size_t>(message.step) * message.height);
  publisher->publish(message);

  if (publish_camera_info_ && info_publisher) {
    sensor_msgs::msg::CameraInfo info = camera_info;
    assign_stamp(stamp, info.header.stamp);
    info_publisher->publish(info);
  }
}

void R200Node::capture_loop()
{
  sensor_msgs::msg::CameraInfo color_info = make_camera_info(rs::stream::color, color_frame_id_);
  sensor_msgs::msg::CameraInfo depth_info;
  if (enable_depth_) {
    depth_info = make_camera_info(rs::stream::depth, depth_frame_id_);
  }
  sensor_msgs::msg::CameraInfo infrared_info;
  sensor_msgs::msg::CameraInfo infrared2_info;
  if (enable_infrared_) {
    infrared_info = make_camera_info(rs::stream::infrared, infrared_frame_id_);
  }
  if (enable_infrared2_) {
    infrared2_info = make_camera_info(rs::stream::infrared2, infrared2_frame_id_);
  }

  const int color_width = device_->get_stream_width(rs::stream::color);
  const int color_height = device_->get_stream_height(rs::stream::color);
  const int depth_width = enable_depth_ ? device_->get_stream_width(rs::stream::depth) : 0;
  const int depth_height = enable_depth_ ? device_->get_stream_height(rs::stream::depth) : 0;
  const int infrared_width = enable_infrared_ ? device_->get_stream_width(rs::stream::infrared) : 0;
  const int infrared_height = enable_infrared_ ? device_->get_stream_height(rs::stream::infrared) : 0;
  const int infrared2_width = enable_infrared2_ ? device_->get_stream_width(rs::stream::infrared2) : 0;
  const int infrared2_height = enable_infrared2_ ? device_->get_stream_height(rs::stream::infrared2) : 0;

  while (!stop_requested_ && rclcpp::ok()) {
    try {
      if (!device_->poll_for_frames()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
        continue;
      }
      const rclcpp::Time color_stamp = camera_stamp(device_->get_frame_timestamp(rs::stream::color));
      publish_image(rs::stream::color, "rgb8", color_width, color_height, 3, color_stamp,
        color_publisher_, color_info_publisher_, color_info);
      if (enable_depth_) {
        const rclcpp::Time depth_stamp = camera_stamp(device_->get_frame_timestamp(rs::stream::depth));
        publish_image(rs::stream::depth, "16UC1", depth_width, depth_height, 2, depth_stamp,
          depth_publisher_, depth_info_publisher_, depth_info);
        if (publish_pointcloud_) {
          publish_pointcloud(depth_stamp, depth_width, depth_height);
        }
      }
      if (enable_infrared_) {
        const rclcpp::Time infrared_stamp =
          camera_stamp(device_->get_frame_timestamp(rs::stream::infrared));
        publish_image(rs::stream::infrared, "mono8", infrared_width, infrared_height, 1, infrared_stamp,
          infrared_publisher_, infrared_info_publisher_, infrared_info);
      }
      if (enable_infrared2_) {
        const rclcpp::Time infrared2_stamp =
          camera_stamp(device_->get_frame_timestamp(rs::stream::infrared2));
        publish_image(rs::stream::infrared2, "mono8", infrared2_width, infrared2_height, 1, infrared2_stamp,
          infrared2_publisher_, infrared2_info_publisher_, infrared2_info);
      }
    } catch (const rs::error & error) {
      if (!stop_requested_) {
        RCLCPP_ERROR(
          get_logger(), "R200 采集失败 (%s): %s", error.get_failed_function().c_str(), error.what());
      }
      break;
    } catch (const std::exception & error) {
      if (!stop_requested_) {
        RCLCPP_ERROR(get_logger(), "R200 采集失败: %s", error.what());
      }
      break;
    }
  }
}

void R200Node::publish_pointcloud(const rclcpp::Time & stamp, int width, int height)
{
  if (!pointcloud_publisher_) {
    return;
  }
  const auto * data = static_cast<const uint8_t *>(device_->get_frame_data(rs::stream::points));
  if (data == nullptr) {
    return;
  }

  sensor_msgs::msg::PointCloud2 message;
  assign_stamp(stamp, message.header.stamp);
  message.header.frame_id = depth_frame_id_;
  message.height = static_cast<uint32_t>(height);
  message.width = static_cast<uint32_t>(width);
  message.is_bigendian = false;
  message.is_dense = false;
  message.point_step = 3U * sizeof(float);
  message.row_step = message.point_step * message.width;
  message.fields.resize(3);
  message.fields[0].name = "x";
  message.fields[0].offset = 0;
  message.fields[0].datatype = sensor_msgs::msg::PointField::FLOAT32;
  message.fields[0].count = 1;
  message.fields[1].name = "y";
  message.fields[1].offset = sizeof(float);
  message.fields[1].datatype = sensor_msgs::msg::PointField::FLOAT32;
  message.fields[1].count = 1;
  message.fields[2].name = "z";
  message.fields[2].offset = 2U * sizeof(float);
  message.fields[2].datatype = sensor_msgs::msg::PointField::FLOAT32;
  message.fields[2].count = 1;
  message.data.assign(data, data + static_cast<size_t>(message.row_step) * message.height);
  pointcloud_publisher_->publish(message);
}

void R200Node::publish_static_transforms()
{
  std::vector<geometry_msgs::msg::TransformStamped> transforms;
  if (enable_depth_) {
    transforms.push_back(make_stream_transform(rs::stream::depth, depth_frame_id_));
  }
  transforms.push_back(make_stream_transform(rs::stream::color, color_frame_id_));
  if (enable_infrared_) {
    transforms.push_back(make_stream_transform(rs::stream::infrared, infrared_frame_id_));
  }
  if (enable_infrared2_) {
    transforms.push_back(make_stream_transform(rs::stream::infrared2, infrared2_frame_id_));
  }
  static_tf_broadcaster_->sendTransform(transforms);
}

geometry_msgs::msg::TransformStamped R200Node::make_stream_transform(
  rs::stream stream, const std::string & child_frame_id) const
{
  geometry_msgs::msg::TransformStamped transform;
  transform.header.stamp = now();
  transform.header.frame_id = frame_id_;
  transform.child_frame_id = child_frame_id;

  if (stream == rs::stream::depth) {
    transform.transform.rotation.w = 1.0;
    return transform;
  }

  // R200 外参以米和行主序旋转矩阵给出，父坐标系采用深度光学坐标系。
  const rs::extrinsics extrinsics = device_->get_extrinsics(rs::stream::depth, stream);
  transform.transform.translation.x = extrinsics.translation[0];
  transform.transform.translation.y = extrinsics.translation[1];
  transform.transform.translation.z = extrinsics.translation[2];
  tf2::Matrix3x3 rotation(
    extrinsics.rotation[0], extrinsics.rotation[1], extrinsics.rotation[2],
    extrinsics.rotation[3], extrinsics.rotation[4], extrinsics.rotation[5],
    extrinsics.rotation[6], extrinsics.rotation[7], extrinsics.rotation[8]);
  tf2::Quaternion quaternion;
  rotation.getRotation(quaternion);
  transform.transform.rotation.x = quaternion.x();
  transform.transform.rotation.y = quaternion.y();
  transform.transform.rotation.z = quaternion.z();
  transform.transform.rotation.w = quaternion.w();
  return transform;
}

}  // namespace realsense_r200_ros2

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  try {
    auto node = std::make_shared<realsense_r200_ros2::R200Node>();
    rclcpp::spin(node);
  } catch (const rs::error & error) {
    std::cerr << "RealSense 调用失败 (" << error.get_failed_function() << "): " << error.what() << std::endl;
    rclcpp::shutdown();
    return EXIT_FAILURE;
  } catch (const std::exception & error) {
    std::cerr << "R200 ROS2 节点启动失败: " << error.what() << std::endl;
    rclcpp::shutdown();
    return EXIT_FAILURE;
  }
  rclcpp::shutdown();
  return EXIT_SUCCESS;
}
