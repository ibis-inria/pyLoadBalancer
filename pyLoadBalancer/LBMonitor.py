#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module implements a web interface that gives information on the LoadBalancing activity.

To launch the Monitored Web Interface, enter in a Terminal ;
    bokeh serve LBMonitor.py --show

This will open an http server on your machine and a new browser window that display the Monitor.

Note that the "log" option must be set to True when starting the LoadBalancer and the HealthCheck.
"""

from bokeh.io import curdoc
from bokeh.models import ColumnDataSource,DatetimeTickFormatter,Range1d, LinearAxis, LogAxis
from bokeh.plotting import figure
import datetime
import numpy as np
timeout = 500
from matplotlib import cm,colors
from math import ceil,log10



keylist = ['times','timesout','load0','load1','load2','left','bottom']
LBkeylist = ['zeros','LBtimes','LBtimesEnd','LBload0','LBload1','LBload2','QueuedTasks','DoneTasks','halfDoneTasks','minWaitTime','maxWaitTime','lowPQueuedTasks','lowPDoneTasks','halflowPDoneTasks','lowPminWaitTime','lowPmaxWaitTime','LBleft','LBbottom']

def updatesource():
    with open('workerslive.log', 'r') as logfile:
        datalist = logfile.read().splitlines(True)

    datasource = {}
    for key in keylist:
        datasource[key] = []

    for line in datalist:
        linedata = line.split()

        datasource['times'].append(datetime.datetime.strptime(linedata[0], "%Y-%m-%dT%H:%M:%S.%f"))
        if len(datasource['times'])>1:
            datasource['left'].append(datasource['times'][-2])
        else:
            datasource['left'].append(datasource['times'][-1])
        datasource['bottom'].append(0)

        datasource['timesout'].append(timeout)

        if linedata[1]=='0':
            datasource['load0'].append(timeout)
            datasource['load1'].append(0)
            datasource['load2'].append(0)
        elif linedata[1] == '1':
            datasource['load0'].append(0)
            datasource['load1'].append(timeout)
            datasource['load2'].append(0)
        elif linedata[1] == '2':
            datasource['load0'].append(0)
            datasource['load1'].append(0)
            datasource['load2'].append(timeout)
        else:
            datasource['load0'].append(0)
            datasource['load1'].append(0)
            datasource['load2'].append(0)

        for i in range(2, len(linedata), 2):
            if linedata[i] in datasource:
                datasource[linedata[i]].append(linedata[i + 1])
            else:
                datasource[linedata[i]] = [linedata[i + 1]]

    return datasource

def updateLBsource():
    ####LB LOG
    with open('LB.log', 'r') as logfile:
        datalist = logfile.read().splitlines(True)

    dataLBsource = {}
    for key in LBkeylist:
        dataLBsource[key] = []

    for line in datalist:
        linedata = line.split()
        dataLBsource['LBtimes'].append(datetime.datetime.strptime(linedata[0], "%Y-%m-%dT%H:%M:%S.%f"))
        dataLBsource['LBtimesEnd'].append(datetime.datetime.strptime(linedata[1], "%Y-%m-%dT%H:%M:%S.%f"))
        dataLBsource['zeros'].append(0)
        if len(dataLBsource['LBtimes']) > 1:
            dataLBsource['LBleft'].append(dataLBsource['LBtimes'][-2])
        else:
            dataLBsource['LBleft'].append(dataLBsource['LBtimes'][-1])
        dataLBsource['LBbottom'].append(-1)

        if linedata[2] == '0':
            dataLBsource['LBload0'].append(int(linedata[2]))
            dataLBsource['LBload1'].append(-1)
            dataLBsource['LBload2'].append(-1)
        elif linedata[2] == '1':
            dataLBsource['LBload0'].append(-1)
            dataLBsource['LBload1'].append(int(linedata[2]))
            dataLBsource['LBload2'].append(-1)
        elif linedata[2] == '2':
            dataLBsource['LBload0'].append(-1)
            dataLBsource['LBload1'].append(-1)
            dataLBsource['LBload2'].append(int(linedata[2]))
        else:
            dataLBsource['LBload0'].append(-1)
            dataLBsource['LBload1'].append(-1)
            dataLBsource['LBload2'].append(-1)

        dataLBsource['QueuedTasks'].append(int(linedata[3]))
        dataLBsource['DoneTasks'].append(int(linedata[4]))
        dataLBsource['halfDoneTasks'].append(int(linedata[4])/2)
        dataLBsource['minWaitTime'].append(float(linedata[5]))
        dataLBsource['maxWaitTime'].append(float(linedata[6]))
        '''mini,maxi = float(linedata[5]),float(linedata[6])
        if mini>0 and maxi >0:
            dataLBsource['minWaitTime'].append( 10**( (log10(mini)+log10(maxi))/2  ) ) #log mean
            dataLBsource['maxWaitTime'].append(maxi - mini)  # length
        else:
            dataLBsource['minWaitTime'].append(0)
            dataLBsource['maxWaitTime'].append(0)  # length'''



        dataLBsource['lowPQueuedTasks'].append(int(linedata[7]))
        dataLBsource['lowPDoneTasks'].append(int(linedata[8]))
        dataLBsource['halflowPDoneTasks'].append(int(linedata[8]) / 2)

        dataLBsource['lowPminWaitTime'].append(float(linedata[9]))
        dataLBsource['lowPmaxWaitTime'].append(float(linedata[10]))
        '''mini, maxi = float(linedata[9]), float(linedata[10])
        if mini > 0 and maxi > 0:
            dataLBsource['lowPminWaitTime'].append(10 ** ((log10(mini) + log10(maxi)) / 2))  # log mean
            dataLBsource['lowPmaxWaitTime'].append(maxi - mini)  # length
        else:
            dataLBsource['lowPminWaitTime'].append(0)
            dataLBsource['lowPmaxWaitTime'].append(0)  # length'''

    return dataLBsource

#LIVE WORKERS PLOT
p = figure(plot_width=1000, plot_height=300, x_axis_type='datetime',title='LIVE Workers Response Time - Timeout %sms' %timeout, y_range=Range1d(-timeout*0.1, timeout*1.4))
#p.logo = None
p.toolbar_location = None
p.yaxis[0].axis_label = 'Response Time (ms)'
p.xaxis[0].axis_label = 'Time'

datasource = updatesource()
source = ColumnDataSource(data=datasource)

p.quad(top='load0',bottom='bottom',left='left',right='times', source=source, fill_alpha=0.2, fill_color='green', line_width=0,  line_alpha=0, legend="Load 0")
p.quad(top='load1',bottom='bottom',left='left',right='times', source=source, fill_alpha=0.2, fill_color='blue', line_width=0,  line_alpha=0, legend="Load 1")
p.quad(top='load2',bottom='bottom',left='left',right='times', source=source, fill_alpha=0.2, fill_color='red', line_width=0,  line_alpha=0, legend="Load 2")


workers = []
for workerid in datasource:
    if not (workerid in keylist) :
        workers.append(workerid)

nbworkers = len(workers)
colorslist = ["#%02x%02x%02x" % (int(r), int(g), int(b)) for r, g, b, _ in 255*cm.autumn(colors.Normalize()(np.linspace(0,1,nbworkers)))]
for i in enumerate(workers):
    p.line(x='times', y=i[1], source=source, line_width=1, color=colorslist[i[0]],legend=i[1])
    p.circle(x='times', y=i[1], source=source, fill_color='white',line_color=colorslist[i[0]], size=5, legend=i[1])

p.line(x='times',y='timesout', line_color='red', line_width=2,line_alpha=0.5, source=source)

p.legend.orientation = "horizontal"
p.legend.location = "top_left"

p.xaxis.formatter=DatetimeTickFormatter(
    formats=dict(
    microseconds=["%H:%M:%S"],
    milliseconds=["%H:%M:%S"],
    seconds=["%H:%M:%S"],
    minsec=["%H:%M:%S"],
    minutes=["%H:%M:%S"],
    hourmin=["%H:%M:%S"],
    hours=["%H:%M:%S"],
    days=["%d/%m %Hh"],
    months=["%d/%m"],
    years=["%d/%m/%Y"]
    )
)

dataLBsource = updateLBsource()
LBsource = ColumnDataSource(data=dataLBsource)

##LOAD PLOT
p2 = figure(plot_width=1000, plot_height=150, x_axis_type='datetime',title='Load',y_range=Range1d(-0.5, 2.5),tools="pan,box_zoom,reset",logo = None)#,y_axis_type=None)
#ticker = SingleIntervalTicker(interval=1, num_minor_ticks=0)
#yaxis = LinearAxis(ticker=ticker)
#p2.add_layout(yaxis, 'left')

p2.yaxis[0].axis_label = 'Load'
p2.xaxis.formatter=DatetimeTickFormatter(
    formats=dict(
    microseconds=["%H:%M:%S"],
    milliseconds=["%H:%M:%S"],
    seconds=["%H:%M:%S"],
    minsec=["%H:%M:%S"],
    minutes=["%H:%M:%S"],
    hourmin=["%H:%M:%S"],
    hours=["%H:%M:%S"],
    days=["%d/%m %Hh"],
    months=["%d/%m"],
    years=["%d/%m/%Y"]
    )
)
p2.quad(top='LBload0',bottom='LBbottom',left='LBleft',right='LBtimes', source=LBsource, fill_alpha=0.2, fill_color='green', line_width=0,  line_alpha=0, legend="Load 0")
p2.quad(top='LBload1',bottom='LBbottom',left='LBleft',right='LBtimes', source=LBsource, fill_alpha=0.2, fill_color='blue', line_width=0,  line_alpha=0, legend="Load 1")
p2.quad(top='LBload2',bottom='LBbottom',left='LBleft',right='LBtimes', source=LBsource, fill_alpha=0.2, fill_color='red', line_width=0,  line_alpha=0, legend="Load 2")
p2.legend.orientation = "horizontal"
p2.legend.location = "top_left"

##QUEUES PLOT
p3 = figure(plot_width=1000, plot_height=300, x_axis_type='datetime',title='Done Tasks',tools="pan,box_zoom,reset",logo = None,y_range=Range1d( 0, 1.1*max(LBsource.data["DoneTasks"])))

p3.xaxis.formatter=DatetimeTickFormatter(
    formats=dict(
    microseconds=["%H:%M:%S"],
    milliseconds=["%H:%M:%S"],
    seconds=["%H:%M:%S"],
    minsec=["%H:%M:%S"],
    minutes=["%H:%M:%S"],
    hourmin=["%H:%M:%S"],
    hours=["%H:%M:%S"],
    days=["%d/%m %Hh"],
    months=["%d/%m"],
    years=["%d/%m/%Y"]
    )
)
mini,maxi = min(LBsource.data["lowPDoneTasks"]),max(LBsource.data["lowPDoneTasks"])
p3.extra_y_ranges = {'lowP': Range1d( 0, maxi*1.1)}
p3.add_layout(LinearAxis(y_range_name="lowP"), 'right')
p3.yaxis[0].axis_label = 'Done Tasks'
p3.yaxis[1].axis_label = 'Low Priority Done Tasks'
p3.xaxis[0].axis_label = 'Time'

#p3.circle(x='LBtimes', y='QueuedTasks', source=LBsource, line_width=1, legend='Queued Tasks')
#p3.circle(x='LBtimes', y='lowPQueuedTasks', source=LBsource, line_width=1, color='red',legend='Low Priority Queued Tasks')#,y_range_name="lowP")

'''for element in enumerate(dataLBsource['lowPQueuedTasks']):
    i = element[0]
    if dataLBsource['lowPQueuedTasks'][i] != 0:
        p3.line(x=[dataLBsource['LBtimes'][i],dataLBsource['LBtimes'][i]], y=[0,dataLBsource['lowPQueuedTasks'][i]], line_width=6,color='orange')

for element in enumerate(dataLBsource['QueuedTasks']):
    i = element[0]
    if dataLBsource['QueuedTasks'][i] != 0:
        p3.line(x=[dataLBsource['LBtimes'][i],dataLBsource['LBtimes'][i]], y=[0,dataLBsource['QueuedTasks'][i]], line_width=4)'''

p3.quad(left='LBtimes', right='LBtimesEnd', top='lowPDoneTasks',bottom='zeros',  source=LBsource, color='orange', legend='LowP Done Tasks',y_range_name="lowP",line_width=0)
p3.quad(left='LBtimes', right='LBtimesEnd', top='DoneTasks',bottom='zeros',  source=LBsource, legend='Done Tasks', alpha=0.5, line_width=0)

p3.legend.location = "top_left"
p3.legend.orientation = "horizontal"
##WAITING TIME PLOT
maxlog = 10**ceil(log10(max(LBsource.data["maxWaitTime"])))
maxloglowP = 10**ceil(log10(max(LBsource.data["lowPmaxWaitTime"])))

p4 = figure(plot_width=1000, plot_height=300, x_axis_type='datetime',title='Tasks Waiting Time',tools="pan,box_zoom,reset",logo = None,y_range=Range1d( maxlog/(10**7), maxlog), y_axis_type="log")

p4.xaxis.formatter=DatetimeTickFormatter(
    formats=dict(
    microseconds=["%H:%M:%S"],
    milliseconds=["%H:%M:%S"],
    seconds=["%H:%M:%S"],
    minsec=["%H:%M:%S"],
    minutes=["%H:%M:%S"],
    hourmin=["%H:%M:%S"],
    hours=["%H:%M:%S"],
    days=["%d/%m %Hh"],
    months=["%d/%m"],
    years=["%d/%m/%Y"]
    )
)

p4.extra_y_ranges = {'lowP': Range1d( maxloglowP/(10**7), maxloglowP)}
p4.add_layout(LogAxis(y_range_name="lowP"), 'right')

p4.yaxis[0].axis_label = 'Waiting Time (s)'
p4.yaxis[1].axis_label = 'Low Priority Waiting Time (s)'
p4.xaxis[0].axis_label = 'Time'

'''for element in enumerate(dataLBsource['maxWaitTime']):
    i = element[0]
    if dataLBsource['maxWaitTime'][i] > 0:
        p4.line(x=[dataLBsource['LBtimes'][i],dataLBsource['LBtimes'][i]], y=[dataLBsource['minWaitTime'][i],dataLBsource['maxWaitTime'][i]], line_width=2,legend='Tasks')

for element in enumerate(dataLBsource['lowPmaxWaitTime']):
    i = element[0]
    if dataLBsource['lowPmaxWaitTime'][i] > 0:
        p4.line(x=[dataLBsource['LBtimes'][i], dataLBsource['LBtimes'][i]],
                y=[dataLBsource['lowPminWaitTime'][i], dataLBsource['lowPmaxWaitTime'][i]],color='orange', line_width=2,legend='LowP Tasks')'''


p4.quad(left='LBtimes', right='LBtimesEnd', top='lowPmaxWaitTime',bottom='lowPminWaitTime', source=LBsource,color='orange', legend='LowP Tasks',y_range_name="lowP")
p4.quad(left='LBtimes', right='LBtimesEnd', top='maxWaitTime',bottom='minWaitTime', source=LBsource, legend='Tasks')

p4.line(x=[dataLBsource['LBtimes'][0], dataLBsource['LBtimes'][-1]], y=[1,1], line_width=1,legend='1s limit',line_dash=[5,5,5,5])
#p4.circle(x='LBtimes', y='maxWaitTime', source=LBsource, line_width=1, legend='Tasks')
#p4.circle(x='LBtimes', y='minWaitTime', source=LBsource, line_width=1, color='blue', legend='Tasks')
#p4.circle(x='LBtimes', y='lowPmaxWaitTime', source=LBsource, line_width=1, color='orange',legend='Low Priority Tasks',y_range_name="lowP")
#p4.circle(x='LBtimes', y='lowPminWaitTime', source=LBsource, line_width=1, color='red',legend='Low Priority Tasks')



p4.legend.location = "top_left"
p4.legend.orientation = "horizontal"

def update():
    datasource = updatesource()
    source.stream(datasource, len(datasource['times']))

curdoc().add_periodic_callback(update, 1000)
curdoc().add_root(p)
curdoc().add_root(p2)
curdoc().add_root(p3)
curdoc().add_root(p4)