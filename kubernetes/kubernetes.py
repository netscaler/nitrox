import argparse
import os
import json
import logging
import requests
import requests.exceptions
from client import K8sClient
# from pykube.config import KubeConfig
# from pykube.http import HTTPClient


logger = logging.getLogger('docker_netscaler')


class KubernetesInterface(object):
    """Interface for the Kubernetes REST API."""

    def __init__(self, netskaler, app_info,
                 cfg_file=None, token=None, ca=None,
                 server=None, insecure=False):
        """Constructor

        :param str cfg_file: location of kubectl config (e.g., ~/.kube/config)
        :param NetscalerInterface netskaler: Netscaler object
        :param app_info : dictionary of app names
        :param token: Auth (bearer) token
        :param server: Kubernetes URL (e.g., 'http://api-server:8080' )
        :param ca: certificate authority of kube api server
        :param insecure: whether to ignore certificate host mismatch
        """
        self.cfg_file = cfg_file
        self.netskaler = netskaler
        self.app_info = app_info
        self.insecure_tls_skip_verify = insecure
        self.client = K8sClient(cfg_file=cfg_file,
                                url=server,
                                token=token,
                                ca=ca,
                                insecure_skip_tls_verify=insecure)

    def _get(self, api, namespace='default'):
        response = None
        success = True
        try:
            # TODO:support other namespace
            response = self.client.get(url=api,
                                       namespace=namespace)
        except requests.exceptions.RequestException as e:
            logger.error('Error while calling  %s:%s', api, e.message)
            success = False  # TODO: throw exception
        if success and response.status_code >= 300:
            logger.error('Got HTTP {code}: {body}'.
                         format(code=response.status_code, body=response.text))
            success = False
        return success, response

    def get_node_ports(self):
        success, response = self._get('/services')
        if not success:
            return []
        svc_list = response.json()
        nodePorts = [{item['metadata']['name']:
                     [port['nodePort'] for port in item['spec']['ports']]}
                     for item in svc_list['items']
                     if item['spec']['type'] == 'NodePort']
        # nodePorts.keys() has names of services that have NodePort
        return nodePorts

    def get_backends_for_app(self, appid):
        """Get host endpoints for apps (services)

        :returns: list of endpoint (hostIp, port) tuples
        :rtype: list
        """
        backends = []
        api = '/services/' + appid
        success, response = self._get(api)
        if not success and response and response.status_code >= 300:
            status = response.json()
            if status['reason'] == 'NotFound':
                logger.info("Service %s not found" % appid)
        if not success:
            return backends
        svc = response.json()
        # node port is the backend port we need. Handle only 1 port for now
        nodePort = svc['spec']['ports'][0]['nodePort']  # TODO
        if nodePort == 0:
            logger.warn("Service %s does not have a node port" % appid)
            return backends
        # find the endpoint for the service so that we can find its pods
        api = '/endpoints'
        success, endpoints = self._get(api)
        if not success:
            return backends
        podnames = []
        if endpoints.status_code == 200:
            endpoints = endpoints.json()
            for ep in endpoints['items']:
                if ep['metadata']['name'] == appid:
                    if ep['subsets']:
                        podnames = [addr['targetRef']['name']
                                    for addr in ep['subsets'][0]['addresses']]
                    break
        for p in podnames:
            api = '/pods/' + p
            success, response = self._get(api)
            if not success:
                continue
            pod = response.json()
            status = pod['status']['phase']
            host = pod['status']['hostIP']
            if status == 'Running':
                backends.append((host, nodePort))
        return list(set(backends))

    def events(self, resource_version):
        """Get event stream for k8s endpoints
        """
        url = self.client.url +\
            "/v1/watch/namespaces/default/endpoints?" +\
            "resourceVersion=%s&watch=true" % resource_version
        evts = self.client.session.request('GET', url,
                                           stream=True)
        # TODO re-start the loop when disconnected from api server
        for e in evts.iter_lines():
            event_json = json.loads(e)
            yield event_json

    def watch_all_apps(self):
        appnames = map(lambda x:  x['name'], self.app_info['apps'])
        api = '/endpoints'
        success, response = self._get(api)
        if not success:
            logger.error("Failed to watch for endpoint changes, exiting")
            return
        endpoints = response.json()
        resource_version = endpoints['metadata']['resourceVersion']
        for e in self.events(resource_version):
            service_name = e['object']['metadata']['name']
            if service_name in appnames:
                self.configure_ns_for_app(service_name)

    def configure_ns_for_app(self, appname):
        backends = self.get_backends_for_app(appname)
        logger.info("Backends for %s are %s" % (appname, str(backends)))
        self.netskaler.configure_app(appname,  backends)

    def configure_ns_for_all_apps(self):
        appnames = map(lambda x:  x['name'], self.app_info['apps'])
        for app in appnames:
            self.configure_ns_for_app(app)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description='Process Kubernetes args')
    parser.add_argument("--kubeconfig", required=False, dest='cfg')
    parser.add_argument("--token", required=False, dest='token')
    parser.add_argument("--server", required=False, dest='server')
    parser.add_argument("--insecure-tls-verify", required=False,
                        dest='insecure')

    result = parser.parse_args()

    # '{"appkey": "com.citrix.lb.appname", "apps": [{"name": "foo"},
    #  {"name": "bar"}]}'
    app_info = json.loads(os.environ['APP_INFO'])
    appnames = map(lambda x: x['name'], app_info['apps'])

    kube = KubernetesInterface(netskaler=None, app_info=app_info,
                               cfg_file=result.cfg, insecure=True)
    for app in appnames:
        endpoints = kube.get_backends_for_app(app)
        logger.info("Endpoints for app " + app + ": " + str(endpoints))
    kube.watch_all_apps()
