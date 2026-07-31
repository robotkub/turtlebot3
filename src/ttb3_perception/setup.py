import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'ttb3_perception'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='robotkub',
    maintainer_email='napat559977@gmail.com',
    description='AprilTag number reading and victim-sign detection for the RobotKub TurtleBot3 WRG2026 mission',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'apriltag_detector = ttb3_perception.apriltag_detector:main',
            'victim_detector = ttb3_perception.victim_detector:main',
        ],
    },
)
