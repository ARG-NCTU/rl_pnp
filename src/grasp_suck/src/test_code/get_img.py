#!/usr/bin/env python
'''
  Call service to get pointcloud and save the heightmap images
'''

import sys
import os
import rospy
from visual_system.srv import get_pc, get_pcRequest

sys.path.insert(1, os.path.join(sys.path[0], '..'))
import utils

s = rospy.ServiceProxy("/combine_pc_node/get_pc", get_pc)
req = get_pcRequest()
req.file_name = "/home/sean/Documents/flip_obj/src/grasp_suck/src/test.pcd"
res = s(req)

color, depth, points, msg = utils.get_heightmap(res.pc, "", 100)
print points[160][160]
