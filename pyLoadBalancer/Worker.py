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
from .colorprint import cprint, bcolors



__all__ = ['Worker'] #Only possible to import Client

class Worker:
    def __init__(self, id, ip, lbrepport, healthport, priority = 0, parametersfile=None):
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

        self.setProcessPriority(priority)

        self.id = id
        self.ip = ip
        self.taskList = {}

        self.context = zmq.Context()
        self.lbrepport = lbrepport
        self.healthport = healthport

        self.pushStateSock = self.context.socket(zmq.PUSH)
        self.pushStateSock.connect('tcp://' + self.CONSTANTS['LB_IP'] + ':' + str(self.CONSTANTS['LB_WKPULLPORT']))

        self.LBrepSock = self.context.socket(zmq.REP)
        self.LBrepSock.bind('tcp://' + ip + ':' + str(self.lbrepport))

        self.HCrepSock = self.context.socket(zmq.REP)
        self.HCrepSock.bind('tcp://' + ip + ':' + str(self.healthport))

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
            cprint('TASK %s ALREADY EXISTS, SKIPPING addTask' % taskname, 'FAIL')

    def rmvTask(self, taskname):
        if taskname in self.taskList:
            del self.taskList[taskname]

    def sendState(self, percentDone, to='LB'):
        message = {'workerid': self.id, 'workerip': self.ip, 'workerport': self.lbrepport,
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
        cprint('Starting Worker %s : '%self.id, 'OKGREEN')
        print(bcolors.OKBLUE, '    WK_IP:', bcolors.ENDC, self.ip)
        print(bcolors.OKBLUE, '    WK_LBport:', bcolors.ENDC, self.lbrepport)
        print(bcolors.OKBLUE, '    WK_HCport:', bcolors.ENDC, self.healthport)
        print(bcolors.OKBLUE, '    WK_PRIORITY:', bcolors.ENDC, self.priority)
        for keys, values in self.CONSTANTS.items():
            print(bcolors.OKBLUE,'   ', keys, ':',bcolors.ENDC, values)

        while True:
            self.sayHello()
            sockets = dict(self.poller.poll(10000))
            if not sockets:
                cprint('%s - %s - NOTHING TO DO' % (self.id, time.strftime('%H:%M:%S')), 'OKBLUE')
                self.sendCPUState()
                self.sendState(100)

            if self.LBrepSock in sockets:
                msg = self.LBrepSock.recv_json()
                # print(id, " received %r" % msg)
                if msg['TASK'] == 'READY?':
                    self.LBrepSock.send_json({'WK':'OK'})

                elif msg['TASK'] == 'EXIT':
                    self.LBrepSock.send_json({'WK':'OK'})
                    break

                elif msg['TASK'] in self.taskList:
                    msg.pop('HELLO')
                    self.LBrepSock.send_json({'WK':'OK'})
                    #SENDING TASK TO TASK FUNCTION
                    self.taskList[msg['TASK']]['funct'](task=msg,arguments=self.taskList[msg['TASK']]['kwargs'])
                else:
                    cprint('WORKER %s - UNKNOWN COMMAND %s'% (self.id, msg['TASK']), 'FAIL')
                    self.LBrepSock.send_json({'WK':'ERROR'})
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



