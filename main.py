#!/usr/bin/env python

import argparse
import getopt
import logging
import os
import sys
import json
sys.path.append(os.getcwd())
from docker_swarm import DockerSwarmInterface
from netscaler import NetscalerInterface

handler = logging.StreamHandler(sys.stderr)
#handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s  - %(levelname)s - [%(filename)s:%(funcName)-10s] (%(threadName)s) %(message)s',)
handler.setFormatter(formatter)
logger = logging.getLogger('docker_netscaler')
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

if __name__ == "__main__":
    swarm_url = "unix:///var/run/docker.sock"
    swarm_tls_ca_cert = ""
    swarm_tls_cert = ""
    swarm_tls_key = ""
    swarm_allow_insecure = False

    parser = argparse.ArgumentParser(description='Process Docker client args')
    parser.add_argument("--swarm-url", required=True, dest='swarm_url')
    parser.add_argument("--swarm-tls-ca-cert", required=False,
                        dest='swarm_tls_ca_cert')
    parser.add_argument("--swarm-tls-cert", required=False,
                        dest='swarm_tls_cert')
    parser.add_argument("--swarm-tls-key", required=False,
                        dest='swarm_tls_key')
    parser.add_argument("--swarm-allow-insecure", required=False,
                        dest='swarm_allow_insecure')

    result = parser.parse_args()

    # '{"appkey": "com.citrix.lb.appname", "apps": [{"name": "foo"},
    #  {"name": "bar"}]}'
    app_info = json.loads(os.environ['APP_INFO'])
    netskaler = NetscalerInterface(os.environ.get("NS_IP"),
                                   os.environ.get("NS_USER"),
                                   os.environ.get("NS_PASSWORD"),
                                   app_info)
    dokker = DockerSwarmInterface(result.swarm_url, result.swarm_tls_ca_cert,
                                  result.swarm_tls_cert, result.swarm_tls_key,
                                  swarm_allow_insecure, app_info, netskaler)
    dokker.configure_all()
