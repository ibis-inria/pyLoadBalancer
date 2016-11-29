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

def workerloop(**kwargs):
    setProcessPriority(kwargs["processpriority"])
    test = 0
    time.sleep(2) #sleep when start or restart
    conn = kwargs["conn"]
    conn.send({"HELLO":100})

    while True:
        msg = conn.recv()
        if ('funct' in msg) and ('taskname' in msg) and ('task' in msg) and ('arguments' in msg) :
            print('WORKING ON',msg['taskname'])
            taskresult = msg['funct'](task=msg['task'],arguments=msg['arguments'])
            conn.send(taskresult)
        else:
            print('TASK NOT WELL FORMATTED',msg)
            conn.send({"WK":"ERROR"})


        #if "HELLO" in msg:
        #    conn.send({"HELLO":100})
        #elif msg == "state":
        #    conn.send({"ok":100})
        #else:
        #    conn.send({"WK":"ERROR"})

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
        #self.task = manager.dict()
        #self.result = manager.dict()

        self.mintaskpriority = mintaskpriority
        self.maxtaskpriority = maxtaskpriority
        self.processpriority = processpriority

        self.startProcess()

        self.workingon = None
        self.state = 0
        self.laststate = time.time()

    def terminateProcess(self):
        try:
            print('TERMINATING PROCESS')
            self.process.terminate()
        except:
            try:
                print('TERMINATING PROCESS')
                self.process.kill()
            except:
                print('ERROR KILLING PROCESS')
                pass
            pass

    def startProcess(self):
        self.parent_conn, self.child_conn = multiprocessing.Pipe()
        self.process = multiprocessing.Process(target=workerloop, kwargs={'conn': self.child_conn, 'id':self.id, 'processpriority':self.processpriority})
        self.process.start()



class WorkerHub:
    def __init__(self, ip, lbrepport, healthport, parametersfile=None):

        with open(os.path.join(os.path.dirname(__file__), 'parameters.json'), 'r') as fp:
            self.CONSTANTS = json.load(fp) #Loading default constants
        if parametersfile != None:
            try:
                with open(parametersfile, 'r') as fp:
                    self.CONSTANTS.update(json.load(fp)) #updating constants with user defined ones
            except:
                print('ERROR : %s is not a valid JSON file'%parametersfile)
                sys.exit()

        self.manager = multiprocessing.Manager()
        self.workers = {}

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

        self.taskList = {}
        self.cpustate = psutil.cpu_percent()
        self.lastcpustate = time.time()

    def addTask(self, taskname, taskfunct, **kwargs):
        if taskname not in self.taskList:
            self.taskList[taskname] = {'funct':taskfunct, 'kwargs':kwargs}
        else:
            cprint('TASK %s ALREADY EXISTS, SKIPPING addTask' % taskname, 'FAIL')

    def rmvTask(self, taskname):
        if taskname in self.taskList:
            del self.taskList[taskname]

    def sendState(self, worker, percentDone=None, resultmessage=None, taskid=None, to='LB', CPUonly = False):
        if percentDone == -1:
            message = {'workerid': worker, 'workerstate': -1}
            self.pushStateSock.send_json(message)
            return
        if isinstance( worker, str ):
            worker = self.workers[worker]

        if percentDone == None:
            percentDone = worker.state

        worker.laststate = time.time()
        if CPUonly:
            message = {'workerid': worker.id, 'workerstate': 'CPUonly', 'workercpustate': self.cpustate}
        else:
            message = {'workerid': worker.id, 'workerip': self.ip, 'workerport': self.lbrepport,
                       'workerhealthport': self.healthport, 'workerstate': percentDone,
                       'workerpriority' : worker.processpriority, 'minpriority' : worker.mintaskpriority, 'maxpriority' : worker.maxtaskpriority,
                       'workerresult': resultmessage, 'taskid' : taskid, 'workercpustate': self.cpustate, 'workingon': worker.workingon}

        if to == 'LB':
            self.pushStateSock.send_json(message)

    def startWKHUB(self,workers):

        print('Start Worker Hub')
        print('    WKHUB_IP:', self.ip)
        print('    WKHUB_LBport:', self.lbrepport)
        print('    WKHUB_HCport:', self.healthport)

        for keys, values in self.CONSTANTS.items():
            print('   ', keys, ':', values)

        for i in range(0,len(workers),4):
            for n in range(0,workers[i]):
                worker = Worker(workers[i+1] , workers[i+2], workers[i+3])
                self.workers[worker.id] = worker
                print('Start Worker ', self.workers[worker.id].id)
                print('    WK_PRIORITY:', self.workers[worker.id].processpriority)
                print('    WK_MINTASKPRIORITY:', self.workers[worker.id].mintaskpriority)
                print('    WK_MAXTASKPRIORITY:', self.workers[worker.id].maxtaskpriority)


        while True:


            if time.time() - self.lastcpustate > 0.5:
                self.cpustate = psutil.cpu_percent()
                self.lastcpustate = time.time()

            sockets = dict(self.poller.poll(400))

            for workerid in self.workers:
                if not self.workers[workerid].process.is_alive():
                    print('RESTARTING WORKER PROCESS',self.workers[workerid].id)
                    self.workers[workerid].startProcess()

                #getting worker results
                while self.workers[workerid].parent_conn.poll():
                    result = self.workers[workerid].parent_conn.recv()
                    print('GOT WORKER RESULT',result)
                    if result == {"HELLO":100}:
                        self.workers[workerid].state = 100
                        self.workers[workerid].workingon = None
                        self.sendState(workerid,"HELLO")
                    else:
                        self.workers[workerid].state = 100
                        self.sendState(workerid,resultmessage=result,taskid=self.workers[workerid].workingon)
                        self.workers[workerid].workingon = None


                if (not sockets) and (self.workers[workerid].state == 100):
                    if (self.workers[workerid].laststate + 1 < time.time()):
                        #print('%s - %s - NOTHING TO DO' % (self.workers[workerid].id, time.strftime('%H:%M:%S')))
                        self.sendState(workerid,"UP")
                        #self.sendCPUState(workerid,cpustate)
                       #self.sendState(self.workers[workerid].state,workerid)

            if self.LBrepSock in sockets:
                print('RECEIVING')
                msg = self.LBrepSock.recv_json()
                #print("WORKER MSG", msg)
                if ('workerid' not in msg) or (msg['workerid'] not in self.workers) :
                    print("UNKNOWN WORKER", msg.get('workerid'))
                    self.LBrepSock.send_json({'WK':'DOWN'})

                else:
                    worker = self.workers[msg['workerid']]
                    #print(self.id, " received %r" % msg)
                    if msg['TASK'] == 'CANCEL':
                            if (worker.state < 100) and (msg['taskid'] == worker.workingon):
                                self.LBrepSock.send_json({'WK':'OK'})
                                worker.terminateProcess()
                            else:
                                self.LBrepSock.send_json({'WK':'ERROR'})

                    elif (worker.state < 100) and (worker.workingon != None):
                        print("WORKER ALREADY WORKING", msg['workerid'])
                        self.LBrepSock.send_json({'WK':'ERROR'})

                    elif msg['TASK'] == 'READY?':
                        self.LBrepSock.send_json({'WK':'OK'})
                        self.sendState(worker)

                    elif msg['TASK'] == 'EXIT':
                        self.LBrepSock.send_json({'WK':'OK'})
                        for workerid in self.workers:
                            self.workers[workerid].terminateProcess()
                        break

                    elif msg['TASKNAME'] in self.taskList:
                        self.LBrepSock.send_json({'WK':'OK'})
                        #SENDING TASK TO TASK FUNCTION
                        #print('WORKING ON TASK',msg['taskid'])
                        worker.parent_conn.send({'funct':self.taskList[msg['TASKNAME']]['funct'],'taskname':msg['TASKNAME'],'task':msg['TASK'],'arguments':self.taskList[msg['TASKNAME']]['kwargs']})
                        print("TASK SENT TO WORKER")
                        #self.workingprocess = multiprocessing.Process(target=self.processtask, args=(self.taskList[msg['TASKNAME']]['funct'],self.taskresult, self.id), kwargs={'task':msg['TASK'],'arguments':self.taskList[msg['TASKNAME']]['kwargs']})
                        worker.state = 0
                        worker.workingon = msg['taskid']
                        ##taskresult = self.taskList[msg['TASKNAME']]['funct'](task=msg['TASK'],arguments=self.taskList[msg['TASKNAME']]['kwargs'])

                    else:
                        print('WORKER %s - UNKNOWN COMMAND %s'% (worker.id, msg['TASKNAME']))
                        self.LBrepSock.send_json({'WK':'UNKNOWN'})



            if self.HCrepSock in sockets:
                msg = self.HCrepSock.recv_json()
                print("WK: HCmsg")
                if msg['HEALTH'] == 'CHECKWORKERS' and ('workerid' in msg):
                    if isinstance(msg['workerid'],list):
                        for workerid in msg['workerid']:
                            if workerid in self.workers:
                                self.HCrepSock.send_json({'workerid': workerid, 'workerstate' : self.workers[workerid].state})
                                self.sendState(workerid, CPUonly=True)
                    else:
                        self.HCrepSock.send_json({msg['HEALTH']: 'COMMAND UNKNOWN'})

                else:
                    self.HCrepSock.send_json({msg['HEALTH']: 'COMMAND UNKNOWN'})




if __name__ == "__main__":
    print('Please start workerHub using a Python Script')
