#### TEST 2 ####
# Tasks with priority not corresponding to workers priority and cancel tasks #
import time


def test(CL):
    taskids = []
    # a task with priority ouside limits
    taskids.append(CL.sendTask('WAIT', {'time': 0.01}, 100000)['taskid'])
    # a task with negative priority
    taskids.append(CL.sendTask('WAIT', {'time': 0.01}, -100)['taskid'])

    time.sleep(1)
    LBanswers = CL.getTask(taskids)
    if len(LBanswers) != len(taskids):
        return 'LoadBalancer answer should contain ' + str(len(taskids)) + ' taskid, it does not.'

    for taskid in LBanswers:
        if LBanswers[taskid].get('progress') == 100:
            return "LB should have leaved two tasks queing (priority not in workers priority intervals)"

    if CL.cancelTask(taskids[0]).get('deleted') != True and CL.cancelTask(taskids[0]).get('from') != 'queue':
        return "LB did not anwser {'deleted': True, 'from': 'queue'} to cancelTask"
    if CL.cancelTask(taskids[0]).get('deleted') != False and CL.cancelTask(taskids[0]).get('from') != None:
        return "LB did not anwser {'deleted': False, 'from': None} to cancelTask with an already deleted taskid"

    if CL.cancelTask(taskids[1]).get('deleted') != True and CL.cancelTask(taskids[1]).get('from') != 'queue':
        return "LB did not anwser {'deleted': True, 'from': 'queue'} to cancelTask"

    LBanswers = CL.getTask(taskids)
    for taskid in LBanswers:
        if LBanswers[taskid].get('progress') != 'cancelled':
            return "Tasks seems not to have been canceled"

    return True
