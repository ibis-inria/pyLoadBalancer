# pyLoadBalancer

This package contains a LoadBalancer that allows a list of tasks to be distributed to Workers.

## Install

To install the pyLoadBalancer package, simply run :
```
python setup.py install
```

## Getting Started


The following scheme explains the use of the package :

```

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
                |    +-------------------+     |     +----------+
+----------+    |                              |
| Client 3 +----+                              |     +----------+
+----------+                                   +---> |          |
                                                     | Worker 3 |
    ...                                              |          |
                                                     +----------+
                                                         ...

```

## Classes

The JSONLoadBalancer Package contains 4 main classes:
1. The Load Balancer, that distribute tasks
2. The Helth Check, that monitors the Load Balancer
3. The Client, that send tasks
4. The Worker, that receive tasks

All the messages between the classes are exchanged in json format.

## Starting the Load Balancer

To start the LoadBalancer, two python scripts need to be executed :

1. The LoadBalancer itself. Simply call the following script from command line :
```sh
pyLoadBalancer_LB
```
2. The HealthCheck module that is launched by :
```sh
pyLoadBalancer_HC
```
You should see the HealthCheck exchanging information with the LoadBalancer. As there is still no workers to do the job, the HealthCheck should print the following warning :
>HC - WARNING : LB HAS NO WORKERS.  

If you get a error message, please check that the two scripts are running, and if yes, check your firewall settings

Note that it is possible to execute the HealthCheck script on another computer than the LoadBalancer one. See advanced uses.

## Defining Workers

Now the LoadBalancer core is running, workers have to be run. Workers are configured to connected automatically to the Load Balancer.  
Insert a worker to your python application by using the following syntax :

```python
from JSONLoadBalancer import Worker
WK = Worker(id, lbport, healthport)
```

Where :
  - `id` (string) is the worker unique id (using same id for two different workers will lead to at best only one active worker.)
  - `lbport` (int) and `healthport` (int) are two ports listened by the worker in order to receive task from the Load Balancer and receive message from the Health Check

Then you will redirect the task the worker will receive to the corresponding python function that will do the job.

```python
WK.addTask('DIAG',diagTask)
```

Here, when the worker receive a task named `'DIAG'`, it will call the diagTask function.  
A task function must be in the form :
```python
def taskFunction(**kwargs):
    task = kwargs['tasks']
    #do something with task
    return
```
The first kwargs argurments will be `kwargs['tasks']` and contains the task message coming from the Client.

Then, when all tasks are defined, start the worker using :
```python
WK.startWK()
```

## Starting Client

Now we have a pretty consistent Load Balancer with active workers. Let's execute the Client side that will send task to the Load Balancer. Use the following syntax :

```python
from JSONLoadBalancer import Client
CL = Client()
```

Then create the task you want to send. It simply is a python dictionnary that contains the description of the task to be done :

```python
task = {'data': '/scratch/data/matrix19160.npy', 'load': 12}
```

The dictionnary must be JSON serializable, because sockets are using json format to communicate between eachothers.  
Note that there are two reserved keys, that are `'HELLO'` and `'TASK'`, your task dict should not contain these two keys.

When the task is to be sent, send it using :

```python
CL.sendTask(taskname,task)
```

Where `taskname` (string) is the name of the task (the one you set for the worker side)  

## Monitoring
A monitoring interface is available to easilly monitor the Load Balancer status (queing task, worker socket)

## Advanced usages

- Update worker state: if long task, can send socket to LB to send worker state
- More than one queue (manual sending to given queue by client)
- Learning parameters (automatic queue selection by LB)
- 
- ...

## Licence

?


