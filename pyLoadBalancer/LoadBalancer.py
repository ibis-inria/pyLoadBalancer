#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module describes the Load Balancer.
Note that all the parameters necessary for the different elements (LoadBalancer, HealthCheck, Worker, Client) to communicate are given in the 'parameters.json' file.

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
import datetime
import zmq
import os.path
import json
from .colorprint import cprint
import sys
import argparse
import uuid
import traceback
import atexit
import signal

__all__ = ['LoadBalancer']  # Only possible to import Client


def argsort(seq):
    # http://stackoverflow.com/questions/3071415/efficient-method-to-calculate-the-rank-vector-of-a-list-in-python
    return sorted(range(len(seq)), key=seq.__getitem__)


class LBWorker:
    def __init__(self, workerinfo, zmqcontext, sockettimeout):
        self.workerid = workerinfo['workerid']
        self.workerinfo = workerinfo
        self.workerstate = 100
        self.workercpustate = 100
        self.lasttasktime = time.time()
        self.taskname = None
        self.taskid = None
        self.workersocket = zmqcontext.socket(zmq.REQ)
        self.SOCKET_TIMEOUT = sockettimeout
        self.resetWorkerSocket()

    def resetWorkerSocket(self):
        # Time out when asking worker
        self.workersocket.setsockopt(zmq.RCVTIMEO, self.SOCKET_TIMEOUT)
        self.workersocket.setsockopt(zmq.SNDTIMEO, self.SOCKET_TIMEOUT)
        # Time before closing socket
        self.workersocket.setsockopt(zmq.LINGER, 0)
        self.workersocket.setsockopt(zmq.REQ_RELAXED, 1)
        self.workersocket.connect(
            'tcp://' + self.workerinfo['workerip'] + ':' + str(self.workerinfo['workerport']))

    def refreshState(self):  # def askWorkerReady(self,workerid):
        try:
            self.lasttasktime = time.time()
            self.workersocket.send_json(
                {'TASK': 'READY?', 'workerid': self.workerid})
            self.workersocket.recv_json()
            return

        except Exception as e:
            return False
            # TO DO : DELETE WORKER del self.workers[workerid]
            cprint('LB - REMOVING WORKER %s - NO ANSWER TO READY QUESTION : %s' %
                   (workerid, str(e)), 'FAIL')
            pass


class LBTask:
    def __init__(self, taskid, taskname, taskdict, priority, userid):
        self.taskid = taskid
        self.taskname = taskname
        self.taskdict = taskdict
        self.priority = priority
        self.submissiontime = time.time()
        self.progress = 0
        self.workerresult = None
        self.resulttime = None
        self.deletetime = time.time() + 48 * 60 * 60  # autodelete in 48 hours
        self.userid = userid


class LBQueue:
    def __init__(self):
        self.tasks = []
        self.maxWaitTime = 0

    def addTask(self, taskname, taskdict, priority, userid):
        taskid = str(uuid.uuid4())
        self.tasks.append(LBTask(taskid, taskname, taskdict, priority, userid))
        return taskid

    def removeTask(self, taskid):
        for i in range(len(self.tasks)):
            if (self.tasks[i].taskid == taskid):
                self.tasks.pop(i)
                return True
        else:
            return False


class LoadBalancer:
    def __init__(self, parametersfile=None, queues=[{'maxallowedtime': 1, 'lowP': True, 'highP': True}, {'maxallowedtime': 1e10, 'lowP': True, 'highP': False}]):

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

        cprint('Starting Load Balancer with the folllowing settings : ', 'OKGREEN')
        for keys, values in self.CONSTANTS.items():
            cprint('   ' + str(keys) + ':', 'OKBLUE', values)

        self.workers = {}

        self.queue = LBQueue()
        self.pendingtasks = {}
        self.donetasks = {}
        self.cancelledtasks = {}

        self.context = zmq.Context()

        self.workerStateSock = self.context.socket(zmq.PULL)
        self.workerStateSock.bind(
            "tcp://" + self.CONSTANTS['LB_IP'] + ":" + str(self.CONSTANTS['LB_WKPULLPORT']))

        self.clientSock = self.context.socket(zmq.REP)
        self.clientSock.bind(
            "tcp://" + self.CONSTANTS['LB_IP'] + ":" + str(self.CONSTANTS['LB_CLIENTPULLPORT']))

        self.healthSock = self.context.socket(zmq.REP)
        self.healthSock.bind(
            "tcp://" + self.CONSTANTS['LB_IP'] + ":" + str(self.CONSTANTS['LB_HCREPPORT']))

        self.poller = zmq.Poller()
        self.poller.register(self.workerStateSock, zmq.POLLIN)
        self.poller.register(self.healthSock, zmq.POLLIN)
        self.poller.register(self.clientSock, zmq.POLLIN)

        self.lastdisplay = time.time()
        self.lastresultdelete = time.time()

        self.stats = {}

        self.exiting = False
        atexit.register(self.on_exit)
        signal.signal(signal.SIGTERM, self.on_exit)
        signal.signal(signal.SIGINT, self.on_exit)

    def on_exit(self, *args):
        self.exiting = True

    def addWorker(self, workerinfo):
        self.workers[workerinfo['workerid']] = LBWorker(
            workerinfo, self.context, self.CONSTANTS['SOCKET_TIMEOUT'])

    def removeWorker(self, workerid):
        if workerid in self.workers:
            print("TASK IN CURRENT PENDING:", self.workers[workerid].taskid)
            if self.workers[workerid].taskid in self.pendingtasks:
                self.queue.tasks.insert(0, self.pendingtasks.pop(
                    self.workers[workerid].taskid))
                self.queue.tasks[0].workerid = None
                print("TASK", self.workers[workerid].taskid,
                      "PENDING ON", workerid, "IN QUEUE AGAIN")
            self.workers.pop(workerid)

    def sendTasks(self):
        if len(self.queue.tasks) < 1:
            return
        for workerid in self.sortedworkersid:

            # there is at least a free worker
            if self.workers[workerid].workerstate >= 100:
                # selecting tasks that are within worker priority boundaries
                queingtasks = [{'index': i, 'userid': t.userid} for i, t in enumerate(self.queue.tasks) if (t.priority >= self.workers[workerid].workerinfo['minpriority']) and (
                    t.priority <= self.workers[workerid].workerinfo['maxpriority'])]
                if len(queingtasks) < 1:
                    continue

                # listing users currently using workers (pendingtasks) and make
                # a priority list
                pendingusers = [
                    self.pendingtasks[t].userid for t in self.pendingtasks]
                userpriority = {uid: pendingusers.count(
                    uid) for uid in set(pendingusers)}

                # listing users in quening tasks, sort them by priority
                queingusers = list(
                    set([taskinfo.get('userid') for taskinfo in queingtasks]))
                queingusers.sort(key=lambda uid: userpriority.get(uid, 0))

                for taskinfo in queingtasks:
                    # Send first task corresponding to highest priority user
                    if (taskinfo.get('userid') == queingusers[0]):
                        i = taskinfo.get('index')
                        task = self.queue.tasks[i]
                        try:
                            self.workers[workerid].workerstate = 0
                            # print('SENDING TASK', task.taskid, 'TO', workerid)
                            # print(datetime.datetime.now().strftime("%H:%M:%S.%f"),'SENDING
                            # TASK', task.taskid, 'TO', workerid)

                            self.workers[workerid].workersocket.send_json(
                                {'TASK': task.taskdict, 'TASKNAME': task.taskname, 'taskid': task.taskid, 'workerid': workerid})
                            answer = self.workers[workerid].workersocket.recv_json(
                            )
                            if answer == {'WK': 'OK'}:
                                waitingtime = time.time() - task.submissiontime

                                self.pendingtasks[task.taskid] = self.queue.tasks.pop(
                                    i)
                                # remove taskdict in case it is big
                                self.pendingtasks[task.taskid].workerid = workerid

                                self.workers[workerid].lasttasktime = time.time()
                                self.workers[workerid].taskname = task.taskname
                                self.workers[workerid].taskid = task.taskid

                            elif answer == {'WK': 'UNKNOWN'}:
                                cprint('LB - WORKER %s DOES NOT UNDERSAND TASK %s. REMOVING TASK' %
                                       (workerid, task.taskname), 'WARNING')
                                self.queue.tasks.pop(i)
                            else:
                                cprint('LB - WORKER %s DID NOT TAKE TASK - stay in queue' %
                                       workerid, 'WARNING')

                        except Exception as e:
                            cprint('LB - CAN\'T SEND TASK TO WORKER %s : %s' %
                                   (workerid, str(e)), 'FAIL')
                            traceback.print_exc()
                            self.workers[workerid].resetWorkerSocket()
                            pass

                        break

    def startLB(self):
        # Start the Load Balancer : listen to incoming sockets.

        while True:
            try:
                if self.exiting:
                    cprint("EXITED Load Balancer", "OKGREEN")
                    break

                sockets = dict(self.poller.poll(500))

                ###### RECEIVE INFORMATION FROM A WORKER ############
                if self.workerStateSock in sockets:
                    msg = self.workerStateSock.recv_json()
                    if ((msg['workerstate'] == "HELLO") or (msg['workerstate'] == "UP")):
                        if (msg['workerid'] not in self.workers):
                            cprint("LB - ADDING WORKER (%s)" %
                                   msg['workerid'], 'OKGREEN')
                            self.addWorker(msg)
                            self.workers[msg['workerid']].refreshState()
                        elif (msg['workerstate'] == "HELLO"):
                            cprint("LB - RECEIVED HELLO MESSAGE FROM KWONN WORKER (%s)." %
                                   msg['workerid'], 'OKBLUE')
                            self.workers[msg['workerid']
                                         ].taskname = msg['workingon']
                            self.workers[msg['workerid']
                                         ].taskid = msg['taskid']
                            self.workers[msg['workerid']].workerstate = 100
                            self.workers[msg['workerid']
                                         ].workercpustate = msg['workercpustate']

                    elif (msg['workerstate'] == -1):
                        if msg['workerid'] in self.workers:
                            cprint('LB - Worker %s is DOWN. Removing it' %
                                   msg['workerid'], 'FAIL')
                            self.removeWorker(msg['workerid'])

                    elif (msg['workerstate'] == "CPUonly"):
                        if (msg['workerid'] in self.workers):
                            self.workers[msg['workerid']
                                         ].workercpustate = msg['workercpustate']
                    else:
                        if (msg['workerid'] in self.workers):
                            self.workers[msg['workerid']
                                         ].workerstate = msg['workerstate']
                            self.workers[msg['workerid']
                                         ].workercpustate = msg['workercpustate']
                            if 'taskid' in msg:
                                if msg['taskid'] in self.pendingtasks:
                                    self.pendingtasks[msg['taskid']
                                                      ].progress = msg['workerstate']

                            if (msg['workerstate'] == 100) and (self.workers[msg['workerid']].taskname != None):
                                if msg['taskid'] != None:
                                    # print(datetime.datetime.now().strftime("%H:%M:%S.%f"),'TASK',
                                    # msg['taskid'], 'DONE')
                                    timetocomplete = time.time() - \
                                        self.workers[msg['workerid']
                                                     ].lasttasktime
                                    self.donetasks[msg['taskid']
                                                   ] = self.pendingtasks.pop(msg['taskid'])
                                    self.donetasks[msg['taskid']].timetocomplete = time.time(
                                    ) - self.workers[msg['workerid']].lasttasktime
                                    self.donetasks[msg['taskid']
                                                   ].workerresult = msg['workerresult']
                                    self.donetasks[msg['taskid']
                                                   ].resulttime = time.time()
                                    self.donetasks[msg['taskid']].deletetime = time.time(
                                    ) + 10 * 60  # result delete ten minutes

                                    self.workers[msg['workerid']
                                                 ].taskname = None
                                    self.workers[msg['workerid']].taskid = None

                                    taskname = self.donetasks[msg['taskid']].taskname
                                    waitingtime = self.workers[msg['workerid']].lasttasktime - \
                                        self.donetasks[msg['taskid']
                                                       ].submissiontime
                                    if taskname not in self.stats:
                                        self.stats[taskname] = {"totaltasks": 0, "totalcalctimes": 0,
                                                                "mincalctimes": 1e10, "meancalctimes": 0, "maxcalctimes": 0,
                                                                "minwaittimes": 1e10, "meanwaittimes": 0, "maxwaittimes": 0}

                                    self.stats[taskname]["totaltasks"] += 1
                                    self.stats[taskname]["totalcalctimes"] += self.donetasks[msg['taskid']].timetocomplete
                                    self.stats[taskname]["mincalctimes"] = min(
                                        self.stats[taskname]["mincalctimes"], self.donetasks[msg['taskid']].timetocomplete)
                                    self.stats[taskname]["maxcalctimes"] = max(
                                        self.stats[taskname]["maxcalctimes"], self.donetasks[msg['taskid']].timetocomplete)
                                    self.stats[taskname]["meancalctimes"] = ((self.stats[taskname]["totaltasks"] - 1) * self.stats[taskname]
                                                                             ["meancalctimes"] + self.donetasks[msg['taskid']].timetocomplete) / self.stats[taskname]["totaltasks"]
                                    self.stats[taskname]["minwaittimes"] = min(
                                        self.stats[taskname]["minwaittimes"], waitingtime)
                                    self.stats[taskname]["maxwaittimes"] = max(
                                        self.stats[taskname]["maxwaittimes"], waitingtime)
                                    self.stats[taskname]["meanwaittimes"] = (
                                        (self.stats[taskname]["totaltasks"] - 1) * self.stats[taskname]["meanwaittimes"] + waitingtime) / self.stats[taskname]["totaltasks"]

                                    # print("DONE",msg['taskid'])
                                    # print(self.stats[taskname])

                ###### RECEIVE INFORMATION FROM HEALTH CHECK or MONITOR########
                if self.healthSock in sockets:
                    msg = self.healthSock.recv_json()

                    ### MESSAGE COMING FROM HEALTH CHECK ###
                    if 'HEALTH' in msg:
                        if msg['HEALTH'] == 'GIVEMEWORKERSLIST':
                            self.healthSock.send_json({workerid: {'workerip': self.workers[workerid].workerinfo['workerip'],
                                                                  'workerhealthport': self.workers[workerid].workerinfo['workerhealthport'],
                                                                  'lasttasktime': self.workers[workerid].lasttasktime,
                                                                  'taskname': self.workers[workerid].taskname} for
                                                       workerid in self.workers})
                        elif msg['HEALTH'] == 'DOWNWORKER':
                            self.healthSock.send_json({'LB': 'OK'})
                            if msg['workerid'] in self.workers:
                                self.removeWorker(msg['workerid'])
                                cprint('LB - Worker %s is DOWN. Removing it' %
                                       msg['workerid'], 'FAIL')
                        else:
                            self.healthSock.send_json({'LB': 'ERROR'})

                    ### MESSAGE COMING FROM MONITOR ###
                    if 'MONITOR' in msg:
                        if msg['MONITOR'] == 'WORKERS':
                            response = {}
                            response['workers'] = [{'workerid': workerid, 'workerip': self.workers[workerid].workerinfo['workerip'], 'workerport':self.workers[workerid].workerinfo['workerport'], 'workerhealthport':self.workers[workerid].workerinfo['workerhealthport'], 'workerCPU':self.workers[workerid].workercpustate,
                                                    'workertask':self.workers[workerid].taskname, 'workertaskid':self.workers[workerid].taskid, 'workerdone':self.workers[workerid].workerstate, 'workerminpriority':self.workers[workerid].workerinfo['minpriority'], 'workermaxpriority':self.workers[workerid].workerinfo['maxpriority']} for workerid in self.workers]

                            response['commandqueue'] = {}
                            response['priorityqueue'] = {}

                            for i, task in enumerate(self.queue.tasks):
                                if task.taskname not in response['commandqueue']:
                                    response['commandqueue'][task.taskname] = {
                                        'number': 0, 'waitingtime': 0}
                                response['commandqueue'][task.taskname]['number'] += 1
                                response['commandqueue'][task.taskname]['waitingtime'] = max(
                                    time.time() - task.submissiontime, response['commandqueue'][task.taskname]['waitingtime'])

                                if task.priority not in response['priorityqueue']:
                                    response['priorityqueue'][task.priority] = 0
                                response['priorityqueue'][task.priority] += 1

                            self.healthSock.send_json(response)
                        elif msg['MONITOR'] == 'STATS':
                            self.healthSock.send_json(self.stats)
                        else:
                            self.healthSock.send_json(0)

                ###### RECEIVE INFORMATION FROM A CLIENT ############
                if self.clientSock in sockets:
                    msg = self.clientSock.recv_json()
                    if 'toLB' in msg:
                        if msg['toLB'] == "NEWTASK":
                            # print('REVEIVED NEW TASK FROM CLIENT',
                            # msg['taskname'])
                            try:
                                if ('priority' in msg):
                                    try:
                                        priority = float(msg['priority'])
                                    except:
                                        priority = 0
                                        pass
                                else:
                                    priority = 0

                                userid = None
                                addtask = True
                                if self.CONSTANTS['LB_QUEING_MAXPERUSER'] > 0:
                                    if (msg.get('userid') == None):
                                        addtask = False
                                        self.clientSock.send_json(
                                            {'error': 'User must send user id while sending a task'})
                                    else:
                                        userid = msg['userid']
                                        if sum([task.userid == userid for task in self.queue.tasks]) >= self.CONSTANTS['LB_QUEING_MAXPERUSER']:
                                            addtask = False
                                            self.clientSock.send_json(
                                                {'error': 'User has too many pending task (%s)' % self.CONSTANTS['LB_QUEING_MAXPERUSER']})
                                if addtask:
                                    taskid = self.queue.addTask(
                                        msg['taskname'], msg['taskdict'], priority, userid)
                                    self.clientSock.send_json(
                                        {'taskid': taskid})
                            except:
                                self.clientSock.send_json(
                                    {"ERROR": "while adding task, please check message syntax"})
                                print(
                                    "ERROR while adding task, please check client message syntax")
                                traceback.print_exc()

                                pass

                        elif msg['toLB'] == "GETTASK":
                            # print('REVEIVED GET TASK FROM CLIENT',
                            # msg['taskid'])
                            if msg['taskid'] in self.cancelledtasks:
                                self.clientSock.send_json(
                                    {'progress': 'cancelled', 'result': None})
                            elif msg['taskid'] in self.donetasks:
                                self.clientSock.send_json(
                                    {'progress': 100, 'result': self.donetasks[msg['taskid']].workerresult})
                                # Delete result 1min after client query (allow query again in short
                                # time)
                                self.donetasks[msg['taskid']
                                               ].deletetime = time.time() + 60
                            elif msg['taskid'] in self.pendingtasks:
                                self.clientSock.send_json(
                                    {'progress': self.pendingtasks[msg['taskid']].progress, 'result': None})
                            else:
                                isinqueue = False
                                for i, task in enumerate(self.queue.tasks):
                                    if task.taskid == msg['taskid']:
                                        isinqueue = True
                                        self.clientSock.send_json(
                                            {'progress': 0, 'result': None})
                                if not isinqueue:
                                    self.clientSock.send_json(
                                        {'progress': None, 'result': None})

                        elif msg['toLB'] == "GETTASKS":
                            # print('REVEIVED GET TASKS FROM CLIENT',
                            # msg['tasksid'])
                            answer = {}
                            for taskid in msg['tasksid']:
                                if taskid in self.cancelledtasks:
                                    answer[taskid] = {
                                        'progress': 'cancelled', 'result': None}
                                elif taskid in self.donetasks:
                                    answer[taskid] = {'progress': 100,
                                                      'result': self.donetasks[taskid].workerresult}
                                    # Delete result 1min after client query (allow query again in
                                    # short time)
                                    self.donetasks[taskid].deletetime = time.time(
                                    ) + 60
                                elif taskid in self.pendingtasks:
                                    answer[taskid] = {
                                        'progress': self.pendingtasks[taskid].progress, 'result': None}
                                else:
                                    isinqueue = False
                                    for i, task in enumerate(self.queue.tasks):
                                        if task.taskid == taskid:
                                            isinqueue = True
                                            answer[taskid] = {
                                                'progress': 0, 'result': None}
                                    if not isinqueue:
                                        answer[taskid] = {
                                            'progress': None, 'result': None}

                            self.clientSock.send_json(answer)

                        elif msg['toLB'] == "CANCELTASK":
                            cancelstatus = {'deleted': False, 'from': None}
                            if 'taskid' in msg:
                                if msg['taskid'] in self.donetasks:
                                    # print('REVEIVED CANCEL TASK FROM CLIENT',
                                    # msg['taskid'])
                                    self.cancelledtasks[msg['taskid']
                                                        ] = self.donetasks.pop(msg['taskid'])
                                    self.cancelledtasks[msg['taskid']
                                                        ].deletetime = time.time() + 120
                                    cancelstatus = {
                                        'deleted': True, 'from': 'done'}
                                elif msg['taskid'] in self.pendingtasks:
                                    # print('TRYING TO CANCEL PENDING TASK',msg['taskid'])
                                    # CANCEL PROSSES IN WORKER
                                    try:
                                        taskworker = self.pendingtasks[msg['taskid']].workerid
                                        self.workers[taskworker].taskname = None
                                        self.workers[taskworker].taskid = None
                                        self.workers[taskworker].workerstate = 0
                                        self.workers[taskworker].workersocket.send_json(
                                            {'TASK': 'CANCEL', 'taskid': msg['taskid'], 'workerid': taskworker})
                                        answer = self.workers[taskworker].workersocket.recv_json(
                                        )
                                        '''if answer == {'WK': 'OK'}:
                                            print("SUCCESS DELETING WORKING TASK",
                                                  answer, taskworker, msg['taskid'])
                                        else:
                                            print("ERROR DELETING WORKING TASK", answer, taskworker, msg['taskid'])'''
                                    except:
                                        print(
                                            "ERROR while canceling task", taskid)
                                        pass
                                    self.cancelledtasks[msg['taskid']
                                                        ] = self.pendingtasks.pop(msg['taskid'])
                                    self.cancelledtasks[msg['taskid']
                                                        ].deletetime = time.time() + 120

                                    cancelstatus = {
                                        'deleted': True, 'from': 'pending'}
                                else:
                                    for i, task in enumerate(self.queue.tasks):
                                        if task.taskid == msg['taskid']:
                                            self.cancelledtasks[msg['taskid']
                                                                ] = self.queue.tasks.pop(i)
                                            self.cancelledtasks[msg['taskid']
                                                                ].deletetime = time.time() + 120
                                            cancelstatus = {
                                                'deleted': True, 'from': 'queue'}
                                            break
                            self.clientSock.send_json(cancelstatus)

                        else:
                            self.clientSock.send('ERROR Unknown toLB command')

                    else:
                        self.clientSock.send(
                            'ERROR, message from Client not toLB')

                # sort the workers by decreasing state then increasing cpu
                self.sortedworkersid = sorted(
                    self.workers, key=lambda x: (-self.workers[x].workerstate, self.workers[x].workercpustate))

                ###### DISLPAY STATS ############
                '''if (time.time() - self.lastdisplay) > 1:
                    self.lastdisplay = time.time()
                    # states = [self.workers[workerid].workerstate for workerid in self.workers]
                    # self.availworkers = len([s for s in states if s >= 100])
                    # print('#################')
                    # print('QUEUED', len(self.queue.tasks))
                    # print('PENDING', len(self.pendingtasks))
                    # print('DONE', len(self.donetasks))
                    # for workerid in self.sortedworkersid:
                    # print(workerid, self.workers[workerid].workerstate,
                    # self.workers[workerid].workercpustate)
                '''
                ###### REMOVE OLD RESULTS ######
                if (time.time() - self.lastresultdelete) > 1:
                    self.lastresultdelete = time.time()
                    tasktopop = []
                    for i, task in enumerate(self.queue.tasks):
                        if task.deletetime < time.time():
                            tasktopop.append(i)
                    for i in reversed(tasktopop):
                        # print('QUEUED TASK', task.taskid, 'TOO OLD DELETING')
                        self.queue.tasks.pop(i)

                    tasktopop = []
                    for taskid in self.pendingtasks:
                        if self.pendingtasks[taskid].deletetime < time.time():
                            tasktopop.append(taskid)
                    for taskid in reversed(tasktopop):
                        # print('PENDING TASK', taskid, 'TOO OLD DELETING')
                        self.pendingtasks.pop(taskid)

                    tasktopop = []
                    for taskid in self.donetasks:
                        if self.donetasks[taskid].deletetime < time.time():
                            tasktopop.append(taskid)
                    for taskid in reversed(tasktopop):
                        # print('DONE TASK',taskid,'TOO OLD DELETING')
                        self.donetasks.pop(taskid)

                    tasktopop = []
                    for taskid in self.cancelledtasks:
                        if self.cancelledtasks[taskid].deletetime < time.time():
                            tasktopop.append(taskid)
                    for taskid in reversed(tasktopop):
                        # print('CANCELLED TASK', taskid, 'TOO OLD DELETING')
                        self.cancelledtasks.pop(taskid)

                ###### DO TASKS ############
                self.sendTasks()

            except KeyboardInterrupt:
                # interupt loop = close LB
                cprint("LB KeyboardInterrupt", "FAIL")
                sys.exit()
            except:
                # something when wrong in loop
                traceback.print_exc()
                print("Unexpected error in main LB LOOP")
                pass


def main():
    parser = argparse.ArgumentParser(
        description='Health Check Script for the pyLoadBalancer module.')
    parser.add_argument('-p', '--pfile', default=None,
                        help='parameter file, in JSON format')
    args = parser.parse_args()
    LB = LoadBalancer(parametersfile=args.pfile)
    LB.startLB()


if __name__ == '__main__':
    main()
