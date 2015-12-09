# Nitrox for Docker Swarm
You can run Nitrox as a container or as a regular python script.

# Usage
## Pre-requisites
1. Docker Swarm Cluster. Instructions assume you are running on the Swarm Manager/Master
2. Netscaler pre-requisites are [here](https://github.com/chiradeep/nitrox/blob/master/README.swarm.md)
3. An `appkey` that will be used to label the containers that comprise the apps/microservices. For example, `com.citrix.lb.appname`

## As a container
### Launch the 'nitrox' container 
The code has been containerized into `chiradeeptest/nitrox` . Use this container from the swarm master:

````
[root@swarm-master ~]# eval "$(docker-machine env --swarm swarm-master)"
[root@swarm-master ~]# docker run \
           -e NS_IP=$NS_IP \
           -e NS_USER=$NS_USER \
           -e NS_PASSWORD=$NS_PASSWORD \
           -e APP_INFO='{"appkey": "com.citrix.lb.appname", "apps": [{"name": "AccountService"}, {"name": "ProductCatalog"}, {"name":"ShoppingCart"}, {"name":"OrderServer"}]}' \
           -d \
           -v /etc/docker:/etc/docker \
           --name nitrox \
           chiradeeptest/nitrox \
           --swarm-url=$DOCKER_HOST \
           --swarm-tls-ca-cert=/etc/docker/ca.pem \
           --swarm-tls-cert=/etc/docker/server.pem \
           --swarm-tls-key=/etc/docker/server-key.pem
````
Monitor the logs of the containers with `docker logs nitrox`

### Test
Run some containers and see your netscaler get reconfigured 

````
for i in 0 1 2 3 4 
do
	   docker run -d -l com.citrix.lb.appname=AccountService --name AccountService$i -p 800$i:80 nginx
done
````
Kill a few container instances:

````
docker stop AccountService0
docker start AccountService0
````
Logs:

````
2015-12-01 00:55:37,045  - DEBUG - [docker_swarm.py:watch_app ]  (Thread-1) Event status: die, id: 97df5d1fa1d0 2015-12-01 00:55:37,048  - INFO - [docker_swarm.py:watch_app ]  (Thread-1) Configuring NS for app AccountService,container id=97df5d1fa1d0
2015-12-01 00:55:37,048  - INFO - [docker_swarm.py:get_backends_for_app]  (Thread-1) Getting backends for app label com.citrix.lb.appname=AccountService
2015-12-01 00:55:37,051  - DEBUG - [docker_swarm.py:configure_ns_for_app]  (Thread-1) Backends are [(u'10.71.137.30', 8004), (u'10.71.137.7', 8003), (u'10.71.137.38', 8002), (u'10.71.137.30', 8001)]
2015-12-01 00:55:37,129  - INFO - [netscaler.py:_create_service_group]  (Thread-1) Service group AccountService already configured 
2015-12-01 00:55:37,182  - INFO - [netscaler.py:_bind_service_group_lb]  (Thread-1) LB AccountService is already bound to service group AccountService
2015-12-01 00:55:37,240  - INFO - [netscaler.py:_configure_services]  (Thread-1) Unbinding 10.71.137.38:8000 from service group AccountService
2015-12-01 00:55:37,279  - INFO - [netscaler.py:_configure_services]  (Thread-1) 10.71.137.30:8002 is already bound to  service group AccountService
2015-12-01 00:55:37,279  - INFO - [netscaler.py:_configure_services]  (Thread-1) 10.71.137.38:8001 is already bound to  service group AccountService
2015-12-01 00:55:37,279  - INFO - [netscaler.py:_configure_services]  (Thread-1) 10.71.137.7:8004 is already bound to  service group AccountService
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

Run the code while pointing it to the Docker Swarm environment. (This assumes you are running on the Docker Swarm manager)

```
eval "$(docker-machine env --swarm swarm-master)"
python main.py  --swarm-url=$DOCKER_HOST --swarm-tls-ca-cert=$DOCKER_CERT_PATH/ca.pem --swarm-tls-cert=$DOCKER_CERT_PATH/cert.pem --swarm-tls-key=$DOCKER_CERT_PATH/key.pem
```

Containers instances for each app backend have to be started with a label of the form label=app_key=app_name. For instance

````
for i in 0 1 2 3 4 5
do
   docker run -d -l com.citrix.lb.appname=foo --name www$i -p 80$i:80 nginx
done
````

Try changing the state of a few containers:

````
docker stop www0 
docker start www0
````
The Netscaler will get reconfigured by removing the container from the load balancer service group (docker stop) or with the new location/port of the container (docker run).
