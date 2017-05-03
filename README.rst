pyLoadBalancer
==============

Licence
~~~~~~~

pyLoadBalancer has been developped by IBIS team (INRIA Grenoble
Rhône-Alpes, France) and is distributed under the GPL licence.

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your
option) any later version. This program is distributed in the hope that
it will be useful, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details. You should have received a
copy of the GNU General Public License along with this program. If not,
see http://www.gnu.org/licenses/.

--------------

Install
~~~~~~~

To install the pyLoadBalancer package, simply run :

::

    python setup.py install

--------------

Getting Started
~~~~~~~~~~~~~~~

The pyLoadBalancer Package contains 5 main objects: 1. The
``Load Balancer``, that distribute tasks 2. The ``Client``, that send
tasks 3. The ``Worker``, that receive tasks 4. The ``Health Check``,
that check the status of the Load Balancer *(optional)* 5. The
``Monitor``, a small web server that displays information on the Load
Balancer *(optional)*

The following scheme explains the relationship:

::


                           +--------------+
                           |              |     info     +----------+
                           | Health Check | <----------> |          |
                           |              |              | Worker 1 |
    +----------+  tasks    +------^-------+        +---> |          |
    | Client 1 +----+             |                |     +----------+
    +----------+    |             |info          task
                    |    +--------v----------+     |     +----------+
    +----------+    |    |                   |     |     |          |
    | Client 2 +-------->+   Load Balancer   | <-------> | Worker 2 |
    +----------+    |    |                   |     |     |          |
                    |    +--------^----------+     |     +----------+
    +----------+    |             |                |
    | Client 3 +----+                              |     +----------+
    +----------+           +------v-------+        +---> |          |
                           |    Monitor   |              | Worker 3 |
        ...                +--------------+              |          |
                                                         +----------+
                                                             ...

All the messages between objects are exchanged in json format.

Parameters
~~~~~~~~~~

pyLoadBalancer has to be configured in order to allow the communication
between the different objects (and also between different computers).

The default parameters are stored in ``parameters.json`` file.

Load Balancer parameters
''''''''''''''''''''''''

-  ``"SOCKET_TIMEOUT" : 500`` *Timeout for communication in ms (increase
   this values if computers are not inside the same local network)*
-  ``"LB_IP": "127.0.0.1"`` *IP of the LoadBalancer computer as visible
   for other objects of the Load Balancer, 127.0.0.1 means local
   computer*
-  ``"LB_WKPULLPORT": 5699`` *Port for communication with the workers*
-  ``"LB_HCREPPORT" : 5999`` *Port for communication with the healt
   check*
-  ``"LB_CLIENTPULLPORT" : 5799`` *Port for communication with clients*
-  ``"LB_QUEING_MAXPERUSER" : 1000`` *Maximum number of queuing task for
   a given user*

Workers parameters
''''''''''''''''''

-  ``"WKHUB_IP" : "127.0.0.1"`` *IP of the Worker computer as visible
   for the Load Balancer, 127.0.0.1 means local computer*
-  ``"WKHUB_LBPORT" : 8300`` *Port for communication with the Load
   Balancer*
-  ``"WKHUB_HCPORT" : 8301`` *Port for communication with the Health
   Check*
-  ``"WKHUB_WORKERS" : []`` *List of workers*

The list of workers is defined with the following template:

::

    {"nWorkers" : Number of workers, "minP" : minimum prority, "maxP": minimum prority, "processP" : process prority}

To start 12 workers, with 3 different load balancer priorities, and one
low process priority, use:

.. code:: json

            [ {"nWorkers" : 4, "minP" : 0, "maxP": 9, "processP" : 10},
              {"nWorkers" : 4, "minP" : 10, "maxP": 99, "processP" : 0},
              {"nWorkers" : 4, "minP" : 100, "maxP": 1000, "processP" : 0}
            ],

Monitor parameters
''''''''''''''''''

-  ``"MONITOR_IP": "127.0.0.1"`` *IP of the Monitor computer as visible
   for the user that wants to monitor the load balancer, 127.0.0.1 means
   local computer*
-  ``"MONITOR_PORT" : 9000,`` *Port used to access the monitor from a
   web browser*

--------------

Starting the Load Balancer core
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To start the LoadBalancer on one computer, run the following command :

.. code:: python

    from pyLoadBalancer import startAll
    startAll('parameters.json')

Where ``parameters.json`` is a parameter file as defined in the previous
section.

The ``startAll()`` function starts the core of the Load Balancer: - The
``Load Balancer``, that distribute tasks - The ``Helth Check``, that
check the status of the Load Balancer *(optional)* - The ``Monitor``, a
small web server that displays information on the Load Balancer
*(optional)*

There is still no client to ask for a job and no workers to do it, the
HealthCheck should therefore print the following warning :

{- HC - WARNING : LB HAS NO WORKERS. -}

If you get another error message, please check check your firewall and
antivirus settings that may block the communication between the Load
Balancer objects.

The LoadBalancer can be monitored by typing the monitor address
(http://localhost:9000 by default) in a web browser.

Note that it is possible to execute the core objects on separate
computers. See advanced uses.

--------------

Starting Workers
~~~~~~~~~~~~~~~~

Now the LoadBalancer core is running, workers have to be run. Workers
are configured to connect automatically to the Load Balancer (with the
help of the parameter file).

Workers can be created using the following syntax :

.. code:: python

    from pyLoadBalancer import WorkerHub
    WKHub = WorkerHub('parameters.json')

The workers have to learn what tasks they will perform and how to
perform them. This can be done by adding a task like:

.. code:: python

    WKHub.addTask('HELLO', helloFunction)

In this exemple, when the worker receive a task named ``HELLO``, it will
call the ``helloFunction``.

A task function should be in the following form:

.. code:: python

    def helloFunction(**kwargs):
        print('WORKER GOT TASK', kwargs)
        result = 'Hello %s %s !' % (kwargs.get('task').get('firstName'), kwargs.get('task').get('lastName'))
        #do something with task
        return result

kwargs arguments will contains the task sent by the Client. It can be
accessed by the worker task function using \`kwargs.get('task')\`\`

Then, when all tasks are defined, start the worker using :

.. code:: python

    WKHub.startWKHUB()

When the workers are started, you should see the Load Balancer console
displaying massages like ``LB - ADDING WORKER (worker_c0b28c1f)``

--------------

Starting Client
~~~~~~~~~~~~~~~

Now we have a pretty consistent Load Balancer with active workers. Let's
execute the Client side that will send task to the Load Balancer. Use
the following syntax:

.. code:: python

    from pyLoadBalancer import Client
    CL = Client('parameters.json')

Then create the task you want to send. It simply is a python dictionary
that corresponds the parameters of the task function to be done :

.. code:: python

    task = {'firstName': 'John', 'lastName': 'Doe'}

| The dictionnary must be JSON serializable, because sockets are using
  JSON format to communicate between each-others.
| When the task is to be sent, send it using:

.. code:: python

    taskid = CL.sendTask('HELLO', task, userid='username').get('taskid')

The Load Balancer will return a task unique id, that can be used to
asynchronously retrieved the status of the task:

.. code:: python

    taskinfo = CL.getTask(taskid)
    progress = taskinfo.get('progress')
    result = taskinfo.get('result')

The returned ``progress`` can take the following values: - ``None``
*taskid is not correct or task result in an error* - ``0`` *task is
queing* - ``100`` *task is done*

When the task is done, the ``result`` is return by the Load Balancer

Please note that the Load Balancer automatically remove tasks whose
result has been collected by the Client within 60 seconds.

A waiting (or processing) task can also be canceled by using the
following command:

.. code:: python

    CL.cancelTask(taskid)

--------------

Monitoring
~~~~~~~~~~

A monitoring interface is available to easilly monitor the Load Balancer
status (queing task, statistics ...)

It can be access by a web browser at the monitor address
(http://localhost:9000 by default).

--------------

Advanced usages
~~~~~~~~~~~~~~~

User priority
'''''''''''''

The username sent by clients have an influence on the priority of the
queuing tasks.

When a worker is available, the first task from the user that have the
lowest number of occupied worker will be processed.

Task priority
'''''''''''''

A task is sent by default with a zero priority. This priority can be
changed by setting the

.. code:: python

    taskid = CL.sendTask('HELLO', task, userid='username', priority=100)

This task will only be processed by a worker that follows minP ≥ 100 and
a maxP ≤ 100.

This behavior allows to keep available workers for high priority tasks.

Run on clusters of computers
''''''''''''''''''''''''''''

pyLoadBalancer is designed to be run in clusters of computers.

Every objects of pyLoadBalancer can be run by a different computer (one
computer can run the Load Balancer core, and few other computers can run
each one a hub of workers).

Configure the ``parameters.json`` in each computers in order to assign
the correct IPs and ports, and be sure to open corresponding ports.
