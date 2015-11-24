# Nitrox
Configure Citrix Netscaler loadbalancing for container platforms such as Docker Swarm. Currently only Docker Swarm is supported.

# Theory of Operation
1. Containers that form a load-balanced backend for an app are labeled with the same label 
2. Information from the docker API for the labeled containers are used to configure a Netscaler loadbalancer.

# Usage

Download and install the Citrix Netscaler SDK for Python:
```
wget http://downloadns.citrix.com.edgesuite.net/10902/ns-10.5-58.11-sdk.tar.gz
tar xzf ns-10.5-58.11-sdk.tar.gz
cd ns-10.5-58.11-sdk/
tar xzf ns-10.5-58.11-nitro-python.tgz
cd nitro-python-1.0/
sudo python setup.py
```

Get the code:
```
git clone <>
cd nitrox
```
To run the code, you need to point it to a Docker swarm location. Also, you need to pass in the Netscaler credentials.

Location and credentials for the Netscaler are specified in the environment.
````
export NS_IP=10.220.73.33
export NS_USER=nsroot
export NS_PASSWORD=3df8jha@k0
````

Application information is also passed in via environment variable:
```
export APP_INFO='{"appkey": "com.citrix.lb.appname", "apps": [{"name": "foo0", "lb_ip":"10.220.73.122", "lb_port":"443"}, {"name": "foo1", "lb_ip":"10.220.73.123", "lb_port":"80"}, {"name":"foo2"}, {"name":"foo3"}]}'
```

Run the code while pointing it to the Docker Swarm environment. (This assumes you are running on the Docker Swarm controller)

```
python main.py  --swarm-url=$DOCKER_HOST --swarm-tls-ca-cert=$DOCKER_CERT_PATH/ca.pem --swarm-tls-cert=$DOCKER_CERT_PATH/cert.pem --swarm-tls-key=$DOCKER_CERT_PATH/key.pem
```

Containers instances for each app backend have to be started with a label of the form label=<app_key>=<app_name> .

````
for i in 0 1 2 3 4 5
do
   docker run -d -l com.citrix.lb.appname=foo --name www$i -p 80$i:80 nginx
done
````

Try changing the state of a few containers:
```
docker stop www0
docker start www0
```
The Netscaler will get reconfigured by removing the container from the load balancer service group (docker stop) or with the new location/port of the container (docker run).


