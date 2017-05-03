#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

import pyLoadBalancer

setup(
    name='pyLoadBalancer',
    version=pyLoadBalancer.__version__,
    packages=find_packages(),
    author="Yannick Martin - INRIA IBIS",
    author_email='janiick@gmail.com',
    description="A Load Balancer in Pure Python",
    long_description=open('README.md').read(),
    # use the URL to the github repo
    url='https://github.com/ibis-inria/pyLoadBalancer',
    download_url='https://github.com/ibis-inria/pyLoadBalancer/archive/0.1.tar.gz',
    keywords=['load-balancer', 'multiprocessing', 'cluster-computing',
              'clustering', 'loadbalancing', 'monitoring'],
    install_requires=["pyzmq", "json", "tornado", "psutil", "colorama"],
    include_package_data=True,
    entry_points={
        'console_scripts': ['pyLoadBalancer_LB=pyLoadBalancer.LoadBalancer:main', 'pyLoadBalancer_HC=pyLoadBalancer.HealthCheck:main', 'pyLoadBalancer_Monitor=pyLoadBalancer.Monitor.MonitoringApp:main'],
    },
    license="LGPL",
)
