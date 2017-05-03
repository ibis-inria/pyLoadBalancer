#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module describes a Client.
The Client class sends tasks (in json format from a dict) to the LoadBalancer

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import zmq
import os.path
import json
import time
import traceback
from .colorprint import cprint
import sys

__all__ = ['Client']  # Only possible to import Client


class Client:
    def __init__(self, parametersfile=None):
        ### Constants definitions ###
        with open(os.path.join(os.path.dirname(__file__), 'parameters.json'), 'r') as fp:
            self.CONSTANTS = json.load(fp)  # Loading default constants

        if parametersfile != None:
            try:
                with open(parametersfile, 'r') as fp:
                    # updating constants with user defined ones
                    self.CONSTANTS.update(json.load(fp))
            except:
                cprint('ERROR : %s is not a valid JSON file' %
                       parametersfile, 'FAIL')
                sys.exit()

        self.context = zmq.Context()

    def openSock(self):
        pushSock = self.context.socket(zmq.REQ)
        # Time out when asking worker
        pushSock.setsockopt(zmq.RCVTIMEO, self.CONSTANTS['SOCKET_TIMEOUT'])
        pushSock.setsockopt(zmq.SNDTIMEO, self.CONSTANTS['SOCKET_TIMEOUT'])
        pushSock.setsockopt(zmq.LINGER, 0)  # Time before closing socket
        pushSock.setsockopt(zmq.REQ_RELAXED, 1)
        pushSock.connect('tcp://' + self.CONSTANTS['LB_IP'] +
                         ':' + str(self.CONSTANTS['LB_CLIENTPULLPORT']))
        return pushSock

    def resetSocket(pushSock):
        # Time out when asking worker
        self.pushSock.setsockopt(zmq.RCVTIMEO, self.CONSTANTS['LB_IP'])
        self.pushSock.setsockopt(zmq.SNDTIMEO, self.CONSTANTS['LB_IP'])
        self.pushSock.setsockopt(zmq.LINGER, 0)  # Time before closing socket
        self.pushSock.setsockopt(zmq.REQ_RELAXED, 1)
        self.pushSock.connect(
            'tcp://' + self.CONSTANTS['LB_IP'] + ':' + str(self.CONSTANTS['LB_CLIENTPULLPORT']))

    def sendTask(self, taskname, taskdict, priority=0, userid=None):
        task = {'toLB': 'NEWTASK', 'priority': priority,
                'taskdict': taskdict, 'taskname': taskname, 'userid': userid}
        for i in range(3):
            try:
                pushSock = self.openSock()
                pushSock.send_json(task)
                result = pushSock.recv_json()
                pushSock.close()
                return result
            except:
                try:
                    pushSock.close()
                except:
                    pass

                if (i >= 2):
                    print("sendTask ERROR WHILE SENDING/RECEIVING SOCKET")
                    traceback.print_exc()
                else:
                    time.sleep(1)
                pass

        return {'LB': 'ERROR'}

    def getTask(self, taskid):
        if isinstance(taskid, list):
            task = {'toLB': 'GETTASKS', 'tasksid': taskid}
        else:
            task = {'toLB': 'GETTASK', 'taskid': taskid}

        for i in range(3):
            try:
                pushSock = self.openSock()
                pushSock.send_json(task)
                result = pushSock.recv_json()
                pushSock.close()
                return result
            except:
                try:
                    pushSock.close()
                except:
                    pass

                if (i >= 2):
                    print("getTask ERROR WHILE SENDING/RECEIVING SOCKET")
                    traceback.print_exc()
                else:
                    time.sleep(1)
                pass

        return {'LB': 'ERROR'}

    def cancelTask(self, taskid):
        task = {'toLB': 'CANCELTASK', 'taskid': taskid}

        for i in range(3):
            try:
                pushSock = self.openSock()
                pushSock.send_json(task)
                result = pushSock.recv_json()
                pushSock.close()
                return result
            except:
                try:
                    pushSock.close()
                except:
                    pass

                if (i >= 2):
                    print("cancelTask ERROR WHILE SENDING/RECEIVING SOCKET")
                    traceback.print_exc()
                else:
                    time.sleep(1)
                pass

        return {'LB': 'ERROR'}
