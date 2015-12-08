import argparse
import os
import json
import logging
import requests
import requests.exceptions


logger = logging.getLogger('docker_netscaler')


class MarathonInterface(object):
    """Interface for the Marathon REST API."""

    def __init__(self, server, username=None, password=None, timeout=10000):
        """Constructor

        :param server: Marathon URL (e.g., 'http://host:8080' )
        :param str username: Basic auth username
        :param str password: Basic auth password
        :param int timeout: Timeout (in seconds) for requests to Marathon
        """
        self.server = server
        self.auth = (username, password) if username and password else None
        self.timeout = timeout

    def get_app_endpoints(self, appid):
        """Get host endpoints for apps

        :returns: endpoints dict
        :rtype: dict
        """
        response = None
        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json'}
        url = self.server + 'v2/apps' + appid
        try:
            response = requests.request('GET', url,
                                        headers=headers,
                                        auth=self.auth)
        except requests.exceptions.RequestException as e:
            logger.error('Error while calling %s: %s', url, e.message)
        if response.status_code >= 500:
            logger.error('Got HTTP {code}: {body}'.
                         format(code=response.status_code, body=response.text))
            raise RuntimeError(response)
        elif response.status_code >= 400:
            logger.error('Got HTTP {code}: {body}'.
                         format(code=response.status_code, body=response.text))
            if response.status_code == 404:
                raise RuntimeError(response)
            else:
                raise RuntimeError(response)
        elif response.status_code >= 300:
            logger.warn('Got HTTP {code}: {body}'.
                        format(code=response.status_code, body=response.text))
        else:
            logger.debug('Got HTTP {code}: {body}'.
                         format(code=response.status_code, body=response.text))
        return [(t['host'], t['ports'])
                for t in response.json()['app']['tasks']]

    def events(self):
        """Get event stream
           See:
           https://mesosphere.github.io/marathon/docs/rest-api.html#event-stream
        """
        path = 'v2/events'
        url = self.server + path
        headers = {'Content-Type': 'application/json',
                   'Accept': 'text/event-stream'}
        r = requests.get(url,
                         auth=self.auth,
                         headers=headers,
                         stream=True)
        for line in r.iter_lines():
            if line and line.find("data:") > -1:
                event = json.loads(line[line.find("data:") +
                                        len('data: '):].rstrip())
                if event['eventType'] == 'status_update_event':
                    yield event['appId']
            yield None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process Marathon args')
    parser.add_argument("--marathon-url", required=True, dest='marathon_url')

    result = parser.parse_args()

    # '{"appkey": "com.citrix.lb.appname", "apps": [{"name": "foo"},
    #  {"name": "bar"}]}'
    app_info = json.loads(os.environ['APP_INFO'])
    appnames = map(lambda x: x['name'], app_info['apps'])

    marathon = MarathonInterface(result.marathon_url)
    for app in appnames:
        endpoints = marathon.get_app_endpoints("/" + app)
        logger.info("Endpoints for app " + app + ": " + str(endpoints))

    for e in marathon.events():
        if e is not None and e in appnames:
            endpoints = marathon.get_app_endpoints(e)
            logger.info("Endpoints for app " + e + ": " + str(endpoints))
