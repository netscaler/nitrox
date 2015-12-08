#!/usr/bin/env python

import argparse
import logging
import os
import sys
import json
sys.path.append(os.getcwd())
from docker_swarm import DockerSwarmInterface
from mesos_marathon import MarathonInterface
from netscaler import NetscalerInterface

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
    parser.add_argument("--marathon-user",  dest='marathon_user')
    parser.add_argument("--marathon-password",  dest='marathon_password')
    result = parser.parse_args()
    marathon = MarathonInterface(server=result.marathon_url,
                                 netskaler=netskaler,
                                 app_info=app_info,
                                 username=result.marathon_user,
                                 password=result.marathon_password)

    marathon.configure_ns_for_all_apps()
    marathon.watch_all_apps()

if __name__ == "__main__":

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
    result = parser.parse_known_args()

    if result[0].swarm_url:
        docker_swarm(app_info, netskaler)
    elif result[0].marathon_url:
        mesos_marathon(app_info, netskaler)
