cmake_minimum_required(VERSION 2.8.3)
project(grasp_suck)

add_compile_options(-std=c++11)

find_package(catkin REQUIRED COMPONENTS cmake_modules
  roscpp
  rosbag
  rospy
  roslib
  std_msgs
  sensor_msgs
  geometry_msgs
  trajectory_msgs
  tf
  actionlib
  actionlib_msgs
  message_generation
  cv_bridge
  arm_operation
)

find_package(OpenCV REQUIRED)

add_service_files(
  FILES
  recorder.srv
)

generate_messages(
  DEPENDENCIES
  std_msgs
  geometry_msgs
  sensor_msgs
)

catkin_package(
 #INCLUDE_DIRS include
 #LIBRARIES grasp_suck
 CATKIN_DEPENDS roscpp rospy std_msgs roslib message_runtime
 #DEPENDS 
)

include_directories(
  include
  ${catkin_INCLUDE_DIRS}
  ${OpenCV_INCLUDE_DIRS}
)

add_executable(autonomous_recording src/autonomous_recording.cpp)
add_dependencies(autonomous_recording grasp_suck_gencpp)
target_link_libraries(autonomous_recording ${catkin_LIBRARIES} -lstdc++fs)

add_executable(bag_to_data src/bag_to_data.cpp)
add_dependencies(bag_to_data grasp_suck_gencpp)
target_link_libraries(bag_to_data ${catkin_LIBRARIES})
