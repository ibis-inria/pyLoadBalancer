#### TEST 2 ####
# Send 100 HELLO POLITE requests, get tasks results until all done #
import time


def test(CL):
    taskids = []
    for i in range(100):
        taskids.append(CL.sendTask('HELLO', {'extra': 'POLITE'}, 10)['taskid'])

    LBanswers = CL.getTask(taskids)
    newtaskids = []

    if len(LBanswers) != len(taskids):
        return 'LoadBalancer answer should contain ' + str(len(taskids)) + ' taskid, it does not.'

    while len(LBanswers) > 0:
        for taskid in LBanswers:
            if LBanswers[taskid].get('progress') != 100:
                newtaskids.append(taskid)
            elif LBanswers[taskid].get('result') != "Good morning":
                return "Worker anwsered '" + str(LBanswers[taskid].get('result')) + "' instead of 'Good morning' to command HELLO with extra POLITE"
        time.sleep(0.1)
        LBanswers = CL.getTask(newtaskids)
        newtaskids = []

    return True
