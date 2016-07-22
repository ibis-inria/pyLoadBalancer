#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module describes the Load Balancer.

The Load Balancer can be either directly launch from a console :
    python3 LoadBalancer.py

Or it can be imported as a module :
    from JSONLoadBalancer import LoadBalancer
    LB = LoadBalancer()
    LB.startLB(log=True)

Note that all the parameters necessary for the different elements (LoadBalancer, HealthCheck, Worker, Client) to communicate are given in the 'parameters.json' file.
"""

import time, datetime
import zmq
import os.path
import json
import numpy as np

__all__ = ['LoadBalancer'] #Only possible to import Client

# Constants definitions
with open(os.path.join(os.path.dirname(__file__), 'parameters.json'), 'r') as fp:
    CONSTANTS = json.load(fp)

def argsort(seq):
    # http://stackoverflow.com/questions/3071415/efficient-method-to-calculate-the-rank-vector-of-a-list-in-python
    return sorted(range(len(seq)), key=seq.__getitem__)

class learnTaskTimes:
    def __init__(self, command):
        self.learnParams = np.zeros((1,))
        self.learnTimes = np.zeros((1,))
        self.command = command

    def cleanPoints(self):
        #sqrerr =  ( np.fromiter(map(self.guessTime, self.learnParams), dtype='float') - self.learnTimes ) **2
        #self.learnParams = self.learnParams[sqrerr < np.std(sqrerr)/2]
        #self.learnTimes = self.learnTimes[sqrerr < np.std(sqrerr)/2]
        self.learnTimes = self.learnTimes[::4]
        self.learnParams = self.learnParams[::4]

    def addObservation(self,param,time):

        if self.learnParams.shape[0] > 200:
            self.cleanPoints()

        self.learnParams = np.append(self.learnParams,param)
        self.learnTimes = np.append(self.learnTimes, time)

        if self.learnParams.shape[0] < 5 :
            self.timesfit = np.poly1d(np.polyfit(self.learnParams,self.learnTimes,1))
        else:
            self.timesfit = np.poly1d(np.polyfit(self.learnParams, self.learnTimes,2))

    def guessTime(self, param):
        return self.timesfit(param)

class Queue:
    def __init__(self, maxAllowedTime, highP=False, lowP=True):
        self.tasks = []
        self.tasksSubmissionTimes = []
        self.tasksEstCalculTimes = []
        self.tasksDone = 0
        self.meanWaitTime = 0
        self.maxWaitTime = 0
        self.highP = highP
        self.lowP = lowP

        self.maxAllowedTime = maxAllowedTime


class LoadBalancer:
    def __init__(self,log=False, queues=[{'maxallowedtime':1,'lowP':True,'highP':True},{'maxallowedtime':1e10,'lowP':True,'highP':False}]):

        self.learnTimes = {}

        self.workers = {}

        self.queues = []
        for queue in queues:
            self.queues.append( Queue(queue['maxallowedtime'],queue['highP'],queue['lowP']) )

        self.log = log


        self.context = zmq.Context()

        self.workerStateSock = self.context.socket(zmq.PULL)
        self.workerStateSock.bind("tcp://"+CONSTANTS['LB_IP']+":" + str(CONSTANTS['LB_WKPULLPORT']))

        self.clientPullSock = self.context.socket(zmq.PULL)
        self.clientPullSock.bind("tcp://"+CONSTANTS['LB_IP']+":" + str(CONSTANTS['LB_CLIENTPULLPORT']))

        self.healthSock = self.context.socket(zmq.REP)
        self.healthSock.bind("tcp://"+CONSTANTS['LB_IP']+":" + str(CONSTANTS['LB_HCREPPORT']))

        self.poller = zmq.Poller()
        self.poller.register(self.workerStateSock, zmq.POLLIN)
        self.poller.register(self.healthSock, zmq.POLLIN)
        self.poller.register(self.clientPullSock, zmq.POLLIN)

    def resetWorkerSocket(self,workerid):
        self.workers[workerid]['workersocket'].setsockopt(zmq.RCVTIMEO, CONSTANTS['SOCKET_TIMEOUT'])  # Time out when asking worker
        self.workers[workerid]['workersocket'].setsockopt(zmq.SNDTIMEO, CONSTANTS['SOCKET_TIMEOUT'])
        self.workers[workerid]['workersocket'].setsockopt(zmq.LINGER, 0)  # Time before closing socket
        self.workers[workerid]['workersocket'].setsockopt(zmq.REQ_RELAXED, 1)
        self.workers[workerid]['workersocket'].connect('tcp://' + self.workers[workerid]['workerip'] + ':' + str(self.workers[workerid]['workerport']))

    def addWorker(self, workerinfo):
        workerid = workerinfo['workerid']
        self.workers[workerid] = workerinfo
        self.workers[workerid]['workerstate'] = 0
        self.workers[workerid]['workercpustate'] = 100
        self.workers[workerid]['lasttasktime'] = time.time()
        self.workers[workerid]['learningCommand']  = None
        self.workers[workerid]['learningParam'] = None
        self.workers[workerid]['workersocket'] = self.context.socket(zmq.REQ)
        self.resetWorkerSocket(workerid)
        print('WORKER '+ workerid + ' ADDED : ', self.workers[workerid])

    def askWorkerReady(self,workerid):
        try:
            self.workers[workerid]['lasttasktime'] = time.time()
            self.workers[workerid]['workersocket'].send_json({'TASK': 'READY?'})
            if self.workers[workerid]['workersocket'].recv_json() == CONSTANTS['WK_OK']:
                self.workers[workerid]['workerstate'] = 100
            else:
                self.workers[workerid]['workerstate'] = 0

        except Exception as e:
            del self.workers[workerid]
            print(CONSTANTS['FAIL'],'LB - REMOVING WORKER %s : NO ANSWER TO READY QUESTION' % workerid, str(e),CONSTANTS['ENDC'])
            pass


    def sendTasks(self):

        for workerid in self.sortedworkersid:
            if self.workers[workerid]['workerstate'] >= 100: #there is at least a free worker

                for nqueue, queue in enumerate(self.queues):
                    if queue.tasks:
                        if (queue.highP and (self.workers[workerid]['workerpriority'] == 0)) or (queue.lowP and (self.workers[workerid]['workerpriority'] == 10)):
                            try:
                                self.workers[workerid]['workerstate'] = 0
                                taskmsg = queue.tasks[0]
                                self.workers[workerid]['workersocket'].send_json(taskmsg)
                                answer = self.workers[workerid]['workersocket'].recv_json()
                                if answer == CONSTANTS['WK_OK']:
                                    waitingtime = time.time() - queue.tasksSubmissionTimes[0]
                                    queue.maxWaitTime = max(queue.maxWaitTime,  waitingtime)
                                    queue.meanWaitTime = (queue.meanWaitTime * queue.tasksDone + waitingtime)/ (queue.tasksDone + 1)
                                    queue.tasksDone += 1
                                    queue.tasks.pop(0)
                                    queue.tasksSubmissionTimes.pop(0)
                                    queue.tasksEstCalculTimes.pop(0)

                                    self.workers[workerid]['lasttasktime'] = time.time()
                                    self.workers[workerid]['learningCommand'] = taskmsg['TASK']
                                    self.workers[workerid]['learningParam'] = taskmsg['learningParam']
                                else:
                                    print(CONSTANTS['WARNING'], 'LB - WORKER ', workerid,
                                          'DID NOT TAKE TASK - stay in queue', CONSTANTS['ENDC'])

                            except Exception as e:
                                print(CONSTANTS['FAIL'], 'LB - CAN\'T SEND TASK TO WORKER', workerid, str(e),
                                      CONSTANTS['ENDC'])
                                self.workers[workerid]['workersocket'].disconnect(
                                    'tcp://' + self.workers[workerid]['workerip'] + ':' + str(
                                        self.workers[workerid]['workerport']))
                                self.resetWorkerSocket(workerid)
                                pass

                            break





    def startLB(self):
        #Start the Load Balancer : listen to incoming sockets.

        while True:
            sockets = dict(self.poller.poll())

            ###### RECEIVE INFORMATION FROM A WORKER ############
            if self.workerStateSock in sockets:
                msg = self.workerStateSock.recv_json()
                if 'CPUonly' in msg:
                    if (msg['workerid'] in self.workers):
                        self.workers[msg['workerid']]['workercpustate'] = msg['workercpustate']
                elif (msg['workerstate'] == "HELLO"):
                    if (msg['workerid'] not in self.workers):
                        print(CONSTANTS['OKBLUE'], "LB - RECEIVED HELLO MESSAGE FROM AN UNKWONN WORKER (%s). ADDING WORKER" %
                              msg['workerid'],CONSTANTS['ENDC'])
                        self.addWorker(msg)
                        self.askWorkerReady(msg['workerid'])
                else:
                    if (msg['workerid'] in self.workers):
                        self.workers[msg['workerid']]['workerstate'] = msg['workerstate']
                        if (msg['workerstate'] == 100) and (self.workers[msg['workerid']]['learningParam'] != None):
                            command = self.workers[msg['workerid']]['learningCommand']
                            learningparam = self.workers[msg['workerid']]['learningParam']
                            timetocomplete = time.time() - self.workers[msg['workerid']]['lasttasktime']
                            if command not in self.learnTimes:
                                self.learnTimes[command] = learnTaskTimes(command)
                            self.learnTimes[command].addObservation(learningparam,timetocomplete)
                            self.workers[msg['workerid']]['learningCommand'] = None
                            self.workers[msg['workerid']]['learningParam'] = None

                            guess = self.learnTimes[command].guessTime(learningparam)
                            print('REAL TIME ', timetocomplete, ' - ESTIMATED TIME ', guess, ' - ', (guess-timetocomplete)/timetocomplete*100, ' % err')



            ###### RECEIVE INFORMATION FROM HEALTH CHECK or MONITOR############
            if self.healthSock in sockets:
                msg = self.healthSock.recv_json()

                ### MESSAGE COMING FROM HEALTH CHECK ###
                if 'HEALTH' in msg:
                    if msg['HEALTH'] == 'GIVEMEWORKERSLIST':
                        self.healthSock.send_json({workerid: {'workerip': self.workers[workerid]['workerip'],
                                                            'workerhealthport': self.workers[workerid]['workerhealthport'],
                                                            'lasttasktime': self.workers[workerid]['lasttasktime']} for
                                                 workerid in self.workers})
                    elif msg['HEALTH'] == 'DOWNWORKER':
                        self.healthSock.send_json(CONSTANTS['LB_OK'])
                        if msg['workerid'] in self.workers:
                            print(CONSTANTS['FAIL'], 'LB - Worker ', msg['workerid'], ' is DOWN. Removing it', CONSTANTS['ENDC'])
                            del self.workers[msg['workerid']]
                    else:
                        self.healthSock.send_json(CONSTANTS['LB_ERROR'])

                ### MESSAGE COMING FROM MONITOR ###
                if 'MONITOR' in msg:
                    if msg['MONITOR'] == 'WORKERS':
                        response = {}
                        response['workers'] = [{'workerid':workerid, 'workerip':self.workers[workerid]['workerip'], 'workerport':self.workers[workerid]['workerport'], 'workerhealthport':self.workers[workerid]['workerhealthport'], 'workerCPU':self.workers[workerid]['workercpustate'], 'workertask':self.workers[workerid]['learningCommand'], 'workerdone':self.workers[workerid]['workerstate'], 'workerpriority':self.workers[workerid]['workerpriority']} for workerid in self.workers]
                        response['queues'] = []

                        queuestotaltimes = 0
                        for nqueue, queue in enumerate(self.queues):
                            response['queues'].append("Queue" + str(nqueue))
                            queueavailableworkers = sum( [ ((queue.highP and (self.workers[workerid]['workerpriority'] == 0)) or (queue.lowP and (self.workers[workerid]['workerpriority'] == 10))) for workerid in self.workers])

                            response["Queue" + str(nqueue)] = {  'meantime': queue.meanWaitTime,
                                                                 'maxtime' : queue.maxWaitTime,
                                                                 'donetasks' : queue.tasksDone,
                                                                 'availworkers': queueavailableworkers,
                                                                 'highP': queue.highP,
                                                                 'lowP': queue.lowP}
                            if queue.tasks:
                                queuestotaltimes += sum(queue.tasksEstCalculTimes)/queueavailableworkers
                                response["Queue" + str(nqueue)]['queuetime'] = time.time() - queue.tasksSubmissionTimes[0]
                                response["Queue" + str(nqueue)]['queuingtasks'] = len(queue.tasks)
                            else:
                                response["Queue" + str(nqueue)]['queuetime'] = 0
                                response["Queue" + str(nqueue)]['queuingtasks'] = 0

                            response["Queue" + str(nqueue)]['totalesttime'] = queuestotaltimes

                        print(response)
                        self.healthSock.send_json(response)
                    elif msg['MONITOR'] == 'COMMANDS':
                        response = [command for command in  self.learnTimes]
                        self.healthSock.send_json(response)

                    elif msg['MONITOR'] == 'COMMAND':
                        if 'name' in msg:
                            command = msg['name']
                            if command in self.learnTimes :
                                print('MONITOR ASKING FOR INFO ', command, msg)
                                response = {'command': command,
                                             'timepoints': [{"x": self.learnTimes[command].learnParams[i],
                                                             "y": self.learnTimes[command].learnTimes[i]} for (i, learnparam) in
                                                            enumerate(self.learnTimes[command].learnParams)],
                                             'esttimepoints': [{"x": param, "y": self.learnTimes[command].guessTime(param)} for
                                                               param in np.linspace(min(self.learnTimes[command].learnParams),
                                                                                    max(self.learnTimes[command].learnParams),
                                                                                    50)]}
                            else:
                                response = 0
                        else:
                            response = 0
                        self.healthSock.send_json(response)
                    else:
                        self.healthSock.send_json(0)



            ###### RECEIVE INFORMATION FROM A CLIENT ############
            if self.clientPullSock in sockets:
                msg = self.clientPullSock.recv_json()
                if msg['HELLO'] == 'TOWORKER':
                    print('REVEIVED TASK FROM CLIENT', msg['TASK'])

                    if 'learningParam' not in msg:
                        msg['learningParam'] = 1

                    if msg['TASK'] in self.learnTimes:
                        estimatedtime =  self.learnTimes[msg['TASK']].guessTime(msg['learningParam'])
                        print(CONSTANTS['OKBLUE'], 'LB - TASK %s WITH PARAM %f WILL TAKE ABOUT %f sec ' % (msg['TASK'],msg['learningParam'],estimatedtime),
                              CONSTANTS['ENDC'])
                    else:
                        estimatedtime = self.queues[-1].maxAllowedTime
                        print(CONSTANTS['OKBLUE'], 'LB - TASK %s HAS NO ESTIMATED TIME, time set to ', estimatedtime, 's',CONSTANTS['ENDC'])

                    nqueue = 0
                    for nqueue,queue in enumerate(self.queues):
                        if (estimatedtime < queue.maxAllowedTime) or (nqueue == len(self.queues) - 1): ##go to the first queue that have a superior max time or to the last
                            queue.tasks.append(msg)
                            queue.tasksSubmissionTimes.append(time.time())
                            queue.tasksEstCalculTimes.append(estimatedtime)
                            break


            ###### DISLPAY STATS ############
            states = [self.workers[workerid]['workerstate'] for workerid in self.workers]
            cpustates = [self.workers[workerid]['workercpustate'] for workerid in self.workers]
            self.availworkers = len([s for s in states if s >= 100])
            self.sortedworkersid = sorted(self.workers, key=lambda x: (-self.workers[x]['workerstate'], self.workers[x][
                'workercpustate']))  # sort the workers by decreasing state then increasing cpu


            ###### DO TASKS ############
            self.sendTasks()



def main():
    print('Launching pyLoadBalancer : Load Balancer')
    LB = LoadBalancer(log=True)
    LB.startLB()

if __name__ == '__main__':
    main()