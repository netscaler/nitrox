#!/usr/bin/env python

import argparse
import getopt
import os
import sys
import threading
from docker import Client
from docker import tls
from netscaler import NetscalerInterface

import logging
logger = logging.getLogger('docker_netscaler')


class DockerSwarmInterface:

    def __init__(self, swarm_url, swarm_tls_ca_cert, swarm_tls_cert,
                 swarm_tls_key, swarm_allow_insecure, app_info, netscaler):
        tls_config = False
        if not swarm_allow_insecure:
            if swarm_url.startswith("tcp"):
                swarm_url = swarm_url.replace("tcp", "https")
                logger.info("Using swarm url %s" % swarm_url)
            tls_config = tls.TLSConfig(client_cert=(swarm_tls_cert,
                                                    swarm_tls_key),
                                       verify=swarm_tls_ca_cert,
                                       assert_hostname=False)
        self.client = Client(base_url=swarm_url, tls=tls_config)
        self.app_info = app_info
        self.netskaler = netscaler
        self.lock = threading.Lock()

    def get_backends_for_app(self, app_label):
        logger.info("Getting backends for app label %s" % app_label)
        containers = self.client.containers(filters={'status': 'running',
                                                     'label': [app_label]})
        portConfigs = [n['Ports'] for n in containers]
        """
        [[{u'Type': u'tcp', u'PrivatePort': 443},
          {u'IP': u'0.0.0.0', u'Type': u'tcp', u'PublicPort': 807, u'PrivatePort': 80}],
          [{u'IP': u'0.0.0.0', u'Type': u'tcp', u'PublicPort': 806, u'PrivatePort': 80},
          {u'Type': u'tcp', u'PrivatePort': 443}]]
        """
        result = []
        for ports in portConfigs:
            for port in ports:
                if port.get('PublicPort'):
                    # TODO: handle the case where more than one port is exposed
                    result.append((port['IP'], port['PublicPort']))

        return result

    def configure_ns_for_app(self, app_key, appname):
        self.lock.acquire()
        try:
            app_label = app_key + "=" + appname
            backends = self.get_backends_for_app(app_label)
            # backends = map(lambda y: ("192.168.99.100", y[1]), backends)
            # TODO: remove above for actual swarm. With plain docker machine, host IP
            # is "0.0.0.0" -- that cannot be load balanced. Docker swarm supplies
            # correct host IP.
            logger.debug("Backends are %s" % str(backends))
            self.netskaler.configure_app(appname,  backends)
        finally:
            self.lock.release()

    def configure_all(self):
        app_key = self.app_info['appkey']
        appnames = map(lambda x: x['name'], self.app_info['apps'])
        logger.info("Configuring for app names: %s" % str(appnames))
        for appname in appnames:
            self.configure_ns_for_app(app_key, appname)
        self.watch_all_apps()
        self.wait_for_all()

    def watch_app(self, app_key, appname):
        app_label = app_key + "=" + appname
        events = self.client.events(
            filters={"event": ["start", "kill", "die"],
                     "label": [app_label]})
        for e in events:
            self.configure_ns_for_app(app_key, appname)

    def watch_all_apps(self):
        app_key = self.app_info['appkey']
        appnames = map(lambda x: x['name'], self.app_info['apps'])
        for appname in appnames:
            logger.debug("Watching for events for app: %s" % str(appname))
            t = threading.Thread(target=self.watch_app,
                                 args=(app_key, appname,))
            t.start()

    def wait_for_all(self):
        main_thread = threading.currentThread()
        for t in threading.enumerate():
            if t is main_thread:
                continue
            logging.debug('joining %s', t.getName())
            t.join()
