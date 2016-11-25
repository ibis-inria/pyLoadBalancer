#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module describes a Worker Node.
Import the worker class into project, and it will automatically connect to the LoadBalancer.

To create a worker, use the following syntax :

    from JSONLoadBalancer import Worker
    WK = Worker(id, lbport, healthport, [minpriority=0 ,maxpriority=0])

Where :
  - id (string) is the worker unique id.
  - lbport (int) and healthport (int) are two ports listened by the worker in order to receive task from the Load Balancer and receive message from the Health Check
  - minpriority (int) and maxpriority (int) are the min and max task priority the worker can work on

Then you will add tasks names the worker should understand.

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
import multiprocessing



__all__ = ['Worker'] #Only possible to import Client

class Worker:
    def __init__(self, id, processpriority = 0, mintaskpriority=0, maxtaskpriority=0):
        self.setProcessPriority(processpriority)
        self.mintaskpriority = mintaskpriority
        self.maxtaskpriority = maxtaskpriority

        self.id = id
        self.taskList = {}

        self.process = None
        self.workingprocess = None
        self.state = 100
        self.workingon = None

    def addTask(self, taskname, taskfunct, **kwargs):
        if taskname not in self.taskList:
            self.taskList[taskname] = {'funct':taskfunct, 'kwargs':kwargs}
        else:
            cprint('TASK %s ALREADY EXISTS, SKIPPING addTask' % taskname, 'FAIL')

    def rmvTask(self, taskname):
        if taskname in self.taskList:
            del self.taskList[taskname]

    def setProcessPriority(self, priority):
        """ Set the priority of the process to below-normal."""

        if abs(priority) > 20:
            return
        self.processpriority = priority
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

    def processtask(self,taskfunct,resultdict,id,**kwargs):
        resultdict[id] = taskfunct(**kwargs)

def processloop():
    while True:
        time.sleep(0.1)


class WorkerStack:
    def __init__(self, ip, lbrepport, healthport, parametersfile=None):
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

        self.ip = ip
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

        self.manager = multiprocessing.Manager()
        self.taskresult = self.manager.dict()
        self.workers = {}

    def sayHello(self):
        self.sendState("HELLO")

    def sendState(self, percentDone, resultmessage=None, taskid=None, to='LB'):
        message = {'workerid': self.id, 'workerip': self.ip, 'workerport': self.lbrepport,
                   'workerhealthport': self.healthport, 'workerstate': percentDone,
                   'workerpriority' : self.processpriority, 'minpriority' : self.mintaskpriority, 'maxpriority' : self.maxtaskpriority,
                   'workerresult': resultmessage, 'taskid' : taskid}
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

    def flushsockets(self):
        socketstoflush = dict(self.poller.poll(50))
        #print('SOCKET TO FLUSH', socketstoflush)

        while socketstoflush:
            if self.LBrepSock in socketstoflush:
                #print('FLUSHED : ',self.LBrepSock.recv_json())
                try:
                    self.LBrepSock.recv_json()
                    self.LBrepSock.send_json({'WK':'FLUSHED'})
                except:
                    break
                    pass
            elif self.HCrepSock in socketstoflush:
                #print('FLUSHED : ',self.HCrepSock.recv_json())
                try:
                    self.HCrepSock.recv_json()
                    self.HCrepSock.send_json({'WK':'FLUSHED'})
                except:
                    break
                    pass
            else:
                print('UNRECOGNIZED SOCKET')
                break
            socketstoflush = dict(self.poller.poll(50))

    '''
    Starts the stack of workers.
    Option is a dict with the following structure :
    {
        "idworker1" : {mintaskpriority=0, maxtaskpriority=0} ,
        "idworker2" : {mintaskpriority=0, maxtaskpriority=0} ,
        ..
    }
    '''

    def startWKstack(self,options):
        cprint('Starting WorkerStack :', 'OKGREEN')
        print(bcolors.OKBLUE, '    IP:', bcolors.ENDC, self.ip)
        print(bcolors.OKBLUE, '    LBport:', bcolors.ENDC, self.lbrepport)
        print(bcolors.OKBLUE, '    HCport:', bcolors.ENDC, self.healthport)
        print(bcolors.OKBLUE, '    Options:', bcolors.ENDC, options)

        for wkid in options :
            processpriority = options[wkid].get('processpriority',0)
            mintaskpriority = options[wkid].get('mintaskpriority',0)
            maxtaskpriority = options[wkid].get('maxtaskpriority',0)

            self.workers[wkid] = Worker(wkid, processpriority, mintaskpriority, maxtaskpriority)
            self.workers[wkid].process = multiprocessing.Process(target=self.workers[wkid].processloop, args=(self.taskList[msg['TASKNAME']]['funct'],self.taskresult, self.id), kwargs={'task':msg['TASK'],'arguments':self.taskList[msg['TASKNAME']]['kwargs']})

        #Start Workers

        #print(bcolors.OKBLUE, '    WK_PRIORITY:', bcolors.ENDC, self.processpriority)
        #print(bcolors.OKBLUE, '    MIN_TASK_PRIORITY:', bcolors.ENDC, self.mintaskpriority)
        #print(bcolors.OKBLUE, '    MAX_TASK_PRIORITY:', bcolors.ENDC, self.maxtaskpriority)
        for keys, values in self.CONSTANTS.items():
            print(bcolors.OKBLUE,'   ', keys, ':',bcolors.ENDC, values)

        while True:
            if self.state < 100:
                if not self.workingprocess.is_alive():
                    print("WORKER SEEMS TO BE DONE")
                    self.workingprocess.join(100)
                    print("RESULT", self.id in self.taskresult)
                    self.sendState(100,resultmessage=self.taskresult[self.id],taskid=self.workingon)
                    self.state = 100
                    self.workingon = None
                    self.taskresult[self.id] = None
                sockets = dict(self.poller.poll(100))
            else:
                sockets = dict(self.poller.poll(10000))


            if (not sockets) and (self.state == 100):
                self.sayHello()
                cprint('%s - %s - NOTHING TO DO' % (self.id, time.strftime('%H:%M:%S')), 'OKBLUE')
                self.sendCPUState()
                self.sendState(self.state)

            if self.LBrepSock in sockets:
                msg = self.LBrepSock.recv_json()
                #print("WORKER MSG", msg)

                #print(self.id, " received %r" % msg)
                if msg['TASK'] == 'CANCEL':
                    if (self.state < 100) and (self.workingprocess != None) and (self.workingprocess.is_alive()):
                        self.state = 100
                        self.LBrepSock.send_json({'WK':'OK'})
                        try:
                            self.workingprocess.terminate()
                        except:
                            pass
                        self.workingon = None
                        self.taskresult[self.id] = None
                        time.sleep(1)
                        self.state = 100
                    else:
                        self.LBrepSock.send_json({'WK':'ERROR'})

                elif (self.state < 100) and (self.workingprocess != None) and (self.workingprocess.is_alive()):
                    self.LBrepSock.send_json({'WK':'ERROR'})

                elif msg['TASK'] == 'READY?':
                    self.LBrepSock.send_json({'WK':'OK'})
                    self.sendCPUState()
                    self.sendState(self.state)

                elif msg['TASK'] == 'EXIT':
                    self.LBrepSock.send_json({'WK':'OK'})
                    break

                elif msg['TASKNAME'] in self.taskList:
                    print("WORKER RECEIVED TASK")
                    self.LBrepSock.send_json({'WK':'OK'})
                    #SENDING TASK TO TASK FUNCTION
                    #print('WORKING ON TASK',msg['taskid'])
                    self.taskresult[self.id] = None
                    self.workingprocess = multiprocessing.Process(target=self.processtask, args=(self.taskList[msg['TASKNAME']]['funct'],self.taskresult, self.id), kwargs={'task':msg['TASK'],'arguments':self.taskList[msg['TASKNAME']]['kwargs']})
                    self.state = 0
                    self.workingon = msg['taskid']
                    print("STARTING PROCESS, RESULT",self.taskresult)
                    self.workingprocess.start()
                    print("PROCESS STARTED", self.workingprocess.is_alive())
                    ##taskresult = self.taskList[msg['TASKNAME']]['funct'](task=msg['TASK'],arguments=self.taskList[msg['TASKNAME']]['kwargs'])

                    # FINISHED TASK
                    # FLUSHING SOCKETS received during calculation time
                    #self.flushsockets()

                    #print('TASK FINISHED',msg['taskid'], taskresult)
                    #self.sendCPUState()
                    #self.sendState(100,resultmessage=taskresult,taskid=msg['taskid'])


                else:
                    cprint('WORKER %s - UNKNOWN COMMAND %s'% (self.id, msg['TASKNAME']), 'FAIL')
                    self.LBrepSock.send_json({'WK':'UNKNOWN'})



            if self.HCrepSock in sockets:
                msg = self.HCrepSock.recv_json()
                if msg['HEALTH'] == 'CHECKWORKERS' and ('workerid' in msg):
                    self.HCrepSock.send_json({'workerid': self.id, 'workerstate' : 100})
                else:
                    self.HCrepSock.send_json({msg['HEALTH']: 'COMMAND UNKNOWN'})
                self.sendState(self.state)
                self.sendCPUState()
        return
