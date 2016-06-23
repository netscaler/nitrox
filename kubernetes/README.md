# Nitrox for Kubernetes
You can run Nitrox as a container or as a regular python script.

# Theory of Operation
Exposing a replicated service to [external access](https://github.com/kubernetes/kubernetes/blob/master/docs/user-guide/accessing-the-cluster.md) in Kubernetes can be done with a supported `LoadBalancer` or `NodePort`. In the case of `NodePort` a (random) port is chosen and this port is exposed on every host (node) in the cluster. `nitrox` listens for changes in the replication controller for an app and figures out the hosts(nodes) the pods belonging to the replication controller run on. The list of [(nodeIP:nodePort)] for each pod is configured on the NetScaler.

Note that this is rather inefficient: traffic sent to each NodePort is itself load balanced by `KubeProxy` to the destination Pods. So, NetScaler configuration such as `lbMethod` and `persistence` may be redundant / incompatible.

# Usage
## Pre-requisites
1. Kubernetes cluster, at least v1.1
2. Kubernetes [service accounts](https://github.com/kubernetes/kubernetes/blob/master/docs/admin/service-accounts-admin.md)  feature, enabled as described in [k8s.md](k8s.md)
3. NetScaler pre-requisites are [here](../README.md)

## As a container
### Launch the 'nitrox' container 
The code has been containerized into `chiradeeptest/nitrox` . You can run it as a Kubernetes service, or simply on any docker engine

#### Plain old docker-engine (e.g., your laptop)
Assuming your certificate authority cert in $HOME/.kube/config :

````
[root@localhost ~]# 
[root@localhost ~]# docker run \
           -e NS_IP=$NS_IP \
           -e NS_USER=$NS_USER \
           -e NS_PASSWORD=$NS_PASSWORD \
           -e APP_INFO='{"apps": [{"name": "frontend"}]}' \
           -d \
           --name nitrox \
           chiradeeptest/nitrox \
           -v $HOME/.kube:/kube \
           --kube-token='ABCDEFGHIJKLMNOPQRSTUVWXYZ'\
           --kube-certificate-file=/kube/ca.crt
````
Monitor the logs of the containers with `docker logs nitrox`. Note that you can use the `--insecure-skip-tls-verify` flag instead of `--kube-certifcate-file` if you do not have access to the file.

#### As a Kubernetes Pod
The nitrox container can be scheduled using the Kubernetes APIs:

````
kubectl create -f nitrox-rc.yaml
kubectl get rc nitrox
````
You can find nitrox-rc.yaml [here](https://github.com/chiradeep/nitrox/blob/master/kubernetes/nitrox-rc.yaml)
Edit the environment variables in the file before launching.

### Test
Run some services using Kubernetes. For an example, see the [Guestbook](https://github.com/kubernetes/kubernetes/tree/master/examples/guestbook) . The example is ideal since it has a service ('frontend') that needs to be enabled for external access/load balancing. Edit the 'all-in-one' spec so that the spec for `Service` frontend has `type` `NodePort` 

````
@@ -129,6 +129,7 @@ spec:
   ports:
     # the port that this service should serve on
   - port: 80
+  type: NodePort
   selector:
     app: guestbook
     tier: frontend
````

Create the [guestbook service](https://github.com/kubernetes/kubernetes/tree/master/examples/guestbook):


````
 kubectl create -f examples/guestbook/all-in-one/guestbook-all-in-one.yaml
````

Now, scale the service up and down to see the NetScaler being reconfigured:

````
kubectl scale --replicas=2 rc/frontend
````
Logs:

````
2015-12-11 13:50:11,975  - INFO - [netscaler.py:_configure_services]  (MainThread) Unbinding 10.220.135.41:30734 from service group frontend 
2015-12-11 13:50:12,035  - INFO - [netscaler.py:_configure_services]  (MainThread) 10.220.135.39:30734 is already bound to  service group frontend
2015-12-11 13:50:12,035  - INFO - [netscaler.py:_configure_services]  (MainThread) 10.220.135.43:30734 is already bound to  service group frontend
````

#### Addenda
If you have the [DNS add-on](https://github.com/kubernetes/kubernetes/tree/master/cluster/addons/dns) then you won't need to edit the the guestbook spec. Also you can change `nitrox-rc.yaml` to use DNS and use the certificate file in `/var/run/secrets/kubernetes.io/ca.crt` instead of `insecure-skip-tls-verify`. In this case, the API server URL would be `https://kubernetes/api`


## For developers / hackers

Download and install the Citrix NetScaler SDK for Python:

```
wget http://downloadns.citrix.com.edgesuite.net/10902/ns-11.0-65.31-sdk.tar.gz
tar xzf ns-11.0-65.31-sdk.tar.gz
tar xzvf ns-11.0-65.31-nitro-python.tgz 
cd nitro-python-1.0/
sudo python setup.py install
```
Install the docker python client & YAML support

````
sudo pip install docker-py
sudo pip install pyyaml
````

Get the code:

```
git clone https://github.com/chiradeep/nitrox.git
cd nitrox
```

Run the code while pointing it to the Kubernetes environment. 

```
python main.py  --kubernetes-apiserver=https://kubernetes-master:6443/  --kube-token='ABCDEFGHIJKLMNOPQRSTUVWXYZ' --kube-certificate-file=~/.kube/ca.crt

or

python main.py --kube-config=~/.kube/config
```

Create the [guestbook service](https://github.com/kubernetes/kubernetes/tree/master/examples/guestbook):

````
 kubectl create -f examples/guestbook/all-in-one/guestbook-all-in-one.yaml
````

Now, scale the service up and down to see the NetScaler being reconfigured:

````
kubectl scale --replicas=2 rc/frontend
````

