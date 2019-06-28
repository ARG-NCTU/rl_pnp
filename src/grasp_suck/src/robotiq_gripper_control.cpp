#include <ros/ros.h>
#include <std_srvs/Empty.h>
#include <std_srvs/Trigger.h>
#include <robotiq_2f_gripper_control/Robotiq2FGripper_robot_input.h> // Information and state of gripper
#include <robotiq_2f_gripper_control/Robotiq2FGripper_robot_output.h> // Command from user

const int THRES = 210;  // Gripper position(PO) greater than this will consider as fail grasp
ros::Publisher pub_gripper_out;
ros::Subscriber sub_gripper_in;
robotiq_2f_gripper_control::Robotiq2FGripper_robot_input now_state;

// Initial robotiq 2-finger gripper, refer to: package:robotiq_2f_gripper_control/nodes/Robotiq2FGripperSimpleController.py
void initial_gripepr(void){
  robotiq_2f_gripper_control::Robotiq2FGripper_robot_output msg;
  pub_gripper_out.publish(msg);// Reset
  ros::Duration(0.5).sleep();
  msg.rACT = 1; msg.rGTO = 1; msg.rSP = 200; msg.rFR = 100;
  pub_gripper_out.publish(msg); // Active
  ROS_INFO("Robotiq gripper initialization complete!");
}
// Subscriber callback, only update the global variable for future usage
void cb_update_state(const robotiq_2f_gripper_control::Robotiq2FGripper_robot_input msg){
  now_state = msg;
}
// Close gripper service callback
bool close_gripper_cb(std_srvs::Empty::Request &req, std_srvs::Empty::Response &res){
  ROS_INFO("Receive close gripper request!");
  robotiq_2f_gripper_control::Robotiq2FGripper_robot_output msg;
  msg.rACT = 1; msg.rGTO = 1; msg.rPR = 255; msg.rSP = 200; msg.rFR = 100;
  pub_gripper_out.publish(msg);
  return true;
}
// Open gripper service callback
bool open_gripper_cb(std_srvs::Empty::Request &req, std_srvs::Empty::Response &res){
  ROS_INFO("Receive open gripper request!");
  robotiq_2f_gripper_control::Robotiq2FGripper_robot_output msg;
  msg.rACT = 1; msg.rGTO = 1; msg.rPR = 0; msg.rSP = 200; msg.rFR = 100;
  pub_gripper_out.publish(msg);
  return true;
}
// Check if the action is success
bool get_grasp_state_cb(std_srvs::Trigger::Request &req, std_srvs::Trigger::Response &res){
  ROS_INFO("Now gripper position: %d", now_state.gPO);
  if(now_state.gPO >= THRES){
    res.success = false;
    res.message = "Fail to grasp object";
  } else{ // Gripper position now less than the threshold will be considered as succeed
    res.success = true;
    res.message = "Successfully grasp object";
  }
}

int main(int argc, char** argv)
{
  ros::init(argc, argv, "robotiq_finger_control_node");
  ros::NodeHandle nh, pnh("~");
  // Setup publisher and subscriber
  pub_gripper_out = nh.advertise<robotiq_2f_gripper_control::Robotiq2FGripper_robot_output>("Robotiq2FGripperRobotOutput", 1);
  sub_gripper_in  = nh.subscribe("Robotiq2FGripperRobotInput", 1, cb_update_state);
  // Initialize gripper
  initial_gripepr();
  // Advertise services
  ros::ServiceServer close_gripper_service = pnh.advertiseService("close_gripper", close_gripper_cb);
  ros::ServiceServer open_gripepr_service  = pnh.advertiseService("open_gripper", open_gripper_cb);
  ros::ServiceServer check_grasp_succeed   = pnh.advertiseService("get_grasp_state", get_grasp_state_cb);
  // Spin until ROS shutdown  
  ros::spin();
  return 0;
}