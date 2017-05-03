#!/usr/bin/env python
# -*- coding: utf-8 -*-


def startAll(pfile=None, returnStartFct=False):
    import os
    import sys
    import multiprocessing
    import time

    LBProcess = multiprocessing.Process(target=startLBProcess, args=(pfile,))
    LBProcess.start()

    HCProcess = multiprocessing.Process(target=startHCProcess, args=(pfile,))
    HCProcess.start()

    MonitorProcess = multiprocessing.Process(
        target=startMonitorProcess, args=(pfile,))
    MonitorProcess.start()
    if returnStartFct:
        return [[LBProcess, HCProcess, MonitorProcess], [startLBProcess, startHCProcess, startMonitorProcess]]
    else:
        return [LBProcess, HCProcess, MonitorProcess]


def startLBProcess(pfile):
    import os
    import sys
    from pyLoadBalancer import LoadBalancer
    # sys.stdout = open(os.path.join('log','LB.log'), 'a+')
    # sys.stderr = open(os.path.join('log','LB_error.log'), 'a+')
    LB = LoadBalancer(parametersfile=pfile)
    LB.startLB()


def startHCProcess(pfile):
    import os
    import sys
    import time
    from pyLoadBalancer import HealthCheck
    # sys.stdout = open(os.path.join('log','HC.log'), 'a+')
    # sys.stderr = open(os.path.join('log','HC_error.log'), 'a+')
    HC = HealthCheck(parametersfile=pfile)
    time.sleep(3)
    HC.startHC()


def startMonitorProcess(pfile):
    import os
    import sys
    from pyLoadBalancer.Monitor import MonitoringApp
    MonitoringApp.startMonitorServer(parametersfile=pfile)


if __name__ == "__main__":
    print('Please start LoadBalancer using a Python Script, by calling the non blocking function startLoadBalancer(parameterfile)')
