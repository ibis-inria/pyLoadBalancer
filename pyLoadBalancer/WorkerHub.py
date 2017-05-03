#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module describes a WorkerHub.
The WorkerHub lanches several workers (as described in parameters.json file)
that connect to the Load Balancer automatically.

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

import time
import json
import zmq
import os.path
import psutil
import sys
import multiprocessing
import uuid
import argparse
import zmq
import atexit
import signal
from .colorprint import cprint


def workerloop(**kwargs):
    setProcessPriority(kwargs["processpriority"])
    test = 0
    if "sleep" in kwargs:
        time.sleep(kwargs["sleep"])  # sleep when start or t

    conn = kwargs["conn"]
    conn.send({"HELLO": 100})

    while True:
        msg = conn.recv()
        if ('exit' in msg):
            conn.send({'exit': True})
            while True:
                # out of main loop, waiting exit validation
                exitmsg = conn.recv()
                if ('exit' in msg):
                    break
            break
        if ('funct' in msg) and ('taskname' in msg) and ('task' in msg) and ('arguments' in msg):
            # print('WORKING ON',msg['taskname'])
            taskresult = msg['funct'](
                task=msg['task'], arguments=msg['arguments'])
            conn.send(taskresult)
        else:
            print('TASK NOT WELL FORMATTED', msg)
            conn.send({"WK": "ERROR"})


def setProcessPriority(priority):
    import sys
    import psutil
    """ Set the priority of the process."""
    if abs(priority) > 20:
        return
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


class Worker:
    def __init__(self, mintaskpriority, maxtaskpriority, processpriority):
        self.id = 'worker_' + str(uuid.uuid4())[:8]
        # self.task = manager.dict()
        # self.result = manager.dict()

        self.mintaskpriority = mintaskpriority
        self.maxtaskpriority = maxtaskpriority
        self.processpriority = processpriority

        self.startProcess()

        self.workingon = None
        self.state = 0
        self.laststate = time.time()

    def terminateProcess(self):
        if self.pid != None:
            cprint('EXITING ' + str(self.id), 'OKBLUE')
            self.parent_conn.send({'exit': False})
            time.sleep(0.2)
            exitfailed = True
            while self.parent_conn.poll():
                exitresult = self.parent_conn.recv()
                if exitresult == {'exit': True}:
                    exitfailed = False
                    self.parent_conn.send({'exit': True})
                    cprint('EXITED ' + str(self.id), 'OKGREEN')

            if exitfailed:
                try:
                    cprint('TERMINATING ' + str(self.id), 'OKBLUE')
                    self.process.terminate()
                    self.process.join(0.1)
                    if self.process.is_alive():
                        self.killProcess()
                except:
                    cprint('CAN\'T TERMINATE' + str(self.id), 'WARNING')
                    self.killProcess()
                    pass

    def killProcess(self):
        if self.pid != None:
            try:
                cprint('# Killing' + str(self.id) +
                       '(' + str(self.pid) + ')', 'WARNING')
                os.kill(self.pid, signal.SIGKILL)
            except:
                cprint('# FAILED Killing' + str(self.id) +
                       '(' + str(self.pid) + ')', 'FAIL')
                pass

    def startProcess(self, sleep=0):
        self.parent_conn, self.child_conn = multiprocessing.Pipe()
        self.process = multiprocessing.Process(target=workerloop, kwargs={
                                               'conn': self.child_conn, 'id': self.id, 'processpriority': self.processpriority, 'sleep': sleep})
        self.process.start()
        self.pid = self.process.pid


class WorkerHub:
    def __init__(self, parametersfile=None):

        with open(os.path.join(os.path.dirname(__file__), 'parameters.json'), 'r') as fp:
            self.CONSTANTS = json.load(fp)  # Loading default constants
        if parametersfile != None:
            try:
                with open(parametersfile, 'r') as fp:
                    # updating constants with user defined ones
                    self.CONSTANTS.update(json.load(fp))
            except:
                print('ERROR : %s is not a valid JSON file' % parametersfile)
                sys.exit()

        self.manager = multiprocessing.Manager()
        self.workers = {}

        self.ip = self.CONSTANTS['WKHUB_IP']
        self.context = zmq.Context()
        self.lbrepport = self.CONSTANTS['WKHUB_LBPORT']
        self.healthport = self.CONSTANTS['WKHUB_HCPORT']

        self.pushStateSock = self.context.socket(zmq.PUSH)
        self.pushStateSock.connect(
            'tcp://' + self.CONSTANTS['LB_IP'] + ':' + str(self.CONSTANTS['LB_WKPULLPORT']))

        self.LBrepSock = self.context.socket(zmq.REP)
        self.LBrepSock.bind('tcp://' + self.ip + ':' + str(self.lbrepport))

        self.HCrepSock = self.context.socket(zmq.REP)
        self.HCrepSock.bind('tcp://' + self.ip + ':' + str(self.healthport))

        self.poller = zmq.Poller()
        self.poller.register(self.LBrepSock, zmq.POLLIN)
        self.poller.register(self.HCrepSock, zmq.POLLIN)

        self.taskList = {}
        self.cpustate = psutil.cpu_percent()
        self.lastcpustate = time.time()

        atexit.register(self.terminateWKHub)
        signal.signal(signal.SIGTERM, self.terminateWKHub)
        signal.signal(signal.SIGINT, self.terminateWKHub)

        self.exiting = False

        '''def signal_handler(signum, frame):
            print('WKHUB sigterm', signum, frame)
            self.terminateWKHub()

        signal.signal(signal.SIGTERM, signal_handler)'''

    def terminateWKHub(self, *args):
        if not self.exiting:
            self.exiting = True

    def addTask(self, taskname, taskfunct, **kwargs):
        if taskname not in self.taskList:
            self.taskList[taskname] = {'funct': taskfunct, 'kwargs': kwargs}
        else:
            cprint('TASK %s ALREADY EXISTS, SKIPPING addTask' %
                   taskname, 'FAIL')

    def rmvTask(self, taskname):
        if taskname in self.taskList:
            del self.taskList[taskname]

    def sendState(self, worker, percentDone=None, resultmessage=None, taskid=None, to='LB', CPUonly=False):
        if percentDone == -1:
            message = {'workerid': worker, 'workerstate': -1}
            self.pushStateSock.send_json(message)
            return
        if isinstance(worker, str):
            worker = self.workers[worker]

        if percentDone == None:
            percentDone = worker.state

        worker.laststate = time.time()
        if CPUonly:
            message = {'workerid': worker.id, 'workerstate': 'CPUonly',
                       'workercpustate': self.cpustate}
        else:
            message = {'workerid': worker.id, 'workerip': self.ip, 'workerport': self.lbrepport,
                       'workerhealthport': self.healthport, 'workerstate': percentDone,
                       'workerpriority': worker.processpriority, 'minpriority': worker.mintaskpriority, 'maxpriority': worker.maxtaskpriority,
                       'workerresult': resultmessage, 'taskid': taskid, 'workercpustate': self.cpustate, 'workingon': worker.workingon}

        if to == 'LB':
            self.pushStateSock.send_json(message)

    def startWKHUB(self):

        cprint('Starting Worker Hub', 'OKGREEN')
        cprint('   WKHUB_IP:', 'OKBLUE', self.ip)
        cprint('   WKHUB_LBport:', 'OKBLUE', self.lbrepport)
        cprint('   WKHUB_HCport:', 'OKBLUE', self.healthport)

        for keys, values in self.CONSTANTS.items():
            cprint('   ' + str(keys) + ':', 'OKBLUE', values)

        for workerinfo in self.CONSTANTS['WKHUB_WORKERS']:
            for n in range(workerinfo["nWorkers"]):
                worker = Worker(
                    workerinfo["minP"], workerinfo["maxP"], workerinfo["processP"])
                self.workers[worker.id] = worker

        while True:
            if self.exiting:
                cprint("EXITING Worker Hub", "OKBLUE")
                for workerid in self.workers:
                    self.workers[workerid].terminateProcess()
                time.sleep(2)
                break

            if time.time() - self.lastcpustate > 0.5:
                self.cpustate = psutil.cpu_percent()
                self.lastcpustate = time.time()

            sockets = dict(self.poller.poll(200))

            for workerid in self.workers:
                if not self.workers[workerid].process.is_alive() and not self.exiting:
                    #print('RESTARTING WORKER PROCESS',self.workers[workerid].id)
                    self.workers[workerid].startProcess(3)

                # getting worker results
                while self.workers[workerid].parent_conn.poll():
                    result = self.workers[workerid].parent_conn.recv()
                    if result == {"HELLO": 100}:
                        self.workers[workerid].state = 100
                        self.workers[workerid].workingon = None
                        self.sendState(workerid, "HELLO")
                    else:
                        self.workers[workerid].state = 100
                        self.sendState(workerid, resultmessage=result,
                                       taskid=self.workers[workerid].workingon)
                        self.workers[workerid].workingon = None

                if (not sockets) and (self.workers[workerid].state == 100):
                    if (self.workers[workerid].laststate + 1 < time.time()):
                        # print('%s - %s - NOTHING TO DO' % (self.workers[workerid].id, time.strftime('%H:%M:%S')))
                        self.sendState(workerid, "UP")
                        # self.sendCPUState(workerid,cpustate)
                       # self.sendState(self.workers[workerid].state,workerid)

            if self.LBrepSock in sockets:
                # print('RECEIVING')
                msg = self.LBrepSock.recv_json()
                # print("WORKER MSG", msg)
                if ('workerid' not in msg) or (msg['workerid'] not in self.workers):
                    print("UNKNOWN WORKER", msg.get('workerid'))
                    self.LBrepSock.send_json({'WK': 'DOWN'})

                else:
                    worker = self.workers[msg['workerid']]
                    # print(self.id, " received %r" % msg)
                    if msg['TASK'] == 'CANCEL':
                        if (msg['taskid'] == worker.workingon) or (worker.workingon == None):
                            worker.terminateProcess()
                            self.LBrepSock.send_json({'WK': 'OK'})
                        else:
                            print(msg['workerid'], 'NOT WORKING ON', msg['taskid'], 'but',
                                  worker.workingon,  msg['taskid'] == msg['workerid'])
                            self.LBrepSock.send_json({'WK': 'ERROR'})

                    elif (worker.state < 100) and (worker.workingon != None):
                        print("WORKER ALREADY WORKING", msg['workerid'])
                        self.LBrepSock.send_json({'WK': 'ERROR'})

                    elif msg['TASK'] == 'READY?':
                        self.LBrepSock.send_json({'WK': 'OK'})
                        self.sendState(worker)

                    elif msg['TASK'] == 'EXIT':
                        self.LBrepSock.send_json({'WK': 'OK'})
                        for workerid in self.workers:
                            self.workers[workerid].terminateProcess()
                        break

                    elif msg['TASKNAME'] in self.taskList:
                        self.LBrepSock.send_json({'WK': 'OK'})
                        # SENDING TASK TO TASK FUNCTION
                        worker.parent_conn.send({'funct': self.taskList[msg['TASKNAME']]['funct'], 'taskname': msg['TASKNAME'],
                                                 'task': msg['TASK'], 'arguments': self.taskList[msg['TASKNAME']]['kwargs']})
                        # self.workingprocess = multiprocessing.Process(target=self.processtask, args=(self.taskList[msg['TASKNAME']]['funct'],self.taskresult, self.id), kwargs={'task':msg['TASK'],'arguments':self.taskList[msg['TASKNAME']]['kwargs']})
                        worker.state = 0
                        worker.workingon = msg['taskid']
                        # taskresult = self.taskList[msg['TASKNAME']]['funct'](task=msg['TASK'],arguments=self.taskList[msg['TASKNAME']]['kwargs'])

                    else:
                        print('WORKER %s - UNKNOWN COMMAND %s' %
                              (worker.id, msg['TASKNAME']))
                        self.LBrepSock.send_json({'WK': 'UNKNOWN'})

            if self.HCrepSock in sockets:
                msg = self.HCrepSock.recv_json()
                # print("WK: HCmsg")
                if msg['HEALTH'] == 'CHECKWORKERS' and ('workerid' in msg):
                    if isinstance(msg['workerid'], list):
                        wkresponse = {}
                        for workerid in msg['workerid']:
                            if workerid in self.workers:
                                wkresponse[workerid] = self.workers[workerid].state
                                self.sendState(workerid, CPUonly=True)
                        self.HCrepSock.send_json(wkresponse)
                    else:
                        self.HCrepSock.send_json(
                            {msg['HEALTH']: 'workerid MUST BE LIST'})

                else:
                    self.HCrepSock.send_json(
                        {msg['HEALTH']: 'COMMAND UNKNOWN'})


if __name__ == "__main__":
    print('Please start workerHub using a Python Script')
