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
        if self.doc is not None:
            return
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

    def __init__(self, cfg_file, url=None, token=None, insecure=False, version="v1"):
        """
        Creates a new instance of the HTTPClient.

        :Parameters:
           - `cfg_file`: Kubectl config file (useful for testing)
           - `token`: Useful for service account
           - `version`: The version of the API to use
        """
        self.url = url
        self.token = token
        self.insecure_tls_verify = insecure
        if cfg_file:
            self.config = K8sConfig(cfg_file)
            self.config.parse()
            print self.config.cluster
            self.url = self.config.cluster["server"]
        self.version = version
        self.session = self.build_session()

    def build_session(self):
        """
        Creates a new session for the client.
        """
        s = requests.Session()
        if "certificate-authority" in self.config.cluster:
            s.verify = self.config.cluster["certificate-authority"].filename()
        if "token" in self.config.user and self.config.user["token"]:
            s.headers["Authorization"] = \
                "Bearer {}".format(self.config.user["token"])
        else:
            s.cert = (
                self.config.user["client-certificate"].filename(),
                self.config.user["client-key"].filename(),
            )
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
