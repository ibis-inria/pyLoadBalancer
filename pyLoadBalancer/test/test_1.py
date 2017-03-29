#### TEST 1 ####
# Send 50 HELLO requests, wait sequantially for answer #
import time


def test(CL):
    taskids = []
    for i in range(50):
        taskids.append(CL.sendTask('HELLO', {}, 0)['taskid'])

    for taskid in taskids:
        LBanswer = CL.getTask(taskid)
        while LBanswer.get('progress') == 0:
            time.sleep(0.05)
            LBanswer = CL.getTask(taskid)
        if LBanswer.get('result') != 'HI':
            return "Worker anwsered '" + str(LBanswer.get('result')) + "' instead of 'HI' to command HELLO"

    return True
