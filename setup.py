#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

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
    license="GPL",
)
