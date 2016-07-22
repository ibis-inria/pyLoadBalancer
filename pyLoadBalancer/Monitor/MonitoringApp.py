#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging
import tornado.auth
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import os.path
import uuid
import json
import pprint
from  tornado.escape import json_decode
from  tornado.escape import json_encode
import time
import zmq

from tornado.options import define, options

define("port", default=8000, help="run on the given port", type=int)

# Constants definitions
with open(os.path.join(os.path.dirname(__file__), '../parameters.json'), 'r') as fp:
    CONSTANTS = json.load(fp)
LB_HEALTHADRESS = 'tcp://' + CONSTANTS['LB_IP'] + ':' + str(CONSTANTS['LB_HCREPPORT'])


def setLBReqSock(LBReqSock):
    # self.LBReqSock = self.context.socket(zmq.REQ)
    LBReqSock.setsockopt(zmq.RCVTIMEO, CONSTANTS['SOCKET_TIMEOUT'])  # Time out when asking worker
    LBReqSock.setsockopt(zmq.SNDTIMEO, CONSTANTS['SOCKET_TIMEOUT'])
    LBReqSock.setsockopt(zmq.REQ_RELAXED, 1)
    LBReqSock.connect(LB_HEALTHADRESS)
    print('MONITOR - Conected to ', LB_HEALTHADRESS)

def sendReq(LBReqSock,command):
    try:
        LBReqSock.connect(LB_HEALTHADRESS)
        command['MONITOR'] = command.pop('iwouldlike')
        print('SENDING : ', command)
        LBReqSock.send_json(command)
        return LBReqSock.recv_json()
    except Exception as e:
        print(CONSTANTS['FAIL'], 'MONITOR - FAILED REQUESTING LOAD BALANCER: LB DOWN ?', str(e), CONSTANTS['ENDC'])
        LBReqSock.disconnect(LB_HEALTHADRESS)
        setLBReqSock(LBReqSock)
        return 0
        pass

context = zmq.Context()
LBReqSock = context.socket(zmq.REQ)
setLBReqSock(LBReqSock)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/jsontoLB/", WorkersHandler)
        ]
        settings = dict(
            debug=True,
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static")
        )
        tornado.web.Application.__init__(self, handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html", messages=None)


class WorkersHandler(tornado.web.RequestHandler):
    def post(self):
        json_obj = json_decode(self.request.body)
        print('Post data received')

        for key in list(json_obj.keys()):
            print('key: %s , value: %s' % (key, json_obj[key]))

        if 'iwouldlike' in json_obj:
            response_to_send = sendReq(LBReqSock,json_obj)

        print('Response to return')
        pprint.pprint(response_to_send)

        self.write(json.dumps(response_to_send))


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()

