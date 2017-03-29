def startAll(pfile):
    import os
    import sys
    import multiprocessing
    import atexit

    LBProcess = multiprocessing.Process(target=startLBProcess, args=(pfile,))
    atexit.register(LBProcess.terminate)
    LBProcess.start()

    HCProcess = multiprocessing.Process(target=startHCProcess, args=(pfile,))
    atexit.register(HCProcess.terminate)
    HCProcess.start()

    MonitorProcess = multiprocessing.Process(
        target=startMonitorProcess, args=(pfile,))
    atexit.register(MonitorProcess.terminate)
    MonitorProcess.start()

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
    time.sleep(1)
    HC.startHC()


def startMonitorProcess(pfile):
    import os
    import sys
    from pyLoadBalancer.Monitor import MonitoringApp
    MonitoringApp.startMonitorServer(parametersfile=pfile)


if __name__ == "__main__":
    print('Please start LoadBalancer using a Python Script, by calling the non blocking function startLoadBalancer(parameterfile)')
