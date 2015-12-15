"""
K8s client. Deal with auth messiness
"""
import requests
import yaml
import posixpath


class K8sConfig(object):
    """
    Init from kubectl config
    """

    def __init__(self, filename):
        """
        Constructor

        :Parameters:
           - `filename`: The full path to the configuration file
        """
        self.filename = filename
        self.doc = None

    def parse(self):
        """
        Parses the configuration file.
        """
        with open(self.filename) as f:
            self.doc = yaml.safe_load(f.read())
        if "current-context" in self.doc and self.doc["current-context"]:
            current_context = filter(lambda x:
                                     x['name'] == self.doc['current-context'],
                                     self.doc['contexts'])[0]['context']
            username = current_context['user']
            clustername = current_context['cluster']
            self.user = filter(lambda x: x['name'] == username,
                               self.doc['users'])[0]['user']
            self.cluster = filter(lambda x: x['name'] == clustername,
                                  self.doc['clusters'])[0]['cluster']


class K8sClient(object):
    """
    Client for interfacing with the Kubernetes API.
    """

    def __init__(self, cfg_file, url=None, token=None, ca=None,
                 insecure_skip_tls_verify=False, version="/v1"):
        """
        Creates a new instance of the HTTPClient.

        :Parameters:
           - `cfg_file`: Kubectl config file (useful for testing)
           - `token`: Useful for service account
           - `version`: The version of the API to use
        """
        self.url = url
        self.token = token
        self.insecure_skip_tls_verify = insecure_skip_tls_verify
        self.ca = ca
        if cfg_file:
            self.config = K8sConfig(cfg_file)
            self.config.parse()
            self.url = self.config.cluster["server"]
            self.token = self.config.user["token"]
            if "certificate-authority" in self.config.cluster:
                self.ca = self.config.cluster["certificate-authority"]
            elif self.config.cluster.get('insecure-skip-tls-verify'):
                self.insecure_skip_tls_verify = True
            # TODO handle client cert
        self.version = version
        self.session = self.build_session()

    def build_session(self):
        """
        Creates a new session for the client.
        """
        s = requests.Session()
        if self.ca:
            s.verify = self.ca
        elif self.insecure_skip_tls_verify:
            s.verify = False
        s.headers["Authorization"] = "Bearer {}".format(self.token)
        # TODO: handle client cert
        return s

    def get_kwargs(self, **kwargs):
        """
        Creates a full URL to request based on arguments.

        :Parametes:
           - `kwargs`: All keyword arguments to build a kubernetes API endpoint
        """
        bits = [
            self.version,
        ]
        if "namespace" in kwargs:
            bits.extend([
                "namespaces",
                kwargs.pop("namespace"),
            ])
        url = kwargs.get("url", "")
        if url.startswith("/"):
            url = url[1:]
        bits.append(url)
        kwargs["url"] = self.url + posixpath.join(*bits)
        return kwargs

    def request(self, *args, **kwargs):
        """
        Makes an API request based on arguments.

        :Parameters:
           - `args`: Non-keyword arguments
           - `kwargs`: Keyword arguments
        """
        return self.session.request(*args, **self.get_kwargs(**kwargs))

    def get(self, *args, **kwargs):
        """
        Executes an HTTP GET.

        :Parameters:
           - `args`: Non-keyword arguments
           - `kwargs`: Keyword arguments
        """
        return self.session.get(*args, **self.get_kwargs(**kwargs))
