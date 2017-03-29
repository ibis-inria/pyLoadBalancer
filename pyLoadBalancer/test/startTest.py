from tprint import tprint
import time
from pyLoadBalancer import startWorkerHub

pfile = "configtest.json"


def hellotask(**kwargs):
    if kwargs.get('task').get('extra') == "POLITE":
        return "Good morning"
    else:
        return "HI"


def waitingtask(**kwargs):
    if kwargs.get('task').get('time') == None:
        time.sleep(1)
    else:
        time.sleep(kwargs.get('task').get('time'))
    return True


def mainstart():
    from Tests import Tests
    tests = Tests(pfile)
    tests.processes.append(startWorkerHub(
        pfile, {'HELLO': hellotask, 'WAIT': waitingtask}))

    time.sleep(1)
    tprint('Waiting before starting tests...', 'WARNING')
    time.sleep(2)
    tprint(str(len(tests.tests)) + ' tests will be performed.', 'WARNING')

    if not tests.all_alive():
        return

    from pyLoadBalancer import Client
    CL = Client(parametersfile=pfile)

    failed = []
    for testName in tests.tests:
        testResult = tests.tests[testName](CL)
        if testResult == True:
            tprint(testName + ' : pass', 'OKGREEN')
        else:
            failed.append(testName)
            tprint(testName + ' : failed', 'FAIL')
            tprint(str(testResult), 'FAIL')

        if not tests.all_alive():
            return

    if len(failed) == 0:
        tprint("____________________________", 'OKGREEN')
        tprint("", 'OKGREEN')
        tests.exit_test()
        tprint("____________________________", 'OKGREEN')
    else:
        tprint("____________________________", 'FAIL')
        tprint("", 'FAIL')
        tprint("THE FOLOWING TESTS FAILED :", 'FAIL')
        for testName in failed:
            tprint(testName, 'FAIL')
        tprint("____________________________", 'FAIL')
        tests.exit_test("FAILED")


if __name__ == '__main__':
    mainstart()
