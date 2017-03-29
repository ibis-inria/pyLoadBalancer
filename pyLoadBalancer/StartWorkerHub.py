# Starts the hub of Workers
# tasks is a dictionnary containing :
# { 'taskname' : taskfunction, 'tasknumber2' : taskfunction2, ...}


def startWorkerHub(pfile, tasks):
    import os
    import sys
    import multiprocessing
    import atexit

    WorkerHubProcess = multiprocessing.Process(
        target=startWorkerHubProcess, args=(pfile, tasks))
    atexit.register(WorkerHubProcess.terminate)
    WorkerHubProcess.start()

    return WorkerHubProcess


def startWorkerHubProcess(pfile, tasks):
    import os
    import sys
    from pyLoadBalancer.WorkerHub import WorkerHub

    WKHub = WorkerHub(parametersfile=pfile)

    for task in tasks:
        WKHub.addTask(task, tasks[task])

    WKHub.startWKHUB()


if __name__ == "__main__":
    print('Please start LoadBalancer using a Python Script, by calling the non blocking function startLoadBalancer(parameterfile, tasksdict)')
