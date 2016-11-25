import time
import json
import zmq
import os.path
import psutil
import sys
import multiprocessing
import uuid
import random
import argparse


def workerloop(**kwargs):
    test = 0
    conn = kwargs["conn"]

    while True:
        msg = conn.recv()
        if msg == "state":
            conn.send(100)
        print("MSG",msg)

        '''if kwargs["id"] in kwargs["tasks"]:
            test += 1
            #take task
            kwargs["taskslock"].acquire()
            task = kwargs["tasks"].pop(kwargs["id"])
            kwargs["taskslock"].release()
            print('Worker', kwargs["id"] , 'GOT TASK', task)

            kwargs["resultslock"].acquire()
            kwargs["results"] = 'result is ' + str(test) + ' - ' + task
            kwargs["resultslock"].release()

            print('Waiting For Command',kwargs['results'])'''

def test():
    manager = multiprocessing.Manager()
    tasks = manager.dict()
    results = manager.dict()
    taskslock = multiprocessing.Lock()
    resultslock = multiprocessing.Lock()

    parent_conn, child_conn = multiprocessing.Pipe()

    workingprocess = multiprocessing.Process(target=workerloop, kwargs={'conn': child_conn, 'id':'uniqueid','tasks':tasks, 'taskslock': taskslock, 'results':results,'resultslock': resultslock, 'args':'test'})
    workingprocess.start()

    while True:
        if not workingprocess.is_alive:
            workingprocess.start()
        workingprocess.join(2)
        print('Join')
        parent_conn.send('state')
        if parent_conn.poll():
            result = parent_conn.recv()
            print("RESULT",result)
        #taskslock.acquire()
        #tasks['uniqueid'] = str(uuid.uuid4())
        #taskslock.release()
        #print('Join')

def main():
    parser = argparse.ArgumentParser(description='WellFare Workers')
    parser.add_argument('-c', '--config', default=None , help='Workers file, in JSON format')
    parser.add_argument('-p', '--pfile', default=None, help='pyLoadBalancer parameter file, in JSON format')
    args = parser.parse_args()

    with open(os.path.join(os.path.dirname(__file__), 'parameters.json'), 'r') as fp:
        CONSTANTS = json.load(fp) #Loading default constants
    if parametersfile != None:
        try:
            with open(parametersfile, 'r') as fp:
                CONSTANTS.update(json.load(fp)) #updating constants with user defined ones
        except:
            cprint('ERROR : %s is not a valid JSON file'%parametersfile, 'FAIL')
            sys.exit()

    workers = {"id" : "idworker1", "mintaskpriority":0, "maxtaskpriority"=0}

    if args.workers + args.lowpworkers == 0:
        print('NO WORKER TO START : please refer to --help')
        sys.exit(2)

    increment = 0
    for i in range(args.workers):
        process = multiprocessing.Process(target=worker, args=(args.name + str(args.namenumber+increment), args.workerip ,args.LBPort+increment,args.HCPort+increment,0,args.pfile))
        process.start()
        increment += 1
    for i in range(args.lowpworkers):
        process = multiprocessing.Process(target=worker, args=(args.name + str(args.namenumber+increment), args.workerip ,args.LBPort + increment, args.HCPort + increment,10,args.pfile))
        process.start()
        increment += 1

    process.join()

if __name__ == "__main__":
    main()
