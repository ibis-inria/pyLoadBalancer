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
There are two reserved keys, that are 'HELLO' and 'TASK', your task dict should not contain these two keys.
When the task is to be sent, send it using :

    CL.sendTask(taskname,task)

Where taskname (string) is the name of the task (your workers should also have a function that is able to read a task having this name)
The client interface will add two keys to the task dict :
    {'HELLO' : 'TOWORKER'} in order to tell the Load Balancer that this is a task to be done by a Worker.
    {'TASK' : taskname} to describe the task to be done by the worker

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
        self.pushSock = self.context.socket(zmq.PUSH)
        self.pushSock.connect('tcp://'+self.CONSTANTS['LB_IP']+':'+str(self.CONSTANTS['LB_CLIENTPULLPORT']))

    def sendTask(self,taskname,taskdict):
        if ('TASK' in taskdict):
            print(self.CONSTANTS['FAIL'], 'ERROR - YOUR TASK DICT SHOULD NOT CONTAIN A KEY NAMED TASK', self.CONSTANTS['ENDC'])
            return
        if ('HELLO' in taskdict):
            print(self.CONSTANTS['FAIL'], 'ERROR - YOUR TASK DICT SHOULD NOT CONTAIN A KEY NAMED HELLO',
                  self.CONSTANTS['ENDC'])
            return
        taskdict['TASK'] = taskname
        taskdict['HELLO'] = 'TOWORKER'
        self.pushSock.send_json(taskdict)