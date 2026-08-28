# roscar_exploration

这是自动探索的预留包，目前没有探索算法，不能用于自主运行。

未来实现应订阅 `/map` 与 TF `map -> base_footprint`，通过 Nav2 的
`navigate_to_pose` action 发送目标，并提供显式启停和取消能力。探索节点不应直接
发布 `/cmd_vel`，也不应自行实现路径规划或绕过 Nav2 安全链路。
