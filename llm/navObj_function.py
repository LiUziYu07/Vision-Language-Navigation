import json
import uuid
import re
import math

import numpy as np
from sentence_transformers import SentenceTransformer

from graph.node import Node
from download.ssh import download_folders
from fusion.get_depth import run as run_depth_service
from core.task import Task, PointNav
from config.ros import ROS_IP, ROS_PORT, ROS_IMAGE_PTH, ROS_JSON_PTH, ROS_PCD_PTH, ROS_HOST_NAME
from config.nav_node_info import coordinates, node_infos, connection_matrix, uuid2timestamp
from utils.robot_requests import send_post_request, url_dict

text_embedding = SentenceTransformer('paraphrase-MiniLM-L6-v2')


def cos_simularity(embedding1, embedding2):
    return np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))


class ToolBase:
    def get_description(self):
        pass

    def execute(self, task: Task, args_str: str):
        pass


class ToolSurroundingDetect(ToolBase):
    def parser(self, args_str):
        """
            解析输入参数字符串，并返回所需的参数值。

            参数:
            - args_str (str): JSON格式的字符串，包含导航参数。

            返回值:
            - tuple: 包含起点、终点、旋转类型和旋转角度的元组。

            异常处理:
            - 如果参数字符串不是JSON格式，抛出异常。
            - 如果缺少必需的参数，抛出异常。
        """
        try:
            args = json.loads(args_str)
        except ValueError:
            raise Exception("the arguments '{}' is not a json string".format(args_str))

        if "landmark" not in args:
            raise Exception("'landmark' key is missing in the arguments.")

        return args.get("landmark")

    def execute(self, task: PointNav, args_str: str):
        landmark = self.parser(args_str)

        msgs = ""
        cur_x, cur_y, _ = task.cur_node.coordinates
        for degree in [0, 90, 90, 90, 90]:
            msgs = ""
            new_pose = task.cur_node.pose + degree
            nav_data = {
                "goal_x": str(cur_x),
                "goal_y": str(cur_y),
                "goal_z": "0",
                "rotate_degree": new_pose % 360
            }

            nav_response = send_post_request("navigate", nav_data)
            if nav_response.status_code == 200:
                if "success" in nav_response.text.lower():
                    msgs += f"I have success rotate at the current location with pose {new_pose % 360}."
                task.cur_node.update_pose(new_pose)
            else:
                msgs += f"In rotate: {nav_response.text}"

            camera_data = {
                "camera_names": ["front"],
                "analyzers": "manual"
            }

            camera_response = send_post_request("camera", camera_data)
            if camera_response.status_code == 200:
                pass
            else:
                msgs += f"In camera: {camera_response.text}"
            
            # 下载数据
            remote_dirs = [
                ROS_IMAGE_PTH,
                ROS_PCD_PTH,
                ROS_JSON_PTH
            ]
            local_base_dir = 'D:\CEG5003_PointNav\data\obs'

            # 执行下载和删除子文件夹和文件
            download_folders(ROS_IP, 22, ROS_HOST_NAME, remote_dirs, local_base_dir)
            try:
                idx, coords = run_depth_service(landmark)
                msgs += f"landmark median point in lidar coordinates x: {coords[0]}, y: {coords[1]}, z: {coords[2]}."
                break
            except Exception as e:
                msgs += f"In depth estimation: {e}"

        if msgs != "":
            return msgs
        else:
            return "I cannot find the landmark"

    def get_description(self):
        return {
            "type": "function",
            "function": {
                "name": "surrounding_detect",
                "description": "This `surround_detect` function represents detecting the surroundings of a "
                               "specific object.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "landmark": {
                            "type": "string",
                            "description": "`landmark` represents the object for which surroundings are to be detected",
                        }
                    },
                    "required": ["landmark"],
                },
            },
        }


class ToolInterestpointGet(ToolBase):
    def __init__(self):
        self.threshold = 1.5

    def parser(self, args_str):
        try:
            args = json.loads(args_str)
        except ValueError:
            raise Exception("the arguments '{}' is not a json string".format(args_str))

        required_params = ["landmark", "coord_x", "coord_y"]
        for param in required_params:
            if param not in args:
                raise Exception("parameter '{}' not found in the arguments {}.".format(param, args))

        coord_x = args.get("coord_x")
        coord_y = args.get("coord_y")

        try:
            coord_x = float(coord_x)
            coord_y = float(coord_y)
        except ValueError:
            raise Exception("coord_x and coord_y must be convertible to float.")

        return args.get("landmark"), coord_x, coord_y

    def execute(self, task: Task, args_str: str):
        landmark, coord_x, coord_y = self.parser(args_str)
        landmark_embedding = text_embedding.encode(landmark)
        dist = math.sqrt(math.pow(coord_x, 2) + math.pow(coord_y, 2))

        if dist < self.threshold:
            return "I am close enough to the target"

        unit_x = coord_x / dist
        unit_y = coord_y / dist

        new_x = coord_x - self.threshold * unit_x
        new_y = coord_y - self.threshold * unit_y

        print(f"new_x: {new_x}, new_y: {new_y}, dist: {dist}, coord_x: {coord_x}, coord_y: {coord_y}")
        
        step_size = 0.4
        
        navigate_x, navigate_y = None, None
        sign_x = 1 if new_x > 0 else -1
        sign_y = 1 if new_y > 0 else -1
        
        print(f"sign_x: {sign_x}, sign_y: {sign_y}, new_x: {new_x}, new_y: {new_y}")

        # First, test if new_x can be navigated
        lidar_data_x = {
            "goal_x": str(new_x),
            "goal_y": str(new_y),
            "goal_z": "0",
            "rotate_degree": 0
        }
        print(f"Testing new_x: {new_x}, new_y: {new_y}")
        lidar_response_x = send_post_request("plan", lidar_data_x)

        if lidar_response_x.status_code == 200 and "true" in lidar_response_x.text.lower():
            print(f"\033[94mFound accessible point at new_x: {new_x}, new_y: {new_y}\033[0m")
            navigate_x, navigate_y = new_x, new_y
        else:
            print(f"\033[91mnew_x: {new_x}, new_y: {new_y} is not accessible, proceeding with step adjustments\033[0m")
            while sign_x * new_x > 0:
                navigate_x = -sign_x * step_size + new_x
                
                cur_y = new_y
                print(f"cur_y: {cur_y}, sign_y: {sign_y}")
                while sign_y * cur_y > 0:
                    navigate_y = -sign_y * step_size + cur_y
                    
                    lidar_data = {
                    "goal_x": str(navigate_x),
                    "goal_y": str(navigate_y),
                    "goal_z": "0",
                    "rotate_degree": 0
                    }
                    print(f"Checking navigate_x: {navigate_x}, navigate_y: {navigate_y}")
                    lidar_response = send_post_request("plan", lidar_data)
                    
                    cur_y = navigate_y

                new_x = navigate_x
                if lidar_response.status_code == 200 and "true" in lidar_response.text.lower():
                    print(f"\033[94mFound accessible point: {navigate_x}, {navigate_y}\033[0m")
                    break
                else:
                    print(f"\033[91mNot accessible point: {navigate_x}, {navigate_y}\033[0m")
                    continue
        if navigate_x and navigate_y:
            point_data = {
                "point_x": navigate_x,
                "point_y": navigate_y,
                "point_z": 0,
            }
            transform_response = send_post_request("transform", point_data)
            if transform_response.status_code == 200:
                print(f"Point on the map: {transform_response.text}")
            else:
                print("Error in transformation ")
        else:
            return "there is no accessible point for the landmark."

        return transform_response.text

    def get_description(self):
        return {
            "type": "function",
            "function": {
                "name": "interestpoint_get",
                "description": "This `interestpoint_get` function represents get the next accessible viewpoint on the "
                               "topology map.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "landmark": {
                            "type": "string",
                            "description": "`landmark` represents the object for which surroundings are to be detected",
                        },
                        "coord_x": {
                            "type": "string",
                            "description": "`coord_x` represents the x coordinate of the object for which surroundings are to be detected",
                        },
                        "coord_y": {
                            "type": "string",
                            "description": "`coord_y` represents the y coordinate of the object for which surroundings are to be detected",
                        },
                    },
                    "required": ["landmark", "coord_x", "coord_y"],
                },
            },
        }


class ToolNavigate(ToolBase):
    def __init__(self) -> None:
        """
            初始化 ToolNavigate 类，并定义初始变量。
        """
        self.goal_z = 0

    def parser(self, args_str):
        """
            解析输入参数字符串，并返回所需的参数值。

            参数:
            - args_str (str): JSON格式的字符串，包含导航参数。

            返回值:
            - tuple: 包含起点、终点、旋转类型和旋转角度的元组。

            异常处理:
            - 如果参数字符串不是JSON格式，抛出异常。
            - 如果缺少必需的参数，抛出异常。
        """
        try:
            args = json.loads(args_str)
        except ValueError:
            raise Exception("the arguments '{}' is not a json string".format(args_str))

        required_params = ["coord_x", "coord_y", "rotate_degree"]
        for param in required_params:
            if param not in args:
                raise Exception("parameter '{}' not found in the arguments {}.".format(param, args))

        coord_x = float(args.get("coord_x"))
        coord_y = float(args.get("coord_y"))
        rotate_degree = float(args.get("rotate_degree"))

        return coord_x, coord_y, rotate_degree

    def execute(self, task: PointNav, args_str):
        """
           执行导航任务。

           参数:
           - task (Task): 任务对象，包含视点信息。
           - args_str (str): JSON格式的参数字符串。

           返回值:
           - str: 表示导航成功或失败的消息。

           功能描述:
           1. 解析输入参数，获取起点、终点、旋转类型和旋转角度。
           2. 验证起点和终点的有效性。
           3. 计算位移角度，根据旋转类型设置旋转角度。
           4. 构建请求负载并发送导航请求。
           5. 返回导航成功或失败的消息。

           异常处理:
           - 如果请求失败，则抛出异常。
       """
        coord_x, coord_y, rotate_degree = self.parser(args_str)
        sp_x, sp_y, _ = task.cur_node.coordinates

        delta_x = coord_x - sp_x
        delta_y = coord_y - sp_y

        if abs(delta_x) > abs(delta_y):
            if delta_x < 0:
                new_pose = 180
            else:
                new_pose = 0
        else:
            if delta_y > 0:
                new_pose = 90
            else:
                new_pose = 270

        nav_data = {
            "goal_x": str(coord_x),
            "goal_y": str(coord_y),
            "goal_z": "0",
            "rotate_degree": new_pose
        }
        nav_response = send_post_request("navigate", nav_data)

        msgs = nav_response.text
        if nav_response.status_code == 200:
            new_node = Node(node_id=str(uuid.uuid4()), coordinates=(coord_x, coord_y, 0), description="",
                            pose=new_pose)
            task.visited_graph.add_node(new_node)
            task.cur_node = new_node
            msgs = f"You have successfully navigate to point {(coord_x, coord_y)}"
        else:
            msgs += f"You failed navigate to point {(coord_x, coord_y)}"

        return msgs

    def get_description(self):
        """
            获取工具的描述信息，包括功能、参数类型和说明。

            返回值:
            - dict: 描述工具的功能和参数信息的字典。
        """
        return {
            "type": "function",
            "function": {
                "name": "navigate",
                "description": "The `navigate` function directs a robot to a specific location and orientation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "coord_x": {
                            "type": "string",
                            "description": "coord_x represents the x coordinate of the destination position on the map of the robot's "
                                           "navigation",
                        },
                        "coord_y": {
                            "type": "string",
                            "description": "coord_y represents the y coordinate of the destination position on the map of the robot's "
                                           "navigation",
                        },
                        "rotate_degree": {
                            "type": "string",
                            "description": "The `rotate_degree` parameter indicates the desired rotation angle from "
                                           "the robot's current pose, ranging between -360 and 360 degrees.",
                        }
                    },
                    "required": ["coord_x", "coord_y", "rotate_degree"],
                },
            },
        }


if __name__ == "__main__":
    task_id = uuid.uuid4()
    episode = PointNav(task_id, "ObjPointNav_trial_1",  "", "INIT",
                                coordinates, node_infos, connection_matrix, uuid2timestamp)
    episode.test()

    landmarks = ["cabinet", "green bag", "Stop Sign"]
    for landmark in landmarks:
        print(f"Trying to find a landmark: {landmark}")
        point_x, point_y, point_z = None, None, None
        surrounding_detect = ToolSurroundingDetect()
        surrounding_msgs = surrounding_detect.execute(episode, f'{{"landmark": {json.dumps(landmark)}}}')
        try:
            print(f"Surrounding Msgs: {surrounding_msgs}")

            coordinates = re.findall(r"-?\d+\.\d+", str(surrounding_msgs))
            point_x, point_y, point_z = map(float, coordinates)
        except Exception as e:
            print(e)

        if point_x and point_y:
            interestpoint_get = ToolInterestpointGet()
            next_point_interest = interestpoint_get.execute(episode,
                                                            f'{{"landmark": "{landmark}", "coord_x": {point_x}, "coord_y": {point_y}}}')

            print(f"interest point: {next_point_interest}")
            matches = re.findall(r'x=(-?[0-9.]+), y=(-?[0-9.]+), z=(-?[0-9.]+)', next_point_interest)
            if matches:
                point_x, point_y, point_z = matches[0]
            else:
                print("Unmatch Informatinon msgs")

            print(point_x, point_y)
            navi = ToolNavigate()
            navi.execute(episode, f'{{"coord_x": "{point_x}", "coord_y": "{point_y}", "rotate_degree": 90}}')