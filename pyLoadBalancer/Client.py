#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module describes a Client.
The Client class sends tasks (in json format from a dict) to the LoadBalancer

To create a client, use the following syntax :

    from JSONLoadBalancer import Client
    CL = Client()

Then create the tasks you want to send. A task is a dict that must contains a key named 'TASK' :
    task = {'data': '/scratch/data/matrix19160.npy', 'load': 12}

You can then organize your task dict as you want, as long as the Workers are programmed to be able to understand it.
When the task is to be sent, send it using :

    taskID = CL.sendTask(taskdict)

Where taskdict is a python dict describing the task to be done by the worker.
taskID is th ID of the task unique ID returned by the Load Balancer. The task can be retrieved from the Load Balancer using the following syntax :

    taskresult = CL.getTask(taskID)

If the task is done, taskresult will contain the result dict returned by the Worker.
If the task is not done, taskresult will be -1 or the completion percentage (if available)
"""

import zmq
import os.path
import json

__all__ = ['Client'] #Only possible to import Client

class Client:
    def __init__(self):
        with open(os.path.join(os.path.dirname(__file__), 'parameters.json'), 'r') as fp:
            self.CONSTANTS = json.load(fp)
        self.context = zmq.Context()
        self.pushSock = self.context.socket(zmq.REQ)
        self.pushSock.connect('tcp://'+self.CONSTANTS['LB_IP']+':'+str(self.CONSTANTS['LB_CLIENTPULLPORT']))

    def sendTask(self,taskdict,LBinfo=None):
        task = {'toLB' : 'NEWTASK', 'LBinfo':LBinfo, 'taskdict' : taskdict, 'taskname' : taskname}
        return self.pushSock.send_json(task)

    def getTask(self,taskID):
        task = {'toLB' : 'GETTASK', 'taskID':taskID}
        return self.pushSock.send_json(task)

    def cancelTask(self,taskID):
        task = {'toLB' : 'CANCELTASK', 'taskID':taskID}
        return self.pushSock.send_json(task)
