from glob import glob
from setuptools import find_packages, setup


package_name = "recv_from_server"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    tests_require=["pytest"],
    zip_safe=True,
    maintainer="SBGDUT",
    maintainer_email="maintainer@example.com",
    description="Receive remote geometry_msgs/Twist commands from WebSocket.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "recv_node = recv_from_server.bridge_node:main",
        ],
    },
)
