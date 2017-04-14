# Starts the hub of Workers
# tasks is a dictionnary containing :
# { 'taskname' : taskfunction, 'tasknumber2' : taskfunction2, ...}


def startWorkerHub(pfile, tasks, returnStartFct):
    import os
    import sys
    import multiprocessing
    import atexit
    import signal

    WorkerHubProcess = multiprocessing.Process(
        target=startWorkerHubProcess, args=(pfile, tasks))

    def on_exit(*args):
        WorkerHubProcess.terminate()
        WorkerHubProcess.join()

    atexit.register(on_exit)
    signal.signal(signal.SIGTERM, on_exit)
    signal.signal(signal.SIGINT, on_exit)
    WorkerHubProcess.start()

    if returnStartFct:
        return [WorkerHubProcess, startWorkerHubProcess]
    else:
        return WorkerHubProcess


def startWorkerHubProcess(pfile, tasks):
    import os
    import sys
    import atexit
    import signal
    from pyLoadBalancer.WorkerHub import WorkerHub

    WKHub = WorkerHub(parametersfile=pfile)

    for task in tasks:
        WKHub.addTask(task, tasks[task])

    atexit.register(WKHub.terminateWKHub)
    signal.signal(signal.SIGTERM, WKHub.terminateWKHub)
    signal.signal(signal.SIGINT, WKHub.terminateWKHub)

    WKHub.startWKHUB()


if __name__ == "__main__":
    print('Please start LoadBalancer using a Python Script, by calling the non blocking function startLoadBalancer(parameterfile, tasksdict)')
