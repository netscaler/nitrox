#!/usr/bin/env python

import argparse
import logging
import os
import sys
import json
sys.path.append(os.getcwd())
from swarm.docker_swarm import DockerSwarmInterface
from marathon.mesos_marathon import MarathonInterface
from kubernetes.kubernetes import KubernetesInterface
from netscaler import NetscalerInterface
from consul.cfg_file import ConfigFileDriver
import re
import base64

logging.basicConfig(level=logging.CRITICAL,
        format='%(asctime)s  - %(levelname)s - [%(filename)s:%(funcName)-10s]  (%(threadName)s) %(message)s')
logger = logging.getLogger('docker_netscaler')
logger.addFilter(logging.Filter('docker_netscaler'))
logger.setLevel(logging.DEBUG)


def docker_swarm(app_info, netskaler):
    parser = argparse.ArgumentParser(description='Process Docker client args')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--swarm-allow-insecure")
    group.add_argument("--swarm-tls-ca-cert")
    parser.add_argument("--swarm-url", required=True, dest='swarm_url')
    parser.add_argument("--swarm-tls-cert", required=False,
                        dest='swarm_tls_cert')
    parser.add_argument("--swarm-tls-key", required=False,
                        dest='swarm_tls_key')

    result = parser.parse_args()

    dokker = DockerSwarmInterface(result.swarm_url, result.swarm_tls_ca_cert,
                                  result.swarm_tls_cert, result.swarm_tls_key,
                                  result.swarm_allow_insecure,
                                  app_info, netskaler)
    dokker.configure_all()


def mesos_marathon(app_info, netskaler):
    parser = argparse.ArgumentParser(description='Process Marathon args')
    parser.add_argument("--marathon-url", required=True, dest='marathon_url')
    parser.add_argument("--marathon-user", dest='marathon_user')
    parser.add_argument("--marathon-password", dest='marathon_password')
    result = parser.parse_args()
    marathon = MarathonInterface(server=result.marathon_url,
                                 netskaler=netskaler,
                                 app_info=app_info,
                                 username=result.marathon_user,
                                 password=result.marathon_password)

    marathon.configure_ns_for_all_apps()
    marathon.watch_all_apps()


def kubernetes(appinfo, netskaler):
    parser = argparse.ArgumentParser(description='Process Kubernetes args')
    parser.add_argument("--kube-config", required=False,
                        dest='cfg', default=None)
    parser.add_argument("--kube-token", required=False,
                        dest='token', default=None)
    parser.add_argument("--kube-token-file", required=False,
                        dest='token_file', default=None)
    parser.add_argument("--kube-certificate-authority", required=False,
                        dest='ca', default=None)
    parser.add_argument("--kube-apiserver", required=False,
                        dest='server', default=None)
    parser.add_argument("--insecure-skip-tls-verify",
                        required=False, dest='insecure', default=None)

    result = parser.parse_args()

    # '{"appkey": "com.citrix.lb.appname", "apps": [{"name": "foo"},
    #  {"name": "bar"}]}'
    app_info = json.loads(os.environ['APP_INFO'])
    appnames = map(lambda x: x['name'], app_info['apps'])

    if result.token_file:
        with open(result.token_file) as tf:
            result.token = tf.read().strip()

    kube = KubernetesInterface(cfg_file=result.cfg,
                               token=result.token,
                               server=result.server,
                               insecure=result.insecure,
                               ca=result.ca,
                               netskaler=netskaler,
                               app_info=appinfo)
    for app in appnames:
        endpoints = kube.get_backends_for_app(app)
        logger.info("Endpoints for app " + app + ": " + str(endpoints))
    kube.watch_all_apps()


def cfg_file_driver(netskaler, cfg_file):

    # '{"appkey": "com.citrix.lb.appname", "apps": [{"name": "foo"},
    #  {"name": "bar"}]}'
    app_info = json.loads(os.environ['APP_INFO'])
    appnames = map(lambda x: x['name'], app_info['apps'])

    cfg_file_driver = ConfigFileDriver(netskaler=netskaler,
                                       filename=cfg_file)
    for app in appnames:
        cfg_file_driver.configure_ns_for_app(app)

if __name__ == "__main__":
    if re.match('^[a-zA-Z0-9+/=]+$', os.environ['APP_INFO']):
        os.environ['APP_INFO'] = base64.b64decode(os.environ['APP_INFO'])

    # '{"appkey": "com.citrix.lb.appname", "apps": [{"name": "foo"},
    #  {"name": "bar"}]}'
    app_info = json.loads(os.environ['APP_INFO'])
    netskaler = NetscalerInterface(os.environ.get("NS_IP"),
                                   os.environ.get("NS_USER"),
                                   os.environ.get("NS_PASSWORD"),
                                   app_info,
                                   os.environ.get("NS_CONFIG_FRONT_END"))

    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--swarm-url", dest='swarm_url')
    group.add_argument("--marathon-url", dest='marathon_url')
    group.add_argument("--kube-config", dest='kube_config')
    group.add_argument("--kube-apiserver", dest='kube_server')
    group.add_argument("--cfg-file", dest='cfg_file')
    result = parser.parse_known_args()

    if result[0].swarm_url:
        docker_swarm(app_info, netskaler)
    elif result[0].marathon_url:
        mesos_marathon(app_info, netskaler)
    elif result[0].kube_config or result[0].kube_server:
        kubernetes(app_info, netskaler)
    elif result[0].cfg_file:
        cfg_file_driver(netskaler, result[0].cfg_file)
