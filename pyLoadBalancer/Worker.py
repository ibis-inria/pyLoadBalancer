#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module describes a Worker Node.
Import the worker class into project, and it will automatically connect to the LoadBalancer.

To create a worker, use the following syntax :

    from JSONLoadBalancer import Worker
    WK = Worker(id, lbport, healthport)

Where :
  - id (string) is the worker unique id.
  - lbport (int) and healthport (int) are two ports listened by the worker in order to receive task from the Load Balancer and receive message from the Health Check

Then you will add tasks the worker should do.

    WK.addTask('DIAG',diagTask)

Here, when the worker receive a task named 'DIAG', it will call the diagTask function.
A task function must be in the form taskFunction(**kwargs):
    the first kwargs argurments will be kwargs['task'] and contains the task message coming from the Client.

Then, when all tasks are defined, start the worker using :
    WK.startWK()
"""

import time
import json
import zmq
import os.path
import psutil
import sys



__all__ = ['Worker'] #Only possible to import Client


with open(  os.path.join(os.path.dirname(__file__),'parameters.json') , 'r') as fp:
    CONSTANTS = json.load(fp)


class Worker:
    def __init__(self, id, lbrepport, healthport, priority = 0):
        self.setProcessPriority(priority)

        self.id = id
        self.taskList = {}

        self.context = zmq.Context()
        self.lbrepport = lbrepport
        self.healthport = healthport

        self.pushStateSock = self.context.socket(zmq.PUSH)
        self.pushStateSock.connect('tcp://' + CONSTANTS['LB_IP'] + ':' + str(CONSTANTS['LB_WKPULLPORT']))

        self.LBrepSock = self.context.socket(zmq.REP)
        self.LBrepSock.bind('tcp://' + CONSTANTS['WK_IP'] + ':' + str(self.lbrepport))

        self.HCrepSock = self.context.socket(zmq.REP)
        self.HCrepSock.bind('tcp://' + CONSTANTS['WK_IP'] + ':' + str(self.healthport))

        self.poller = zmq.Poller()
        self.poller.register(self.LBrepSock, zmq.POLLIN)
        self.poller.register(self.HCrepSock, zmq.POLLIN)


    def setProcessPriority(self, priority):
        """ Set the priority of the process to below-normal."""

        if abs(priority) > 20:
            return
        self.priority = priority
        try:
            sys.getwindowsversion()
        except:
            isWindows = False
        else:
            isWindows = True

        p = psutil.Process()

        if isWindows:
            if priority == 0:
                p.nice(psutil.NORMAL_PRIORITY_CLASS)
            elif priority < 0:
                p.nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
            elif priority > 0:
                p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        else:
            p.nice(priority)

    def sayHello(self):
        self.sendState("HELLO")

    def addTask(self, taskname, taskfunct, **kwargs):
        if taskname not in self.taskList:
            self.taskList[taskname] = {'funct':taskfunct, 'kwargs':kwargs}
        else:
            print(CONSTANTS['FAIL'],'TASK %s ALREADY EXISTS, SKIPPING addTask' % taskname,CONSTANTS['ENDC'])

    def rmvTask(self, taskname):
        if taskname in self.taskList:
            del self.taskList[taskname]

    def sendState(self, percentDone, to='LB'):
        message = {'workerid': self.id, 'workerip': CONSTANTS['WK_IP'], 'workerport': self.lbrepport,
                                 'workerhealthport': self.healthport, 'workerstate': percentDone, 'workerpriority' : self.priority}
        if to == 'LB':
            self.pushStateSock.send_json(message)
        if to == 'HEALTH':
            # print(self.id, " - Sending progress state to HEALTH : ", self.percentDone)
            self.pushStateSock.send_json(message)

    def sendCPUState(self, to='LB'):
        cpustate = psutil.cpu_percent()
        if cpustate == 0:
            return
        message = {'workerid': self.id, 'CPUonly': True, 'workercpustate': cpustate}
        if to == 'LB':
            self.pushStateSock.send_json(message)
        if to == 'HEALTH':
            # print(self.id, " - Sending progress state to HEALTH : ", self.percentDone)
            self.pushStateSock.send_json(message)

    def startWK(self):
        print(CONSTANTS['OKGREEN'], 'WORKER ', self.id, ' WITH PRIORITY %d STARTED on %s | LBrepPort : %d | HCrepPort : %d' % (self.priority, CONSTANTS['WK_IP'],self.lbrepport,self.healthport), CONSTANTS['ENDC'])

        while True:
            self.sayHello()
            sockets = dict(self.poller.poll(10000))
            if not sockets:
                print(CONSTANTS['OKBLUE'], self.id, ' - ', time.time(), ' - NOTHING TO DO', CONSTANTS['ENDC'])
                self.sendCPUState()
                self.sendState(100)

            if self.LBrepSock in sockets:
                msg = self.LBrepSock.recv_json()
                # print(id, " received %r" % msg)
                if msg['TASK'] == 'READY?':
                    self.LBrepSock.send_json(CONSTANTS['WK_OK'])

                elif msg['TASK'] == 'EXIT':
                    self.LBrepSock.send_json(CONSTANTS['WK_OK'])
                    break

                elif msg['TASK'] in self.taskList:
                    msg.pop('HELLO')
                    self.LBrepSock.send_json(CONSTANTS['WK_OK'])
                    #SENDING TASK TO TASK FUNCTION
                    self.taskList[msg['TASK']]['funct'](task=msg,arguments=self.taskList[msg['TASK']]['kwargs'])
                else:
                    print(CONSTANTS['FAIL'], 'WORKER ', self.id, ' UNKNOWN COMMAND ', msg['TASK'], CONSTANTS['ENDC'])
                    self.LBrepSock.send_json(CONSTANTS['WK_ERROR'])
                self.sendCPUState()
                self.sendState(100)


            if self.HCrepSock in sockets:
                msg = self.HCrepSock.recv_json()
                if msg['HEALTH'] == 'CHECKWORKERS' and ('workerid' in msg):
                    self.HCrepSock.send_json({'workerid': self.id, 'workerstate' : 100})
                else:
                    self.HCrepSock.send_json({msg['HEALTH']: 'COMMAND UNKNOWN'})
                self.sendCPUState()
        return



