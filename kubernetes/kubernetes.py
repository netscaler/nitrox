import argparse
import os
import json
import logging
import requests
import requests.exceptions
from pykube.config import KubeConfig
from pykube.http import HTTPClient


logger = logging.getLogger('docker_netscaler')


class KubernetesInterface(object):
    """Interface for the Kubernetes REST API."""

    def __init__(self, cfg_file, netskaler, app_info):
        """Constructor

        :param server: Kubernetes URL (e.g., 'http://api-server:8080' )
        :param str cfg_file: location of kubectl config (e.g., ~/.kube/config)
        :param NetscalerInterface netskaler: Netscaler object
        :param app_info : dictionary of app names
        """
        self.cfg_file = cfg_file
        self.netskaler = netskaler
        self.app_info = app_info
        self.config = KubeConfig(cfg_file)
        self.client = HTTPClient(config=self.config)

    def get_services(self):
        api = '/services/'
        try:
            # TODO:support other namespace
            response = self.client.get(url=api,
                                       namespace='default',
                                       verify=False)  # FIXME: always verify
        except requests.exceptions.RequestException as e:
            logger.error('Error while calling  %s:%s', api, e.message)
            return []
        if response.status_code >= 300:
            logger.error('Got HTTP {code}: {body}'.
                         format(code=response.status_code, body=response.text))
            return endpoints
        svc_list = response.json()
        nodePorts = [{item['metadata']['name']:
                     [port['nodePort'] for port in item['spec']['ports']]}
                     for item in svc_list['items']
                     if item['spec']['type'] == 'NodePort']
        # nodePorts.keys() has names of services that have NodePort
        return nodePorts

    def get_backends_for_app(self, appid):
        """Get host endpoints for apps (services)

        :returns: endpoints dict
        :rtype: dict
        """
        endpoints = []
        response = None
        api = '/services/' + appid
        try:
            # TODO:support other namespace
            response = self.client.get(url=api,
                                       namespace='default',
                                       verify=False)  # FIXME: always verify
        except requests.exceptions.RequestException as e:
            logger.error('Error while calling  %s:%s', api, e.message)
            return []
        if response.status_code >= 300:
            status = response.json()
            if status['reason'] == 'NotFound':
                logger.info("Service %s not found" % appid)
            else:
                logger.error('Got HTTP {code}: {body}'.
                             format(code=response.status_code,
                                    body=response.text))
            return endpoints
        svc = response.json()
        # node port is the backend port we need. Handle only 1 port for now
        nodePort = svc['spec']['ports'][0]['nodePort']  # TODO
        if nodePort == 0:
            logger.warn("Service %s does not have a node port" % appid)
            return endpoints
        # find the selectors so that we can find its pods
        selector = svc['spec']['selector']
        if not selector:
            logger.error("Found zero selectors for service %s", appid)
            return endpoints

        # construct label selector
        labelString = ""
        for k, v in selector.iteritems():
            labelString = labelString + "%s=%s," % (k, v)

        pods = None
        api = '/pods?labelSelector=' + labelString.rstrip(",")
        try:
            pods = self.client.get(url=api,
                                   namespace='default',  # FIXME
                                   verify=False)  # FIXME: verify
        except requests.exceptions.RequestException as e:
            logger.error('Error while calling  %s:%s', api, e.message)
            return endpoints
        if pods.status_code == 200:
            pods = pods.json()
            for pd in pods['items']:
                if pd['status']['phase'] == 'Running':
                    endpoints.append((pd['status']['hostIP'], nodePort))
        return list(set(endpoints))

    def events(self):
        """Get event stream
        """
        pass

    def watch_all_apps(self):
        pass

    def configure_ns_for_app(self, appname):
        backends = self.get_backends_for_app(appname)
        logger.debug("Backends for %s are %s" % (appname, str(backends)))
        self.netskaler.configure_app(appname,  backends)

    def configure_ns_for_all_apps(self):
        appnames = map(lambda x:  x['name'], self.app_info['apps'])
        for app in appnames:
            self.configure_ns_for_app(app)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description='Process Kubernetes args')
    parser.add_argument("--config", required=True, dest='cfg')

    result = parser.parse_args()

    # '{"appkey": "com.citrix.lb.appname", "apps": [{"name": "foo"},
    #  {"name": "bar"}]}'
    app_info = json.loads(os.environ['APP_INFO'])
    appnames = map(lambda x: x['name'], app_info['apps'])

    kube = KubernetesInterface(result.cfg, netskaler=None, app_info=app_info)
    for app in appnames:
        endpoints = kube.get_backends_for_app(app)
        logger.info("Endpoints for app " + app + ": " + str(endpoints))

    """
    for e in kube.events():
        if e is not None and e in appnames:
            endpoints = kube.get_app_endpoints(e)
            logger.info("Endpoints for app " + e + ": " + str(endpoints))
    """
