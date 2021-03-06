cmake_minimum_required(VERSION 2.8.3)
project(visual_system)
add_compile_options(-std=c++11)

set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOMIC ON)

SET(CMAKE_CXX_FLAGS "-fPIC")
set(CMAKE_INCLUDE_CURRENT_DIR ON)

find_package(catkin REQUIRED COMPONENTS cmake_modules
  roscpp
  rospy
  roslib
  std_msgs
  sensor_msgs
  geometry_msgs
  tf
  image_transport
  cv_bridge
  pcl_conversions
  pcl_ros
  message_generation
  message_filters
)

find_package(Boost REQUIRED)
find_package(OpenCV REQUIRED)
find_package(Qt5 COMPONENTS Widgets Gui REQUIRED)

add_service_files(
  FILES
  get_pc.srv
  pc_is_empty.srv
  check_grasp_success.srv
)

generate_messages(
  DEPENDENCIES
  std_msgs
  geometry_msgs
  sensor_msgs
)

catkin_package(
  INCLUDE_DIRS include  
  CATKIN_DEPENDS roscpp rospy std_msgs geometry_msgs tf message_runtime
)

include_directories(
  include
  ${catkin_INCLUDE_DIRS}
  ${OpenCV_INCLUDE_DIRS}
  ${Qt5Widgets_INCLUDE_DIRS}
  ${Qt5Gui_INCLUDE_DIRS}
)

install(DIRECTORY include/${PROJECT_NAME}/
  DESTINATION ${CATKIN_PACKAGE_INCLUDE_DESTINATION}
  FILES_MATCHING PATTERN "*.h"
  PATTERN ".svn" EXCLUDE
)

add_executable(combine_pc_node src/pc_transform_two_cams.cpp)
add_dependencies(combine_pc_node visual_system_gencpp)
target_link_libraries(combine_pc_node ${catkin_LIBRARIES})

add_executable(two_cams_tf src/two_cams_tf.cpp)
target_link_libraries(two_cams_tf ${catkin_LIBRARIES})

add_library(charuco_detector SHARED src/charuco_detector.cpp)
set_target_properties(charuco_detector PROPERTIES VERSION "1.0.0" SOVERSION "1")
target_link_libraries(charuco_detector ${catkin_LIBRARIES} ${OpenCV_LIBRARIES})

add_executable(charuco src/charuco.cpp)
target_link_libraries(charuco ${catkin_LIBRARIES} ${OpenCV_LIBRARIES} charuco_detector)

add_executable(pointcloud_to_image src/pointcloud_to_image.cpp)
target_link_libraries(pointcloud_to_image ${catkin_LIBRARIES} ${OpenCV_LIBRARIES})

qt5_wrap_cpp(gui_SRC include/visual_system/mainwindow.h)
qt5_wrap_ui(gui_UI src/random_grasping/mainwindow.ui)

add_executable(random_grasping
  src/random_grasping/mainwindow.cpp
  src/random_grasping/main.cpp
  ${gui_SRC}
  ${gui_UI}
)
qt5_use_modules(random_grasping Widgets)
target_link_libraries(random_grasping ${catkin_LIBRARIES})
