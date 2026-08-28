from roscar_base.safety import safe_velocity


def test_watchdog_zeros_stale_command():
    assert safe_velocity(0.2, 0.1, 0.5, 0.31, 0.3, 0.5, 1.0) == (0.0, 0.0, 0.0)


def test_command_is_limited_per_axis():
    assert safe_velocity(1.0, -1.0, 3.0, 0.1, 0.3, 0.5, 1.0) == (0.5, -0.5, 1.0)
