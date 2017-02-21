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

    taskid = CL.sendTask(taskdict)

Where taskdict is a python dict describing the task to be done by the worker.
taskid is th ID of the task unique ID returned by the Load Balancer. The task can be retrieved from the Load Balancer using the following syntax :

    taskresult = CL.getTask(taskid)

If the task is done, taskresult will contain the result dict returned by the Worker.
If the task is not done, taskresult will be -1 or the completion percentage (if available)
"""

import zmq
import os.path
import json
import time
import traceback

__all__ = ['Client'] #Only possible to import Client

class Client:
    def __init__(self, parametersfile = None):
        ### Constants definitions ###
        with open(os.path.join(os.path.dirname(__file__), 'parameters.json'), 'r') as fp:
            self.CONSTANTS = json.load(fp) #Loading default constants

        if parametersfile != None:
            try:
                with open(parametersfile, 'r') as fp:
                    self.CONSTANTS.update(json.load(fp)) #updating constants with user defined ones
            except:
                cprint('ERROR : %s is not a valid JSON file'%parametersfile, 'FAIL')
                sys.exit()

        self.context = zmq.Context()

    def openSock(self):
        pushSock = self.context.socket(zmq.REQ)
        pushSock.setsockopt(zmq.RCVTIMEO, self.CONSTANTS['SOCKET_TIMEOUT'])  # Time out when asking worker
        pushSock.setsockopt(zmq.SNDTIMEO, self.CONSTANTS['SOCKET_TIMEOUT'])
        pushSock.setsockopt(zmq.LINGER, 0)  # Time before closing socket
        pushSock.setsockopt(zmq.REQ_RELAXED,1)
        pushSock.connect('tcp://'+self.CONSTANTS['LB_IP']+':'+str(self.CONSTANTS['LB_CLIENTPULLPORT']))
        return pushSock

    def resetSocket(pushSock):
        self.pushSock.setsockopt(zmq.RCVTIMEO, self.CONSTANTS['LB_IP'])  # Time out when asking worker
        self.pushSock.setsockopt(zmq.SNDTIMEO, self.CONSTANTS['LB_IP'])
        self.pushSock.setsockopt(zmq.LINGER, 0)  # Time before closing socket
        self.pushSock.setsockopt(zmq.REQ_RELAXED, 1)
        self.pushSock.connect('tcp://'+self.CONSTANTS['LB_IP']+':'+str(self.CONSTANTS['LB_CLIENTPULLPORT']))

    def sendTask(self,taskname,taskdict,priority=0):
        task = {'toLB' : 'NEWTASK', 'priority':priority, 'taskdict' : taskdict, 'taskname' : taskname}
        for i in range(3):
            try:
                pushSock = self.openSock()
                pushSock.send_json(task)
                result = pushSock.recv_json()
                pushSock.close()
                return result
            except:
                print("sendTask ERROR WHILE SENDING/RECEIVING SOCKET")
                traceback.print_exc()
                try:
                    pushSock.close()
                except:
                    pass
                time.sleep(1)
                pass

        return {'LB':'ERROR'}

    def getTask(self,taskid):
        if isinstance(taskid,list) :
            task = {'toLB' : 'GETTASKS', 'tasksid':taskid}
        else :
            task = {'toLB' : 'GETTASK', 'taskid':taskid}

        pushSock = self.openSock()

        try:
            pushSock.send_json(task)
            result = pushSock.recv_json()
            pushSock.close()
            return result
        except:
            print("getTask ERROR WHILE SENDING/RECEIVING SOCKET")
            traceback.print_exc()
            try:
                pushSock.close()
            except:
                pass
            time.sleep(0.5)
            pass

        return {'LB':'ERROR'}


    def cancelTask(self,taskid):
        task = {'toLB' : 'CANCELTASK', 'taskid':taskid}
        pushSock = self.openSock()

        try:
            pushSock.send_json(task)
            result = pushSock.recv_json()
            pushSock.close()
            return result
        except:
            print("cancelTask ERROR WHILE SENDING/RECEIVING SOCKET")
            traceback.print_exc()
            try:
                pushSock.close()
            except:
                pass
            time.sleep(0.5)
            pass

        return {'LB':'ERROR'}
