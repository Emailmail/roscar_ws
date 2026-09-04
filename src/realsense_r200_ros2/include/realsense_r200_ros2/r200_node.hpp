#pragma once

#include <librealsense/rs.hpp>

#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/transform_stamped.hpp>
#include <sensor_msgs/msg/camera_info.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <tf2_ros/static_transform_broadcaster.h>

#include <atomic>
#include <memory>
#include <string>
#include <thread>
#include <vector>

namespace realsense_r200_ros2
{

class R200Node final : public rclcpp::Node
{
public:
  R200Node();
  ~R200Node() override;

private:
  void capture_loop();
  void publish_static_transforms();
  void publish_image(const rs::stream stream, const std::string & encoding,
                    int width, int height, int bytes_per_pixel,
                    const rclcpp::Time & stamp,
                    const std::shared_ptr<rclcpp::Publisher<sensor_msgs::msg::Image>> & publisher,
                    const std::shared_ptr<rclcpp::Publisher<sensor_msgs::msg::CameraInfo>> & info_publisher,
                    const sensor_msgs::msg::CameraInfo & camera_info);
  void publish_pointcloud(const rclcpp::Time & stamp, int width, int height);
  geometry_msgs::msg::TransformStamped make_stream_transform(
    rs::stream stream, const std::string & child_frame_id) const;
  sensor_msgs::msg::CameraInfo make_camera_info(rs::stream stream, const std::string & frame_id) const;
  rclcpp::Time camera_stamp(double timestamp_ms);
  std::string topic(const std::string & suffix) const;

  std::unique_ptr<rs::context> context_;
  rs::device * device_{nullptr};
  std::thread capture_thread_;
  std::atomic<bool> stop_requested_{false};

  std::string topic_prefix_;
  std::string frame_id_;
  std::string color_frame_id_;
  std::string depth_frame_id_;
  std::string infrared_frame_id_;
  std::string infrared2_frame_id_;
  std::string serial_;
  bool enable_depth_{true};
  bool enable_infrared_{true};
  bool enable_infrared2_{true};
  bool use_presets_{true};
  bool publish_camera_info_{true};
  bool publish_pointcloud_{true};
  int depth_width_{480};
  int depth_height_{360};
  int depth_fps_{30};
  int color_width_{640};
  int color_height_{480};
  int color_fps_{30};
  int infrared_width_{480};
  int infrared_height_{360};
  int infrared_fps_{30};

  rclcpp::Time first_ros_time_;
  double first_camera_timestamp_ms_{0.0};
  bool have_camera_time_base_{false};

  std::shared_ptr<rclcpp::Publisher<sensor_msgs::msg::Image>> color_publisher_;
  std::shared_ptr<rclcpp::Publisher<sensor_msgs::msg::Image>> depth_publisher_;
  std::shared_ptr<rclcpp::Publisher<sensor_msgs::msg::Image>> infrared_publisher_;
  std::shared_ptr<rclcpp::Publisher<sensor_msgs::msg::Image>> infrared2_publisher_;
  std::shared_ptr<rclcpp::Publisher<sensor_msgs::msg::CameraInfo>> color_info_publisher_;
  std::shared_ptr<rclcpp::Publisher<sensor_msgs::msg::CameraInfo>> depth_info_publisher_;
  std::shared_ptr<rclcpp::Publisher<sensor_msgs::msg::CameraInfo>> infrared_info_publisher_;
  std::shared_ptr<rclcpp::Publisher<sensor_msgs::msg::CameraInfo>> infrared2_info_publisher_;
  std::shared_ptr<rclcpp::Publisher<sensor_msgs::msg::PointCloud2>> pointcloud_publisher_;
  std::unique_ptr<tf2_ros::StaticTransformBroadcaster> static_tf_broadcaster_;
};

}  // namespace realsense_r200_ros2
