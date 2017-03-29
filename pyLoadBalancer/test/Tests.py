from tprint import tprint
import os
import sys
import imp
from pyLoadBalancer import startAll
import time


class Tests:
    def __init__(self, pfile):
        # Get test_*.py files
        self.tests = {}
        for filename in os.listdir('.'):
            if filename.endswith(".py") and filename.startswith('test_'):
                modulename = os.path.splitext(filename)[0]
                fp, pathname, description = imp.find_module(
                    modulename, path=['.'])
                try:
                    mod = imp.load_module(
                        modulename, fp, pathname, description)
                    self.tests[modulename] = getattr(mod, "test")

                finally:
                    if fp:
                        fp.close()
            else:
                continue

        self.processes = startAll(pfile)
        self.processesnames = ['Load Balancer', 'Health Check', 'Monitor']

    def exit_test(self, error=None):
        for p in self.processes:
            p.terminate()
        for p in self.processes:
            p.join()
        if error != None:
            tprint("EXITED - " + str(error), "FAIL")
        else:
            tprint("ALL TESTS PASSED", "OKGREEN")
        return

    def all_alive(self):
        ok = True
        for i, p in enumerate(self.processes):
            if not p.is_alive():
                ok = False
                tprint(
                    "ERROR : " + self.processesnames[i] + "PROCESS IS DEAD...", "FAIL")
        if not ok:
            self.exit_test("DEAD PROCESS")
        return ok
