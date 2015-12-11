# Nitrox for Kubernetes
You can run Nitrox as a container or as a regular python script.

# Usage
## Pre-requisites
1. Kubernetes cluster, at least v1.1
2. Netscaler pre-requisites are [here](https://github.com/chiradeep/nitrox/blob/master/README.md)

## As a container
### Launch the 'nitrox' container 
The code has been containerized into `chiradeeptest/nitrox` . You can run it as a Kubernetes service, or simply on any docker engine

#### Plain old docker-engine (e.g., your laptop)
````
[root@localhost ~]# 
[root@localhost ~]# docker run \
           -e NS_IP=$NS_IP \
           -e NS_USER=$NS_USER \
           -e NS_PASSWORD=$NS_PASSWORD \
           -e APP_INFO='{"apps": [{"name": "AccountService"}, {"name": "ProductCatalog"}, {"name":"ShoppingCart"}, {"name":"OrderServer"}]}' \
           -d \
           --name nitrox \
           chiradeeptest/nitrox \
           --kube-config=$HOME/.kube/config
````
Monitor the logs of the containers with `docker logs nitrox`

#### As a Kubernetes service
The nitrox container can be scheduled using the Kubernetes APIs:

````
kubectl create -f service-nitrox.yaml
````
You can find service-nitrox [here](https://github.com/chiradeep/nitrox/blob/master/kubernetes/service-nitrox.yaml)

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

Create the guestbook service:


````
 kubectl create -f examples/guestbook/all-in-one/guestbook-all-in-one.yaml
````

Now, scale the service up and down to see the Netscaler being reconfigured:

````
kubectl scale --replicas=2 rc/frontend
````
Logs:

````
2015-12-11 13:50:11,975  - INFO - [netscaler.py:_configure_services]  (MainThread) Unbinding 10.220.135.41:30734 from service group frontend 
2015-12-11 13:50:12,035  - INFO - [netscaler.py:_configure_services]  (MainThread) 10.220.135.39:30734 is already bound to  service group frontend
2015-12-11 13:50:12,035  - INFO - [netscaler.py:_configure_services]  (MainThread) 10.220.135.43:30734 is already bound to  service group frontend
````


## For developers / hackers

Download and install the Citrix Netscaler SDK for Python:

```
wget http://downloadns.citrix.com.edgesuite.net/10902/ns-10.5-58.11-sdk.tar.gz
tar xzf ns-10.5-58.11-sdk.tar.gz
tar xzvf ns-10.5-58.11-nitro-python.tgz 
cd nitro-python-1.0/
sudo python setup.py install
```
Install the docker python client

````
sudo pip install docker-py
````

Get the code:

```
git clone https://github.com/chiradeep/nitrox.git
cd nitrox
```

Run the code while pointing it to the Kubernetes environment. 

```
python main.py  --kubernetes-url=http://kubernetes-master:8080/ 
```

Test by launching containerized apps using the Kubernetes API and scaling them up/down using the GUI.

