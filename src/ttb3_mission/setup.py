import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'ttb3_mission'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='skuba',
    maintainer_email='napat559977@gmail.com',
    description='Mission-manager state machine and button handler',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mission_manager = ttb3_mission.mission_manager:main',
            'button_handler = ttb3_mission.button_handler:main',
        ],
    },
)
