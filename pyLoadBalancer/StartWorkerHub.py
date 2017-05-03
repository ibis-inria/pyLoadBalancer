#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Starts the hub of Workers

exiting = False


def startWorkerHub(pfile, tasks, returnStartFct):
    import os
    import sys
    import multiprocessing

    WorkerHubProcess = multiprocessing.Process(
        target=startWorkerHubProcess, args=(pfile, tasks))

    WorkerHubProcess.start()

    if returnStartFct:
        return [WorkerHubProcess, startWorkerHubProcess]
    else:
        return WorkerHubProcess


def startWorkerHubProcess(pfile, tasks):
    import os
    import sys
    from pyLoadBalancer.WorkerHub import WorkerHub
    global exiting

    WKHub = WorkerHub(parametersfile=pfile)

    for task in tasks:
        WKHub.addTask(task, tasks[task])

    WKHub.startWKHUB()


if __name__ == "__main__":
    print('Please start LoadBalancer using a Python Script, by calling the non blocking function startLoadBalancer(parameterfile, tasksdict)')
