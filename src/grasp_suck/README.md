# How to start
```
$ roslaunch arm_operation ur5_real.launch robot_ip:=192.168.50.11 tool_length:=0.0
$ roslaunch realsense2_camera rs_rgbd.launch camera:=caemra1
$ roslaunch grasp_suck grasp_suck_system.launch
$ cd src/grasp_suck/src && python main.py [--force_cpu] [--last_model] PATH_TO_YOUR_MODEL
```
## grasp_suck_system.launch

| Type   | Path    | Description |
| :---:  | :---:   | :---:       |
| launch | arm_operation/tcp_publisher.launch                    | Suction and 2-finger gripper transformation information |
| node   | vacuum_conveyor_control/arduino_control               | Turn on vacuum control services |
| node   | robotiq_2f_gripper_control/Robotiq2FGripperRtuNode.py | Turn on robotiq 2-finger gripper |
| node   | grasp_suck/robotiq_gripper_control                    | Trun on robotiq gripper control services |
| node   | visual_system/pixel_to_xyz                            | Convert pixel to 3D coordinate <br>Get cropped color and depth images</br> |
| node   | grasp_suck/get_reward                                 | Using consecutive depth images to judge if action succeed |
| launch | grasp_suck/helper_services.launch                     | High-level services, including homing, picking and placing | 

## Services List

| Service name                              | Service type | Description |
| :---:                                     | :---: | :---: |
|<tr><td colspan=3><p align="center">**Gripper Related**</p></td></tr>|
| /arduino_control/pheumatic_control | std_srvs/SetBool | Suction cup expansion and contraction |
| /arduino_control/vacuum_control    | vacuum_conveyor_control/vacuum_control | Suction behavior control | 
| /robotiq_finger_control_node/intial_gripper | std_srvs/Empty | Initialize gripper |
| /robotiq_finger_control_node/close_gripper | std_srvs/Empty | Close gripper |
| /robotiq_finger_control_node/open_gripper  | std_srvs/Empty | Open gripper | 
| /robotiq_finger_control_node/get_grasp_state | std_srvs/SetBool | Get if grasp success |
|<tr><td colspan=3><p align="center">**Robot Arm Related**</p></td></tr>|
| /ur5_control_server/ur_control/goto_joint_pose | arm_operation/joint_pose | Go to user given joint pose |
| /ur5_control_server/ur_control/goto_pose | arm_operation/target_pose | Go to user given cartesian pose | 
|<tr><td colspan=3><p align="center">**Visaul Related**</p></td></tr>|
| /get_reward/set_prior | std_srvs/Empty | Set depth image before action |
| /get_reward/set_posterior | std_srvs/Empty | Set depth image after action |
| /get_reward/get_result | std_srvs/SetBool | Get result of action |
| /pixel_to_xyz/get_image | visual_system/get_image | Return cropped color and depth images |
| /pixel_to_xyz/pixel_to_xyz | visual_system/get_xyz | Return 3D coordinate with request pixel in color_optical_frame |
|<tr><td colspan=3><p align="center">**High-level Services**</p></td></tr>|
| /helper_services_node/goto_target | grasp_suck/get_pose | Make arm contact with request point with specific motion primitive and angle
| /helper_services_node/robot_go_home | std_srvs/Empty | Return arm to home and set posterior |
| /helper_services_node/robot_go_place | std_srvs/Empty | Place the object with predifined pose |


