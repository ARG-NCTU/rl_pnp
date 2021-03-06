import utils
from utils import Transition

parser = utils.create_argparser()
args = parser.parse_args()
utils.show_args(args)
testing, run, use_cpu, model_str, epsilon, port, buffer_size, learning_freq, updating_freq, mini_batch_size, save_every, learning_rate, run_episode, densenet_lr, specific_tool, suction_1_memory, suction_2_memory, gripper_memory = utils.parse_input(args)

import os
import sys
import cv2
import time
import numpy as np
import torch
import rospy
import rospkg
import serial
from trainer import Trainer
from prioritized_memory import Memory

# srv
from std_srvs.srv import SetBool, SetBoolRequest, SetBoolResponse, \
                         Empty, EmptyRequest, EmptyResponse
from arm_operation.srv import agent_abb_action, agent_abb_actionRequest, agent_abb_actionResponse, \
                              publish_info, publish_infoRequest, publish_infoResponse
from visual_system.srv import get_pc, get_pcRequest, get_pcResponse, \
                              pc_is_empty, pc_is_emptyRequest, pc_is_emptyResponse, \
                              check_grasp_success, check_grasp_successRequest, check_grasp_successResponse
from visualization.srv import viz_marker, viz_markerRequest, viz_markerResponse
from grasp_suck.srv import recorder, recorderRequest, recorderResponse

# Constant
reward = 5.0
discount_factor = 0.5
iteration = 0
learned_times = 0
sufficient_exp = 0

gripper_memory_buffer   = Memory(buffer_size)
suction_1_memory_buffer = Memory(buffer_size)
suction_2_memory_buffer = Memory(buffer_size)
if port!='':
	arduino = serial.Serial(port, 115200)
else:
	arduino = None

if model_str == "" and testing: # TEST SHOULD PROVIDE MODEL
	print "\033[0;31mNo model provided, exit!\033[0m"
	os._exit(0)

# Get logger path
r = rospkg.RosPack()
package_path = r.get_path("grasp_suck")
csv_path, image_path, depth_path, mixed_paths, feat_paths, pc_path, model_path, vis_path, diff_path, check_grasp_path = utils.getLoggerPath(testing, package_path, run)

'''if run!=0:
	gripper_memory_buffer.load_memory(csv_path.replace("logger_{:03}".format(run), "logger_{:03}".format(run-1))+"gripper_memory.pkl")
	suction_1_memory_buffer.load_memory(csv_path.replace("logger_{:03}".format(run), "logger_{:03}".format(run-1))+"suction_1_memory.pkl")
	suction_2_memory_buffer.load_memory(csv_path.replace("logger_{:03}".format(run), "logger_{:03}".format(run-1))+"suction_2_memory.pkl")
'''
if suction_1_memory!="":
	suction_1_memory_buffer.load_memory(suction_1_memory)
if suction_2_memory!="":
	suction_2_memory_buffer.load_memory(suction_2_memory)
if gripper_memory!="":
	gripper_memory_buffer.load_memory(gripper_memory)

# trainer
if testing: learning_rate = 5e-5; densenet_lr = 1e-5
trainer = Trainer(reward, discount_factor, use_cpu, learning_rate, densenet_lr)

# Load model if provided
if model_str != "":
	print "[%f]: Loading provided model..." %(time.time())
	trainer.behavior_net.load_state_dict(torch.load(model_str))
	trainer.target_net.load_state_dict(trainer.behavior_net.state_dict())
	

if model_str == "":
	torch.save(trainer.behavior_net.state_dict(), model_path+"initial.pth")
	
# Service clients
vacuum_pump_control      = rospy.ServiceProxy("/vacuum_pump_control_node/vacuum_control", SetBool)
check_suck_success       = rospy.ServiceProxy("/vacuum_pump_control_node/check_suck_success", SetBool)
agent_take_action_client = rospy.ServiceProxy("/agent_server_node/agent_take_action", agent_abb_action)
calibrate_gripper_client = rospy.ServiceProxy("/change_tool_service/calibrate_gripper", SetBool)
get_pc_client            = rospy.ServiceProxy("/combine_pc_node/get_pc", get_pc)
empty_checker            = rospy.ServiceProxy("/combine_pc_node/empty_state", pc_is_empty)
check_grasp_success      = rospy.ServiceProxy("/combine_pc_node/grasp_state", check_grasp_success)
go_home                  = rospy.ServiceProxy("/agent_server_node/go_home", Empty)
go_place                 = rospy.ServiceProxy("/agent_server_node/go_place", Empty)
fixed_home               = rospy.ServiceProxy("/agent_server_node/go_home_fix_orientation", Empty)
check_if_collide_client  = rospy.ServiceProxy("/agent_server_node/check_if_collide", agent_abb_action)
publish_data_client      = rospy.ServiceProxy("/agent_server_node/publish_data", publish_info)
viz                      = rospy.ServiceProxy("/viz_marker_node/viz_marker", viz_marker)
record_bag_client        = rospy.ServiceProxy("/autonomous_recording_node/start_recording", recorder)
stop_record_client       = rospy.ServiceProxy("/autonomous_recording_node/stop_recording", Empty)

# Result list
action_list   = [] # If action valid?
target_list   = [] # Takes action at which `pixel`
position_list = [] # Takes at which `3D position`
result_list   = [] # If action success?
loss_list     = [] # Training loss
explore_list  = [] # If using explore?
return_list   = [] # Episode return
episode_list  = [] # Episode step length

# Code for calling service
def _get_pc(iteration, is_before, check_grasp=False):
	get_pc_req = get_pcRequest()
	if check_grasp:
		get_pc_req.file_name = check_grasp_path + "{:06}.pcd".format(iteration)
	elif is_before:
		get_pc_req.file_name = pc_path + "{:06}_before.pcd".format(iteration)
	else:
		get_pc_req.file_name = pc_path + "{:06}_after.pcd".format(iteration)
	return get_pc_client(get_pc_req)
def _viz(point, action, angle, valid):
	viz_req = viz_markerRequest()
	viz_req.point = utils.point_np_to_ros(point)
	viz_req.primitive = action
	viz_req.angle = angle
	viz_req.valid = valid
	viz(viz_req)
def _take_action(tool_id, point, angle):
	agent_action = agent_abb_actionRequest()
	agent_action.tool_id = tool_id
	agent_action.position = utils.point_np_to_ros(point)
	agent_action.angle = angle
	_ = agent_take_action_client(agent_action)
def _check_collide(point, angle):
	agent_action = agent_abb_actionRequest()
	agent_action.tool_id = 1
	agent_action.position = utils.point_np_to_ros(point)
	agent_action.angle = angle
	res = check_if_collide_client(agent_action)
	if res.result == "true":
		return True # Will collide
	else:
		return False # Won't collide
def _check_if_empty(pc):
	empty_checker_req = pc_is_emptyRequest()
	empty_checker_req.input_pc = pc
	return empty_checker(empty_checker_req).is_empty.data
def _check_grasp_success():
	go_home(); rospy.sleep(0.5)
	calibrate_req = SetBoolRequest()
	calibrate_res = calibrate_gripper_client(calibrate_req)
	if not calibrate_res.success: return calibrate_res.success
	check_grasp_success_request = check_grasp_successRequest()
	# Get temporary pc and save file
	_ = _get_pc(iteration, False, True)
	check_grasp_success_request.pcd_str = check_grasp_path + "{:06}.pcd".format(iteration)
	return check_grasp_success(check_grasp_success_request).is_success

cv2.namedWindow("prediction")
program_ts = time.time()
program_time = 0.0

# Initialize
go_home()
vacuum_pump_control(SetBoolRequest(False))
valid_input = None
loss_t = 0

try:
	while True:
		if iteration is not 0: 
			if arduino: arduino.write("gb 1000") # Green + buzzer for alarming resetting
			print "Return: {} | Mean Training Loss: {}".format(return_, np.mean(loss_list[loss_t:len(loss_list)])) # For recording data
			loss_t = len(loss_list)
			return_list.append(return_); 
			episode_list.append(t)
			stop_record_client()
			if valid_input: run_episode+=1 
		program_time += time.time()-program_ts
		cmd = raw_input("\033[1;34m[%f] Reset environment, if ready, press 's' to start. 'e' to exit: \033[0m" %(program_time))
		program_ts = time.time()
		if cmd == 'E' or cmd == 'e': # End
			utils.shutdown_process(program_time, action_list, target_list, result_list, loss_list, explore_list, return_list, episode_list, position_list, csv_path, suction_1_memory_buffer, suction_2_memory_buffer, gripper_memory_buffer, True)
			cv2.destroyWindow("prediction")
		elif cmd == 'V' or cmd == 'v' : # Verbose
			valid_input = False
			trainer.set_verbose(True); print "Save depth tensor for debugging"
		elif cmd == 'D' or cmd == 'd': # Disable
			valid_input = False
			trainer.set_verbose(False); print "Disable saving depth tensor"
		elif cmd == 'S' or cmd == 's': # Start
			valid_input = True
			t = 0; return_ = 0.0; is_empty = False
			record_bag_client(recorderRequest(run_episode)) # Start recording
			while is_empty is not True:
				print "\033[0;32m[%f] Iteration: %d\033[0m" %(program_time+time.time()-program_ts, iteration)
				if not testing: epsilon_ = max(epsilon * np.power(0.998, t), 0.1) # half after 350 steps
				pc_response = _get_pc(iteration, True)
				color, depth, points = utils.get_heightmap(pc_response.pc, image_path, depth_path, iteration)
				ts = time.time()
				suck_1_prediction, suck_2_prediction, grasp_prediction = trainer.forward(color, depth, is_volatile=True)
				print "Forward past: {} seconds".format(time.time()-ts)
				heatmaps, mixed_imgs = utils.save_heatmap_and_mixed(suck_1_prediction, suck_2_prediction, grasp_prediction, feat_paths, mixed_paths, color, iteration)
				# Standarize predictions to avoid bias between them
				#suck_1_prediction = utils.standarization(suck_1_prediction);suck_2_prediction = utils.standarization(suck_2_prediction)
				#grasp_prediction = utils.standarization(grasp_prediction)
				# SELECT ACTION
				if not testing: # Train
					explore, action, action_str, pixel_index, angle = utils.epsilon_greedy_policy(epsilon_, suck_1_prediction, suck_2_prediction, grasp_prediction, depth, diff_path, iteration, specific_tool)
				else: # Testing
					action, action_str, pixel_index, angle = utils.greedy_policy(suck_1_prediction, suck_2_prediction, grasp_prediction, specific_tool); explore = False
				explore_list.append(explore)
				target_list.append(pixel_index)
				position_list.append(points[pixel_index[1], pixel_index[2]])
				del suck_1_prediction, suck_2_prediction, grasp_prediction
				utils.print_action(action_str, pixel_index, points[pixel_index[1], pixel_index[2]])
				# Save (color heightmap + prediction heatmap + motion primitive and corresponding position), then show it
				visual_img = utils.draw_image(mixed_imgs[pixel_index[0]], explore, pixel_index, vis_path + "vis_{:06}.jpg".format(iteration))
				cv2.imshow("prediction", cv2.resize(visual_img, None, fx=2, fy=2)); cv2.waitKey(33)
				# Check if action valid (is NAN?)
				is_valid = utils.check_if_valid(points[pixel_index[1], pixel_index[2]])
				# Visualize in RViz
				_viz(points[pixel_index[1], pixel_index[2]], action, angle, is_valid)
				will_collide = None
				if is_valid: # Only take action if valid
					# suck_1(0) -> 3, suck_2(1) -> 2, other(2~5) (grasp) -> 1
					tool_id = (3-pixel_index[0]) if pixel_index[0] < 2 else 1
					action_list.append(pixel_index[0])
					if tool_id==1:
						will_collide = _check_collide(points[pixel_index[1], pixel_index[2]], angle)
					if not will_collide or tool_id!=1:
						_take_action(tool_id, points[pixel_index[1], pixel_index[2]], angle)
					else:
						print "Will collide, abort request!"
				else: # invalid
					action_list.append(-1); 
					if arduino: arduino.write("r 1000") # Red
					action_success = False
				if is_valid:
					if action < 2: # suction cup
						action_success = check_suck_success().success
					else: # parallel-jaw gripper
						if not will_collide:
							action_success = _check_grasp_success()
						else:
							action_success = False
				result_list.append(action_success)
				if action_success: 
					if arduino: arduino.write("g 1000")
					go_place(); fixed_home(); # Green
				else: 
					if is_valid: 
						if arduino: arduino.write("o 1000") # Orange
					fixed_home(); vacuum_pump_control(SetBoolRequest(False))
				info = publish_infoRequest(); info.execution = utils.wrap_execution_info(iteration, is_valid, pixel_index[0], action_success)
				publish_data_client(info)
				time.sleep(1.0); 
				if arduino: arduino.write("go 1000") # Remind takeing input
				# Get next images, and check if workspace is empty
				next_pc = _get_pc(iteration, False)
				next_color, next_depth, next_points = utils.get_heightmap(next_pc.pc, image_path + "next_", depth_path + "next_", iteration)
				is_empty = _check_if_empty(next_pc.pc)
				current_reward = utils.reward_judgement(reward, is_valid, action_success)
				return_ += current_reward * np.power(discount_factor, t) 
				print "\033[1;33mCurrent reward: {} \t Return: {}\033[0m".format(current_reward, return_)
				# Store transition to experience buffer
				color_name, depth_name, next_color_name, next_depth_name = utils.wrap_strings(image_path, depth_path, iteration)
				transition = Transition(color_name, depth_name, pixel_index, current_reward, next_color_name, next_depth_name, is_empty)
				if pixel_index[0] == 0:
					suction_1_memory_buffer.add(transition)
				elif pixel_index[0] == 1:
					suction_2_memory_buffer.add(transition)
				else:
					gripper_memory_buffer.add(transition)
				print "Suction_1_Buffer: {} | Suction_2_Buffer: {} | Gripper_Buffer: {}".format(suction_1_memory_buffer.length, suction_2_memory_buffer.length, gripper_memory_buffer.length)
				iteration += 1; t += 1
				################################TRAIN################################
				# Start training after buffer has sufficient experiences
				if suction_1_memory_buffer.length > mini_batch_size and \
				   suction_2_memory_buffer.length > mini_batch_size and \
				   gripper_memory_buffer.length   > mini_batch_size:
					sufficient_exp+=1
					if (sufficient_exp-1)%learning_freq==0:
						back_ts = time.time(); 
						if arduino: arduino.write("b 1000")
						learned_times += 1
						mini_batch = []; idxs = []; is_weight = []; old_q = []; td_target_list = [];
						if specific_tool is not None:
							if specific_tool == 0:
								mini_batch, idxs, is_weight = utils.sample_data(suction_1_memory_buffer, mini_batch_size)
							elif specific_tool == 1:
								mini_batch, idxs, is_weight = utils.sample_data(suction_2_memory_buffer, mini_batch_size)
							elif specific_tool == 2:
								mini_batch, idxs, is_weight = utils.sample_data(gripper_memory_buffer, mini_batch_size)
						else:
							_mini_batch, _idxs, _is_weight = utils.sample_data(suction_1_memory_buffer, mini_batch_size); mini_batch += _mini_batch; idxs += _idxs; is_weight += list(_is_weight)
							_mini_batch, _idxs, _is_weight = utils.sample_data(suction_2_memory_buffer, mini_batch_size); mini_batch += _mini_batch; idxs += _idxs; is_weight += list(_is_weight)
							_mini_batch, _idxs, _is_weight = utils.sample_data(gripper_memory_buffer, mini_batch_size);  mini_batch += _mini_batch; idxs += _idxs; is_weight += list(_is_weight)
						for i in range(len(mini_batch)):
							color = cv2.imread(mini_batch[i].color)
							depth = np.load(mini_batch[i].depth)
							pixel_index = mini_batch[i].pixel_idx
							next_color = cv2.imread(mini_batch[i].next_color)
							next_depth = np.load(mini_batch[i].next_depth)
							action_str, rotate_idx = utils.get_action_info(pixel_index)
							old_q.append(trainer.forward(color, depth, action_str, False, rotate_idx, clear_grad=True)[0, pixel_index[1], pixel_index[2]])
							td_target = trainer.get_label_value(mini_batch[i].reward, next_color, next_depth, mini_batch[i].is_empty, pixel_index[0]); td_target_list.append(td_target)
							loss_ = trainer.backprop(color, depth, pixel_index, td_target, is_weight[i], mini_batch_size, i==0, i==len(mini_batch)-1)
							loss_list.append(loss_)
						# After parameter updated, update prioirites tree
						for i in range(len(mini_batch)):
							#episode_, iter_ = utils.parse_string(mini_batch[i].color);
							color = cv2.imread(mini_batch[i].color)
							depth = np.load(mini_batch[i].depth)
							pixel_index = mini_batch[i].pixel_idx
							next_color = cv2.imread(mini_batch[i].next_color)
							next_depth = np.load(mini_batch[i].next_depth)
							td_target = trainer.get_label_value(mini_batch[i].reward, next_color, next_depth, mini_batch[i].is_empty, pixel_index[0])
							action_str, rotate_idx = utils.get_action_info(pixel_index)
							old_value = trainer.forward(color, depth, action_str, False, rotate_idx, clear_grad=True)[0, pixel_index[1], pixel_index[2]]
							print "New Q value: {:03f} -> {:03f} | TD Target: {:03f}".format(old_q[i], old_value, td_target_list[i])
							print "========================================================================================"
							#update_tree[i/5].update(idxs[i], td_target-old_value)
							if i/mini_batch_size==0 or specific_tool == 0: suction_1_memory_buffer.update(idxs[i], td_target-old_value)
							elif i/mini_batch_size==1 or specific_tool == 1: suction_2_memory_buffer.update(idxs[i], td_target-old_value)
							else: gripper_memory_buffer.update(idxs[i], td_target-old_value)
						back_t = time.time()-back_ts
						if arduino: arduino.write("b 1000");
						print "Backpropagation& Updating: {} seconds \t|\t Avg. {} seconds".format(back_t, back_t/(3*mini_batch_size))
						if learned_times % updating_freq == 0:
							print "[%f] Replace target network to behavior network" %(program_time+time.time()-program_ts)
							trainer.target_net.load_state_dict(trainer.behavior_net.state_dict())
						if learned_times % save_every == 0:
							model_name = model_path + "{}_{}.pth".format(run, iteration)
							torch.save(trainer.behavior_net.state_dict(), model_name)
							print "[%f] Model: %s saved" %(program_time+time.time()-program_ts, model_name)
		else:
			valid_input = False
			print "\033[1;33mInvalid input\033[0m"
except KeyboardInterrupt:
	stop_record_client()
	result_list.append(0)
	utils.shutdown_process(program_time, action_list, target_list, result_list, loss_list, explore_list, return_list, episode_list, position_list, csv_path, suction_1_memory_buffer, suction_2_memory_buffer, gripper_memory_buffer, False)
