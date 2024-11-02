intent_recognition_template = """<|begin_of_text|><|start_header_id|>system<|end_header_id|> You are a helpful AI 
assistant to help recognize the intention(Task, Dialogue) of the user only output these two intentions and output in 
json format. { \"intention\": \"{intention}\", \"content\": \"{
content}\"}<|eot_id|><|start_header_id|>user<|end_header_id|> What can you do for 
me?<|eot_id|><|start_header_id|>assistant<|end_header_id|> {\"intention\": \"Dialogue\", \"content\": \"What can you 
do for me\"}<|eot_id|><|start_header_id|>user<|end_header_id|> Follow my instructions to finish the task: go to the 
kitchen and stop at the fridge<|eot_id|><|start_header_id|>assistant<|end_header_id|> {\"intention\": \"Task\", 
\"content\": \"go to the kitchen and stop at the fridge\"}<|eot_id|><|start_header_id|>user<|end_header_id|>"""

system_principle = """
Here are some tips for you to finish point navigation
"""

NavPoint_simple_prompt = ''' Instruct: Starting from viewpoint(0915e34d-80cb-4a0a-808a-8c9793e052d2), go out to the door and turn left, forward to the whiteboard and stop at the it.
> think: To follow the instructions, I should take photos to understand surroundings to find a door
OK.
> Tool calls: detect_surroundings()
I have scan the surroundings and get photos at the viewpoint(0915e34d-80cb-4a0a-808a-8c9793e052d2)
> think: Now, I need to find the door and get its depth.
OK.
> Tool calls: depth_estimate('door')
The depth is 5m away, and the coordinates of the door in the world coordinate is about x=1.5, y=1.5. The door is appear in the first image. So I do not need to rotate to correct my pose. I need to find the next optimum viewpoints.
> Tool calls: find_viewpoint(0915e34d-80cb-4a0a-808a-8c9793e052d2, 1.5, 1.23)
The proper viewpoint is xvcbbgfdgf1.
> Tool calls: navigate(lknvm1sffdh, lknvm1sffdh, NO_CHANGED_POSE)
You are arrive at (lknvm1sffdh) with current pose.
> think: Okay, I have found a door in the first photo, so do not need to rotate and the door is about 2.5 meters away, the coordinates of the door in the world coordinate is about x=1.5, y=1.23.
OK.

> think: Okay. I should go there.
OK.
> Tool calls: navigate(lknvm1sffdh, xvcbbgfdgf1, NO_CHANGED_POSE)
You are arrive at (xvcbbgfdgf1) with current pose.
> think: Okay, after go out of the door, I need to turn left.
OK.
> Tool calls: navigate(xvcbbgfdgf1, xvcbbgfdgf1, TURN_LEFT, 90) 
you are arrive at (xvcbbgfdgf1) meanwhile turn left 90 degrees.
> think: I have turned right, now I need to detect surroundings to find a whiteboard.
Ok.
> Tool calls: detect_surroundings(whiteboard)
There is a whiteboard in the fourth photo, so I need to rotate 90 to right. And the door is about 3 meters away, the coordinates of the door in the world coordinate is about x=-3.7 , y=4.
> think: I need to get back to the pose I had when I took the fourth picture, I need to turn left 90 degree.
OK.
> Tool calls: navigate(xvcbbgfdgf1, xvcbbgfdgf1, TURN_LEFT, 90)
You are arrive at (xvcbbgfdgf1) meanwhile turn left 90 degrees.
> think: okay, I have found the whiteboard, and the door is about 3 meters away, the coordinates of the door in the world coordinate is about x=-3.7 , y=4.
OK.
> think Okay, now I need to find the closet viewpoint.
OK.
> Tool calls: find_viewpoint(xvcbbgfdgf1, 3.7, 4)
The proper viewpoint is xcbvn1.
> think: Okay. I should go there.
OK.
> Tool calls: navigate(xvcbbgfdgf1, xcbvn1, no_changed_pose)
You are arrive at (xcbvn1) with current pose.
> think: Okay, I have already been near the whiteboard. Lets me think whether I am close enough.
OK.
> Tool calls: detect_surroundings(whiteboard) 
There is a whiteboard in the first photo, and the depth of the white board is 0.5m. he coordinates of the door in the world coordinate is about x=-3.7 , y=4.
> think: Okay, I am close enough. Task Completed.
OK.
'''