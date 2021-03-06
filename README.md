## Hardwares
| Hardware | Image |
| :---: | :---: |
| ABB IRB1660ID| <img src="https://github.com/sean85914/rl_pnp/blob/master/src/grasp_suck/img/abb.jpg" width=222 height=296/>|
| RealSense D435/415 <br> One required, one optinal | <img src="https://github.com/sean85914/rl_pnp/blob/master/src/grasp_suck/img/d435.jpeg" width=237 height=105/> |
| Vacuum Pumb <br> Should can be controlled by an Arduino and a valve| <img src="https://github.com/sean85914/rl_pnp/blob/master/src/grasp_suck/img/vacuum_pump.png" width=244 height=186/> |
| Tools from [XYZ Robotics](http://en.xyzrobotics.ai/)| <img src="https://github.com/sean85914/rl_pnp/blob/master/src/grasp_suck/img/tools.png" width=299 height=159/> |

## Dependencies
* [ROS kinetic](http://wiki.ros.org/kinetic/Installation/Ubuntu)
* [librealsense2](https://github.com/IntelRealSense/librealsense/blob/master/doc/installation.md)
* [Serial](http://wjwwood.io/serial/)
* Cuda with version either 9 or 10

## How to Start
```
$ cd && git clone https://github.com/sean85914/flip_object.git
$ cd flip_object && catkin_make
$ source devel/setup.bash # do this every time you open a new terminal
$ roscore
$ roslaunch grasp_suck actuator.launch # Make sure you turn on the robot, run the server and share the same network with your PC
$ roslaunch grasp_suck sensors.launch serial_no:=[D4X5 Serial No.] record_serial_no:=[side-record camera serial no.] # if you don't have side-recording camera, set side_record to false and leave record-serial_no empty
$ roslaunch visualization viz.launch rviz:=true
$ roscd grasp_suck/src && python main.py [integer number]
```

## [DLP 2019 Final Project](https://github.com/sean85914/rl_pnp/tree/master/dlp_final/grasp_suck)
![](https://github.com/sean85914/flip_object/blob/master/img/dlp_system.png)
In this project, we try to use reinforcement learning to do pick and place with custom made gripper. The gripper is composed of Robotiq 2F-85 and a retractable suction cup. The method is inspired by "Learning Synergies between Pushing and Grasping with Self-supervised Deep Reinforcement Learning", from Andy Zeng.
```
@inproceedings{zeng2018learning,  
  title={Learning synergies between pushing and grasping with self-supervised deep reinforcement learning},  
  author={Zeng, Andy and Song, Shuran and Welker, Stefan and Lee, Johnny and Rodriguez, Alberto and Funkhouser, Thomas},  
  booktitle={2018 IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)},  
  pages={4238--4245},  
  year={2018},  
  organization={IEEE}  
}
```

## [Master Thesis](https://github.com/sean85914/rl_pnp/tree/master/src/grasp_suck)
Extend from the project above, we try to use three different tools to do bin picking job with ABB IRB1660ID. Specially thanks to XYZ Robotics for sponsoring the robot arm and the tooling system.
![](https://github.com/sean85914/flip_object/blob/master/img/master_thesis_system.png)
