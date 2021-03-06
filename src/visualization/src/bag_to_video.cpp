// STD
#include <experimental/filesystem>
#include <chrono>
#include <queue>
#include <thread>
#include <utility>
// Boost
#include <boost/foreach.hpp>
#include <boost/thread.hpp>
// ROS
#include <rosbag/bag.h>
#include <rosbag/view.h>
#include <cv_bridge/cv_bridge.h>
#include <sensor_msgs/Image.h>
#include <sensor_msgs/CompressedImage.h>
// CV
#include "opencv2/core.hpp"
#include "opencv2/imgproc.hpp"
#include "opencv2/highgui.hpp"
#include "opencv2/videoio.hpp"

#define foreach BOOST_FOREACH

bool read_complete = false;
int width, height;
double speed = 1.0, fps;
std::string out_name;

typedef std::pair<cv::Mat, std::string> data_pair;

void write_video(/*std::queue<cv::Mat>*/std::queue<data_pair> &data_vec){
  while(data_vec.empty()){} // Wait until data in the queue
  cv::VideoWriter video(out_name, CV_FOURCC('H', '2', '6', '4'), fps, cv::Size(width, height));
  while(true){
    if(read_complete and data_vec.empty()) break; // Stop
    if(data_vec.empty()) continue; // Consume too fast
    /*video << data_vec.front().first;
    data_vec.pop();
    if(read_complete){
      std::cout << "\r" << data_vec.size() << " images remaining...";
    }*/
    // Write time
    cv::Mat raw_img = data_vec.front().first, img_with_time;
    raw_img.copyTo(img_with_time);
    std::string time_str = data_vec.front().second;
    int baseline;
    cv::Size size = cv::getTextSize(time_str, cv::FONT_HERSHEY_PLAIN, 1.0, 2, &baseline);
    cv::putText(img_with_time, time_str, \
                cv::Point(width-size.width, size.height), \
                cv::FONT_HERSHEY_PLAIN, 1.0, \
                cv::Scalar(255, 255, 255), 
                2);
    // Write speed
    if(speed!=1.0){ // Only write if not 1X speed
      std::string speed_str;
      speed_str = std::to_string((int)speed) + "X";
      cv::Size speed_size = cv::getTextSize(speed_str, cv::FONT_HERSHEY_PLAIN, 2.0, 2, &baseline);
      cv::putText(img_with_time, speed_str, \
                cv::Point(width-speed_size.width, size.height+speed_size.height+10),  // Poisition, 10 for Y-margin
                cv::FONT_HERSHEY_PLAIN, 2.0,  // Font & size
                cv::Scalar(255, 255, 255),  // Color
                2); // Thickness
    }
    video << img_with_time;
    data_vec.pop();
    if(read_complete){
      std::cout << "\r" << data_vec.size() << " images remaining...";
    }
  }
}

std::string unix_time2str(ros::Time time){
  time_t ts = time.sec;
  char buf[1024] = "";
  struct tm* tms = localtime(&ts);
  strftime(buf, 1024, "%Y/%m/%d %H:%M:%S", tms);
  return std::string(buf);
}

int main(int argc, char** argv)
{
  // Parse input argument
  bool has_data = false, is_compressed;
  std::string topic_name="";
  if(argc<3){
    std::cout << "\033[1;31mInsufficient input arguments\n\
Usage: ./bag_to_video bag_name output_video_name [speed]\n\033[0m";
    exit(EXIT_FAILURE);
  }
  std::string in_bag(argv[1]);
  out_name = std::string(argv[2]);
  if(out_name.length()<=4) // .mp4
    out_name+=".mp4";
  else{
    size_t pos;
    out_name.find(".");
    if(pos==std::string::npos){
      out_name+=".mp4";
    }
  }
  if(argc==4)
    speed = atof(argv[3]);
  std::cout << "Input bag: " << in_bag << "\n";
  std::cout << "Output video: " << out_name << "\n";
  std::cout << "Video speed: " << speed << "\n";
  // Open bag
  rosbag::Bag bag;
  try{
    bag.open(in_bag, rosbag::bagmode::Read);
  } catch(const rosbag::BagIOException& e){
    std::cout << "\033[1;31mProvided bag name unopenable, please make sure you provide correct name, exiting...\033[0m\n";
    exit(EXIT_FAILURE);
  }
  rosbag::View view(bag);
  cv_bridge::CvImagePtr cv_bridge_ptr;
  //std::queue<cv::Mat> data_queue;
  std::queue<data_pair> data_queue;
  double bag_duration = (view.getEndTime() - view.getBeginTime()).toSec();
  std::cout << "Bag duration: " << bag_duration << " seconds\n";
  std::cout << "Converting...\n";
  // Start writing thread
  std::thread writing_thread(write_video, std::ref(data_queue));
  // Start reading
  auto s_ts = std::chrono::high_resolution_clock::now();
  // First pass: Counting number of images
  int img_cnt = 0;
  foreach(const rosbag::MessageInstance m, view){
    if(m.getDataType()=="sensor_msgs/Image" or \
       m.getDataType()=="sensor_msgs/CompressedImage"){
      if(img_cnt==0){ // Only convert if first image 
        if(m.getDataType()=="sensor_msgs/Image"){
          sensor_msgs::Image::ConstPtr img_ptr = m.instantiate<sensor_msgs::Image>();
          try{
            cv_bridge_ptr = cv_bridge::toCvCopy(img_ptr);
          } catch(cv_bridge::Exception& e){
            std::cout << "\033[1;33mcv_bridge exception: " << e.what() << "\033[0m\n";
            exit(EXIT_FAILURE);
          }
          width = cv_bridge_ptr->image.cols;
          height = cv_bridge_ptr->image.rows;
        }else{
          sensor_msgs::CompressedImage::ConstPtr img_ptr = m.instantiate<sensor_msgs::CompressedImage>();
          try{
            cv_bridge_ptr = cv_bridge::toCvCopy(img_ptr);
          } catch(cv_bridge::Exception& e){
            std::cout << "\033[1;33mcv_bridge exception: " << e.what() << "\033[0m\n";
            exit(EXIT_FAILURE);
          }
          width = cv_bridge_ptr->image.cols;
          height = cv_bridge_ptr->image.rows;
        }
      }
      ++img_cnt;
    }
  }
  double estimated_fps = img_cnt/bag_duration;
  fps = estimated_fps*speed;
  foreach(const rosbag::MessageInstance m, view){
    if(m.getDataType()=="sensor_msgs/Image" or \
       m.getDataType()=="sensor_msgs/CompressedImage"){
      if(m.getDataType()=="sensor_msgs/Image"){
        is_compressed = false;
        sensor_msgs::Image::ConstPtr img_ptr = m.instantiate<sensor_msgs::Image>();
        try{
          cv_bridge_ptr = cv_bridge::toCvCopy(img_ptr);
        } catch(cv_bridge::Exception& e){
          std::cout << "\033[1;33mcv_bridge exception: " << e.what() << "\033[0m\n";
          exit(EXIT_FAILURE);
        }
      } else{
       is_compressed = true;
       sensor_msgs::CompressedImage::ConstPtr img_ptr = m.instantiate<sensor_msgs::CompressedImage>();
        try{
          cv_bridge_ptr = cv_bridge::toCvCopy(img_ptr);
        } catch(cv_bridge::Exception& e){
          std::cout << "\033[1;33mcv_bridge exception: " << e.what() << "\033[0m\n";
          exit(EXIT_FAILURE);
        }
      }
      // Make sure is color image topic
      if((!is_compressed and cv_bridge_ptr->encoding=="rgb8") or \
          (is_compressed and cv_bridge_ptr->encoding=="bgr8") and \
          !has_data){
        has_data = true; topic_name = m.getTopic();
      }
      // Make sure is the same topic
      if(m.getTopic()!=topic_name) continue;
      double read_ratio = ((m.getTime() - view.getBeginTime()).toSec())/bag_duration;
      cv::Mat img;
      if(is_compressed) img = cv_bridge_ptr->image; // Don't have to convert, VideoWriter expected BGR image as input
      else{
        cv::cvtColor(cv_bridge_ptr->image, img, CV_RGB2BGR);
      }
      printf("\r[%05.1f%%]", read_ratio*100);
      data_pair data = std::make_pair(img, unix_time2str(m.getTime()));
      data_queue.push(data);
      //data_queue.push(img);
    }
  }
  read_complete = true;
  if(topic_name.empty()){
    std::cout << "\033[0;31mNo RGB image detected in the bag, exiting...\n\033[0m";
    exit(EXIT_FAILURE);
  }
  // Wait writing thread to stop
  std::cout << "\nWriting video...\n";
  writing_thread.join();
  std::cout << "Complete!\n";
  auto e_ts = std::chrono::high_resolution_clock::now();
  auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(e_ts-s_ts).count();
  std::cout << "Conversion time: " << duration*1e-9 << " seconds\n";
}
