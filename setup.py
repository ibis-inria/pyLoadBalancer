#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

import pyLoadBalancer

setup(

    name='pyLoadBalancer',
    version=pyLoadBalancer.__version__,

    packages=find_packages(),
    author="Yannick Martin",

    description="A Load Balancer in Pure Python",

    long_description=open('README.md').read(),

    install_requires= ["pyzmq","tornado","psutil"],

    include_package_data=True,

    entry_points = {
        'console_scripts': ['pyLoadBalancer_LB=pyLoadBalancer.LoadBalancer:main','pyLoadBalancer_HC=pyLoadBalancer.HealthCheck:main','pyLoadBalancer_Monitor=pyLoadBalancer.Monitor.MonitoringApp:main'],
    },

    license="WTFPL",


)
