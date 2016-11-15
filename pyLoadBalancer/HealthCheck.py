#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module describes a the Health Check class.
Health Check is here to check the activity of the different workers and give information to the Load Balancer.

The Health Check can be either directly launch from a console :
    python3 HeathCheck.py

Or it can be imported as a module :
    from JSONLoadBalancer import HealthCheck
    HC = HealthCheck()
    HC.startHC()
"""

import zmq
import os.path
import time, datetime
import json
import argparse
from .colorprint import cprint,bcolors
import sys
import traceback

__all__ = ['HealthCheck'] #Only possible to import Client

class HealthCheck:
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

        print('pyLoadBalancer - Health Check')
        cprint('Starting Health Check with the folllowing settings : ', 'OKGREEN')
        for keys, values in self.CONSTANTS.items():
            print(bcolors.OKBLUE,'   ', keys, ':',bcolors.ENDC, values)

        self.LB_HEALTHADRESS = 'tcp://' + self.CONSTANTS['LB_IP'] + ':' + str(self.CONSTANTS['LB_HCREPPORT'])

        self.context = zmq.Context()
        self.LBReqSock = self.context.socket(zmq.REQ)
        self.setLBReqSock()
        self.workers = {}
        self.dealer = self.context.socket(zmq.DEALER)
        self.dealer.setsockopt(zmq.RCVTIMEO, 0)  # Time out when asking worker
        self.dealer.setsockopt(zmq.SNDTIMEO, self.CONSTANTS['SOCKET_TIMEOUT'])
        self.dealer.setsockopt(zmq.LINGER, 0)  # Time before closing socket

    def setLBReqSock(self):
        #self.LBReqSock = self.context.socket(zmq.REQ)
        self.LBReqSock.setsockopt(zmq.RCVTIMEO, self.CONSTANTS['SOCKET_TIMEOUT'])  # Time out when asking worker
        self.LBReqSock.setsockopt(zmq.SNDTIMEO, self.CONSTANTS['SOCKET_TIMEOUT'])
        self.LBReqSock.setsockopt(zmq.REQ_RELAXED,1)
        self.LBReqSock.connect(self.LB_HEALTHADRESS)
        print('HC - Conected to ', self.LB_HEALTHADRESS)

    def checkWorkers(self):

        for workerid in self.workers:
                self.dealer.connect(
                    'tcp://' + self.workers[workerid]['workerip'] + ':' + str(
                        self.workers[workerid]['workerhealthport']))

        for workerid in self.workers:
            time.sleep(0.001)
            self.dealer.send(b"", zmq.SNDMORE)
            self.dealer.send_json({"HEALTH": "CHECKWORKERS","workerid" : workerid})

        time.sleep(self.CONSTANTS['SOCKET_TIMEOUT']/1000.)

        for workerid in self.workers:
            self.workers[workerid]['workerstate'] = 0
        failed = 0

        for i,worker in enumerate(self.workers):
            try:
                self.dealer.recv()
                response = self.dealer.recv_json()
                if not 'workerid' in response:
                    if response != {'WK':'FLUSHED'}:
                        cprint('HC - GOT RESPONSE FROM AN UNKNOWN WORKER', 'FAIL')
                if response['workerid'] in self.workers:
                    self.workers[response['workerid']]['workerstate'] = response['workerstate']

            except Exception as e:
                #cprint('    WORKER DID NOT ANSWER', 'FAIL')
                #traceback.print_exc()
                failed += 1
                pass

        #if failed > 0:
        #    cprint('HC - %d WORKERS DID NOT ANSWER' % failed, 'FAIL')


        for workerid in self.workers:
            try:
                self.dealer.disconnect('tcp://' + self.workers[workerid]['workerip'] + ':' + str(self.workers[workerid]['workerhealthport']))
            except zmq.ZMQError:
                pass
                #print('COULD NOT DISCONNECT ', 'tcp://' + self.workers[workerid]['workerip'] + ':' + str(self.workers[workerid]['workerhealthport']))


    def downWorker(self, workerid):
        try:
            self.LBReqSock.connect(self.LB_HEALTHADRESS)
            self.LBReqSock.send_json({'HEALTH': "DOWNWORKER", "workerid":workerid}, zmq.NOBLOCK)
            self.LBReqSock.recv_json()
        except Exception as e:
            cprint('HC - CAN\'T SEND DOWN WORKER TO LB: LB DOWN ??' + str(e), 'FAIL')
            self.LBReqSock.disconnect(self.LB_HEALTHADRESS)
            self.setLBReqSock()
            pass



    def doHealthCheckTasks(self):
        try:
            self.LBReqSock.connect(self.LB_HEALTHADRESS)
            self.LBReqSock.send_json({'HEALTH': "GIVEMEWORKERSLIST"},zmq.NOBLOCK)
            newworkers = self.LBReqSock.recv_json()
            for workerid in list(self.workers):
                if workerid not in newworkers:
                    del self.workers[workerid]
            self.workers.update(newworkers)
        except Exception as e:
            cprint('HC - CAN\'T GET WORKER LIST : LB DOWN ??' + str(e), 'FAIL')
            self.LBReqSock.disconnect(self.LB_HEALTHADRESS)
            self.setLBReqSock()
            pass

        if not self.workers:
            cprint('HC - WARNING : LB HAS NO WORKERS', 'FAIL')
        else:
            self.checkWorkers()

        # If the worker has not done anything since 2 minutes, tell LB it is idle
        for workerid in self.workers:
            if ((time.time() - self.workers[workerid]['lasttasktime']) > 120) and (self.workers[workerid]['workerstate'] == 0):
                cprint('HC - %s SEEMS DOWN (%ss and state=%s)'%(workerid,(time.time() - self.workers[workerid]['lasttasktime']),self.workers[workerid]['workerstate']), 'OKBLUE')
                self.downWorker(workerid)

        states = [self.workers[workerid]['workerstate'] for workerid in self.workers]
        availworkers = len([s for s in states if s >= 100])
        #if self.workers:
        #    if availworkers<1:
        #        cprint("HC - %s - no available workers" % (time.strftime('%H:%M:%S')), 'FAIL')
        #    else:
        #        cprint("HC - %s - %d available workers" %(time.strftime('%H:%M:%S'),availworkers),'OKGREEN')

    def startHC(self, checkTimer=2):
        while True:
            self.doHealthCheckTasks()
            time.sleep(checkTimer)

def main():
    parser = argparse.ArgumentParser(description='Health Check Script for the pyLoadBalancer module.')
    parser.add_argument('-p', '--pfile', default=None, help='parameter file, in JSON format')
    args = parser.parse_args()
    HC = HealthCheck(parametersfile=args.pfile)
    HC.startHC()

if __name__ == '__main__':
    main()
