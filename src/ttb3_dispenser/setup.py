from setuptools import find_packages, setup

package_name = 'ttb3_dispenser'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='robotkub',
    maintainer_email='napat559977@gmail.com',
    description='Supply-box dispenser controller with a swappable hardware backend',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'dispenser_controller = ttb3_dispenser.dispenser_controller:main',
        ],
    },
)
