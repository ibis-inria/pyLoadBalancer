#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module describes a the Health Check class.
Health Check is here to check the activity of the different workers and give information to the Load Balancer.

The Health Check can be either directly launch from a console :
    python3 HeathCheck.py

Or it can be imported as a module :
    from JSONLoadBalancer import HealthCheck
    HC = HealthCheck(log=True)
    HC.startHC()

The log option has to be set to True if you want to monitor the LoadBalancer using the web interface described in LBMonitor.py
"""

import zmq
import os.path
import time, datetime
import json
import asyncio

__all__ = ['HealthCheck'] #Only possible to import Client


# Constants definitions
with open(os.path.join(os.path.dirname(__file__), 'parameters.json'), 'r') as fp:
    CONSTANTS = json.load(fp)
LB_HEALTHADRESS = 'tcp://' + CONSTANTS['LB_IP'] + ':' + str(CONSTANTS['LB_HCREPPORT'])

class HealthCheck:
    def __init__(self):
        self.context = zmq.Context()
        self.LBReqSock = self.context.socket(zmq.REQ)
        self.setLBReqSock()
        self.workers = {}
        self.dealer = self.context.socket(zmq.DEALER)
        self.dealer.setsockopt(zmq.RCVTIMEO, 0)  # Time out when asking worker
        self.dealer.setsockopt(zmq.SNDTIMEO, CONSTANTS['SOCKET_TIMEOUT'])
        self.dealer.setsockopt(zmq.LINGER, 0)  # Time before closing socket

    def setLBReqSock(self):
        #self.LBReqSock = self.context.socket(zmq.REQ)
        self.LBReqSock.setsockopt(zmq.RCVTIMEO, CONSTANTS['SOCKET_TIMEOUT'])  # Time out when asking worker
        self.LBReqSock.setsockopt(zmq.SNDTIMEO, CONSTANTS['SOCKET_TIMEOUT'])
        self.LBReqSock.setsockopt(zmq.REQ_RELAXED,1)
        self.LBReqSock.connect(LB_HEALTHADRESS)
        print('HC - Conected to ', LB_HEALTHADRESS)

    def checkWorkers(self):

        for workerid in self.workers:
                self.dealer.connect(
                    'tcp://' + self.workers[workerid]['workerip'] + ':' + str(
                        self.workers[workerid]['workerhealthport']))

        for workerid in self.workers:
            time.sleep(0.001)
            self.dealer.send(b"", zmq.SNDMORE)
            self.dealer.send_json({"HEALTH": "CHECKWORKERS","workerid" : workerid})

        time.sleep(CONSTANTS['SOCKET_TIMEOUT']/1000.)

        for workerid in self.workers:
            self.workers[workerid]['workerstate'] = 0
        failed = 0

        for i,worker in enumerate(self.workers):
            try:
                self.dealer.recv()
                response = self.dealer.recv_json()
                if not 'workerid' in response:
                    print(CONSTANTS['FAIL'], 'HC - GOT RESPONSE FROM AN UNKNOWN WORKER', CONSTANTS['ENDC'])
                if response['workerid'] in self.workers:
                    self.workers[response['workerid']]['workerstate'] = response['workerstate']

            except Exception as e:
                # self.workers[workerid]['workersocket'].disconnect('tcp://' + self.workers[workerid]['workerip'] + ':' + str(self.workers[workerid]['workerhealthport']))
                failed += 1 #print(CONSTANTS['FAIL'], 'HC - %dTH SOCKET TIMEOUT' % i, str(e), CONSTANTS['ENDC'])
                pass

        if failed > 0:
            print(CONSTANTS['FAIL'], 'HC - %d WORKERS DID NOT ANSWER' % failed, CONSTANTS['ENDC'])


        for workerid in self.workers:
            try:
                self.dealer.disconnect('tcp://' + self.workers[workerid]['workerip'] + ':' + str(self.workers[workerid]['workerhealthport']))
            except zmq.ZMQError:
                print('COULD NOT DISCONNECT ', 'tcp://' + self.workers[workerid]['workerip'] + ':' + str(self.workers[workerid]['workerhealthport']))


    def downWorker(self, workerid):
        try:
            self.LBReqSock.connect(LB_HEALTHADRESS)
            self.LBReqSock.send_json({'HEALTH': "DOWNWORKER", "workerid":workerid}, zmq.NOBLOCK)
            self.LBReqSock.recv_json()
        except Exception as e:
            print(CONSTANTS['FAIL'], 'HC - CAN\'T SEND DOWN WORKER TO LB: LB DOWN ??', str(e), CONSTANTS['ENDC'])
            self.LBReqSock.disconnect(LB_HEALTHADRESS)
            self.setLBReqSock()
            pass



    def doHealthCheckTasks(self):
        try:
            self.LBReqSock.connect(LB_HEALTHADRESS)
            self.LBReqSock.send_json({'HEALTH': "GIVEMEWORKERSLIST"},zmq.NOBLOCK)
            newworkers = self.LBReqSock.recv_json()
            for workerid in list(self.workers):
                if workerid not in newworkers:
                    del self.workers[workerid]
            self.workers.update(newworkers)
        except Exception as e:
            print(CONSTANTS['FAIL'],'HC - CAN\'T GET WORKER LIST : LB DOWN ??', str(e),CONSTANTS['ENDC'])
            self.LBReqSock.disconnect(LB_HEALTHADRESS)
            self.setLBReqSock()
            pass

        if not self.workers:
            print(CONSTANTS['FAIL'],'HC - WARNING : LB HAS NO WORKERS',CONSTANTS['ENDC'])
        else:
            self.checkWorkers()

        # If the worker has not done anything since 2 minutes, tell LB it is idle
        for workerid in self.workers:
            if ((time.time() - self.workers[workerid]['lasttasktime']) > 120) and (self.workers[workerid]['workerstate'] == 0):
                print(CONSTANTS['OKBLUE'], 'HC - ', workerid, ' SEEMS DOWN (%ss and state=%s)'%((time.time() - self.workers[workerid]['lasttasktime']),self.workers[workerid]['workerstate']))
                self.downWorker(workerid)

        states = [self.workers[workerid]['workerstate'] for workerid in self.workers]
        availworkers = len([s for s in states if s >= 100])
        if self.workers:
            if availworkers<1:
                print(CONSTANTS['FAIL'],"HC - ", time.strftime('%H:%M:%S'), " - no available workers" ,CONSTANTS['ENDC'])
            else:
                print(CONSTANTS['OKGREEN'],"HC - ", time.strftime('%H:%M:%S'), "- %d available workers" %availworkers,CONSTANTS['ENDC'])

    def startHC(self, checkTimer=0.5):
        while True:
            self.doHealthCheckTasks()
            time.sleep(checkTimer)

def main():
    HC = HealthCheck()
    HC.startHC()

if __name__ == '__main__':
    main()

