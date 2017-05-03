#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module describes a the Health Check class.
Health Check is here to check the activity of the different workers and give information to the Load Balancer.

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
import time
import datetime
import json
import argparse
from .colorprint import cprint
import sys
import traceback
import atexit
import signal

__all__ = ['HealthCheck']  # Only possible to import Client


class HealthCheck:
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

        cprint('Starting Health Check with the folllowing settings : ', 'OKGREEN')
        for keys, values in self.CONSTANTS.items():
            cprint('   ' + str(keys) + ':', 'OKBLUE', values)

        self.LB_HEALTHADRESS = 'tcp://' + \
            self.CONSTANTS['LB_IP'] + ':' + str(self.CONSTANTS['LB_HCREPPORT'])

        self.context = zmq.Context()
        self.LBReqSock = self.context.socket(zmq.REQ)
        self.setLBReqSock()
        self.workers = {}
        self.dealer = self.context.socket(zmq.DEALER)
        self.dealer.setsockopt(zmq.RCVTIMEO, 0)  # Time out when asking worker
        self.dealer.setsockopt(zmq.SNDTIMEO, self.CONSTANTS['SOCKET_TIMEOUT'])
        self.dealer.setsockopt(zmq.LINGER, 0)  # Time before closing socket

        self.exiting = False
        atexit.register(self.on_exit)
        signal.signal(signal.SIGTERM, self.on_exit)
        signal.signal(signal.SIGINT, self.on_exit)

    def on_exit(self, *args):
        self.exiting = True

    def setLBReqSock(self):
        #self.LBReqSock = self.context.socket(zmq.REQ)
        # Time out when asking worker
        self.LBReqSock.setsockopt(
            zmq.RCVTIMEO, self.CONSTANTS['SOCKET_TIMEOUT'])
        self.LBReqSock.setsockopt(
            zmq.SNDTIMEO, self.CONSTANTS['SOCKET_TIMEOUT'])
        self.LBReqSock.setsockopt(zmq.REQ_RELAXED, 1)
        self.LBReqSock.connect(self.LB_HEALTHADRESS)

    def checkWorkers(self):

        connected = {}
        for workerid in self.workers:
            wkadress = 'tcp://' + self.workers[workerid]['workerip'] + \
                ':' + str(self.workers[workerid]['workerhealthport'])
            if not wkadress in connected:
                self.dealer.connect(wkadress)
                connected[wkadress] = True
        #print("CONNECTED", connected)

        for wkadress in connected:
            self.dealer.send(b"", zmq.SNDMORE)
            self.dealer.send_json({"HEALTH": "CHECKWORKERS", "workerid": [
                                  workerid for workerid in self.workers]})

        time.sleep(2 * self.CONSTANTS['SOCKET_TIMEOUT'] / 1000.)

        for workerid in self.workers:
            self.workers[workerid]['workerstate'] = -1
        failed = 0

        for wkadress in connected:
            try:
                self.dealer.recv()
                response = self.dealer.recv_json()
                # print(response)
                for workerid in response:
                    if workerid in self.workers:
                        self.workers[workerid]['workerstate'] = response[workerid]

            except Exception as e:
                cprint('HC - Worker did not anwser', 'WARNING')
                # traceback.print_exc()
                failed += 1
                pass

        # if failed > 0:
        #    cprint('HC - %d WORKERS DID NOT ANSWER' % failed, 'FAIL')

        for wkadress in connected:
            try:
                self.dealer.disconnect(wkadress)
            except zmq.ZMQError:
                print('COULD NOT DISCONNECT ', wkadress)
                pass

    def downWorker(self, workerid):
        try:
            self.LBReqSock.connect(self.LB_HEALTHADRESS)
            self.LBReqSock.send_json(
                {'HEALTH': "DOWNWORKER", "workerid": workerid}, zmq.NOBLOCK)
            self.LBReqSock.recv_json()
        except Exception as e:
            cprint('HC - CAN\'T SEND DOWN WORKER TO LB: LB DOWN ??' + str(e), 'FAIL')
            self.LBReqSock.disconnect(self.LB_HEALTHADRESS)
            self.setLBReqSock()
            pass

    def doHealthCheckTasks(self):
        try:
            self.LBReqSock.connect(self.LB_HEALTHADRESS)
            self.LBReqSock.send_json(
                {'HEALTH': "GIVEMEWORKERSLIST"}, zmq.NOBLOCK)
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
            cprint('HC - WARNING : LB HAS NO WORKERS', 'WARNING')
        else:
            self.checkWorkers()

        # If the worker has not done anything since 2 minutes, tell LB it is
        # idle
        for workerid in self.workers:
            if ((time.time() - self.workers[workerid]['lasttasktime']) > 10) and (self.workers[workerid]['workerstate'] == -1):
                cprint('HC - %s SEEMS DOWN (%ss and state=%s)' % (workerid, (time.time() -
                                                                             self.workers[workerid]['lasttasktime']), self.workers[workerid]['workerstate']), 'OKBLUE')
                self.downWorker(workerid)

        states = [self.workers[workerid]['workerstate']
                  for workerid in self.workers]
        availworkers = len([s for s in states if s >= 100])
        # if self.workers:
        #    if availworkers<1:
        #        cprint("HC - %s - no available workers" % (time.strftime('%H:%M:%S')), 'FAIL')
        #    else:
        #        cprint("HC - %s - %d available workers" %(time.strftime('%H:%M:%S'),availworkers),'OKGREEN')

    def startHC(self, checkTimer=1):
        while True:
            if self.exiting:
                cprint("EXITED Health Check", "OKGREEN")
                break
            self.doHealthCheckTasks()
            time.sleep(checkTimer)


def main():
    parser = argparse.ArgumentParser(
        description='Health Check Script for the pyLoadBalancer module.')
    parser.add_argument('-p', '--pfile', default=None,
                        help='parameter file, in JSON format')
    args = parser.parse_args()
    HC = HealthCheck(parametersfile=args.pfile)
    HC.startHC()


if __name__ == '__main__':
    main()
