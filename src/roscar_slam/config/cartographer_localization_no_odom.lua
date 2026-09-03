include "map_builder.lua"
include "trajectory_builder.lua"

options = {
  map_builder = MAP_BUILDER,
  trajectory_builder = TRAJECTORY_BUILDER,
  map_frame = "map",
  tracking_frame = "imu_link",
  -- Sensor-only localization (no chassis): mirrors cartographer_2d_no_odom.lua.
  -- Cartographer owns odom -> base_footprint so Nav2 costmaps get their TF;
  -- base_footprint (not base_link) keeps robot_state_publisher the sole parent
  -- of base_link. Same scheme as the old workspace carto_localize.lua.
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
TRAJECTORY_BUILDER.pure_localization_trimmer = {max_submaps_to_keep = 6}
TRAJECTORY_BUILDER_2D.use_imu_data = true
TRAJECTORY_BUILDER_2D.min_range = 0.12
TRAJECTORY_BUILDER_2D.max_range = 12.0
TRAJECTORY_BUILDER_2D.missing_data_ray_length = 5.0
TRAJECTORY_BUILDER_2D.voxel_filter_size = 0.025
TRAJECTORY_BUILDER_2D.motion_filter.max_distance_meters = 0.10
TRAJECTORY_BUILDER_2D.motion_filter.max_angle_radians = math.rad(0.5)
TRAJECTORY_BUILDER_2D.submaps.num_range_data = 160

-- Handheld tuning carried over from the old workspace carto_localize.lua and
-- cartographer_2d_no_odom.lua: trust the scan more than the motion prior and
-- brute-force a wide window so fast hand motion does not lose the match.
TRAJECTORY_BUILDER_2D.ceres_scan_matcher.occupied_space_weight = 20.
TRAJECTORY_BUILDER_2D.ceres_scan_matcher.translation_weight = 5.
TRAJECTORY_BUILDER_2D.ceres_scan_matcher.rotation_weight = 20.
TRAJECTORY_BUILDER_2D.adaptive_voxel_filter.min_num_points = 100
TRAJECTORY_BUILDER_2D.use_online_correlative_scan_matching = true
TRAJECTORY_BUILDER_2D.real_time_correlative_scan_matcher.linear_search_window = 0.3
TRAJECTORY_BUILDER_2D.real_time_correlative_scan_matcher.angular_search_window = math.rad(30.)

POSE_GRAPH.constraint_builder.min_score = 0.65
POSE_GRAPH.constraint_builder.global_localization_min_score = 0.70
POSE_GRAPH.optimize_every_n_nodes = 20

return options
