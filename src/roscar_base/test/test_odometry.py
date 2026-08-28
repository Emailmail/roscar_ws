import math

import pytest

from roscar_base.odometry import PlanarOdometry


def test_forward_and_lateral_motion():
    odom = PlanarOdometry()
    odom.integrate(1.0, 0.0, 0.0, 1.0)
    odom.integrate(0.0, 1.0, 0.0, 2.0)
    assert odom.x == pytest.approx(1.0)
    assert odom.y == pytest.approx(2.0)


def test_body_velocity_rotates_into_odom_frame():
    odom = PlanarOdometry(yaw=math.pi / 2.0)
    odom.integrate(1.0, 0.0, 0.0, 1.0)
    assert odom.x == pytest.approx(0.0, abs=1e-7)
    assert odom.y == pytest.approx(1.0)


def test_invalid_dt_is_ignored():
    odom = PlanarOdometry()
    odom.integrate(1.0, 1.0, 1.0, -1.0)
    assert (odom.x, odom.y, odom.yaw) == (0.0, 0.0, 0.0)
