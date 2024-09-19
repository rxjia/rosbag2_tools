from setuptools import find_packages, setup

package_name = 'rosbag2_tools'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='rx',
    maintainer_email='ruixingjia@outlook.com',
    description='TODO: Package description',
    license='TODO: ',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'bag2video = rosbag2_tools.bag2video:main',
        ],
    },
)
