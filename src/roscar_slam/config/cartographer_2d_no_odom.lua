include "map_builder.lua"
include "trajectory_builder.lua"

options = {
  map_builder = MAP_BUILDER,
  trajectory_builder = TRAJECTORY_BUILDER,
  map_frame = "map",
  tracking_frame = "imu_link",
  -- Cartographer owns odom -> base_footprint in sensor-only mode. The robot
  -- model then provides base_footprint -> base_link without a duplicate parent.
  published_frame = "base_footprint",
  odom_frame = "odom",
  provide_odom_frame = true,
  publish_frame_projected_to_2d = true,
  use_odometry = false,
  use_nav_sat = false,
  use_landmarks = false,
  num_laser_scans = 1,
  num_multi_echo_laser_scans = 0,
  num_subdivisions_per_laser_scan = 1,
  num_point_clouds = 0,
  lookup_transform_timeout_sec = 0.2,
  submap_publish_period_sec = 0.3,
  pose_publish_period_sec = 0.01,
  trajectory_publish_period_sec = 0.03,
  rangefinder_sampling_ratio = 1.0,
  odometry_sampling_ratio = 1.0,
  fixed_frame_pose_sampling_ratio = 1.0,
  imu_sampling_ratio = 1.0,
  landmarks_sampling_ratio = 1.0,
}

MAP_BUILDER.use_trajectory_builder_2d = true
-- Lidar + IMU (no wheel odometry). dm_imu clamps its stamps monotonic, so
-- NTP clock steps on RTC-less boards can no longer abort the imu queue.
TRAJECTORY_BUILDER_2D.use_imu_data = true
TRAJECTORY_BUILDER_2D.min_range = 0.12
TRAJECTORY_BUILDER_2D.max_range = 12.0
TRAJECTORY_BUILDER_2D.missing_data_ray_length = 5.0
TRAJECTORY_BUILDER_2D.voxel_filter_size = 0.025
TRAJECTORY_BUILDER_2D.motion_filter.max_distance_meters = 0.10
TRAJECTORY_BUILDER_2D.motion_filter.max_angle_radians = math.rad(0.5)
TRAJECTORY_BUILDER_2D.submaps.num_range_data = 90

-- Handheld tuning adopted from the old ~/roscar workspace (carto/config/
-- cartographer_2d.lua): trust the scan more than the motion prior, keep
-- more points for matching.
TRAJECTORY_BUILDER_2D.ceres_scan_matcher.occupied_space_weight = 20.
TRAJECTORY_BUILDER_2D.ceres_scan_matcher.translation_weight = 5.
TRAJECTORY_BUILDER_2D.ceres_scan_matcher.rotation_weight = 20.
TRAJECTORY_BUILDER_2D.adaptive_voxel_filter.min_num_points = 100

-- Wide brute-force search for fast handheld motion. The old config set
-- these windows but never enabled the matcher itself; enable it here.
TRAJECTORY_BUILDER_2D.use_online_correlative_scan_matching = true
TRAJECTORY_BUILDER_2D.real_time_correlative_scan_matcher.linear_search_window = 0.3
TRAJECTORY_BUILDER_2D.real_time_correlative_scan_matcher.angular_search_window = math.rad(30.)

POSE_GRAPH.constraint_builder.min_score = 0.65
POSE_GRAPH.constraint_builder.global_localization_min_score = 0.70
-- Room-scale handheld maps have few submaps; try every pair for loop
-- closure instead of the default 30% sampling.
POSE_GRAPH.constraint_builder.sampling_ratio = 1.0
-- The 0.003 default samples almost no far-apart submap pairs on short
-- sessions, so room loops never close; raise it for room-scale maps.
POSE_GRAPH.global_sampling_ratio = 0.01

return options
