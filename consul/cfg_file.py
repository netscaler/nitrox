import argparse
import os
import json
import logging


logger = logging.getLogger('docker_netscaler')


class ConfigFileDriver(object):
    """Uses a config file to drive Nitro APIs"""

    def __init__(self, netskaler, filename):
        """Constructor

        :param str filename: config filename
        """
        self.netskaler = netskaler
        self.filename = filename
        self.cfg_json = json.load(open(self.filename))

    def get_backends_for_app(self, appid):
        """Get host endpoints for apps

        :returns: endpoints dict
        :rtype: dict
        """
        for svc in self.cfg_json:
            if svc["servicename"] == appid:
                return [(b['host'], b['port'])
                        for b in svc['backends']]
        return []

    def configure_ns_for_app(self, appname):
        backends = self.get_backends_for_app(appname)
        logger.debug("Backends for %s are %s" % (appname, str(backends)))
        self.netskaler.configure_app(appname, backends)

    def configure_ns_for_all_apps(self):
        appnames = map(lambda x: x['name'], self.app_info['apps'])
        for app in appnames:
            self.configure_ns_for_app(app)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process Cfg File args')
    parser.add_argument("--cfg-file", required=True, dest='cfg_file')

    result = parser.parse_args()

    # '{"appkey": "com.citrix.lb.appname", "apps": [{"name": "foo"},
    #  {"name": "bar"}]}'
    app_info = json.loads(os.environ['APP_INFO'])
    appnames = map(lambda x: x['name'], app_info['apps'])

    cfg_file_driver = ConfigFileDriver(None, result.cfg_file)
    for app in appnames:
        endpoints = cfg_file_driver.get_backends_for_app(app)
        logger.info("Endpoints for app " + app + ": " + str(endpoints))
        print("Endpoints for app " + app + ": " + str(endpoints))
