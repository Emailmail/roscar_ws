from glob import glob
from setuptools import find_packages, setup

package_name = 'roscar_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Kielas',
    maintainer_email='c1470759@outlook.com',
    description='PC and Raspberry Pi 5 system bringup for ROSCar.',
    license='MIT',
    tests_require=['pytest'],
)
