# Nitrox for Marathon
You can run Nitrox as a container or as a regular python script.

# Usage
## Pre-requisites
1. Marathon framework (at least v0.9) running on Mesos.  
2. Netscaler pre-requisites are [here](https://github.com/chiradeep/nitrox/blob/master/README.md)

## As a container
### Launch the 'nitrox' container 
The code has been containerized into `chiradeeptest/nitrox` . You can either run it as a Marathon app, or use this container on the same server as the Marathon master.

#### On the master
````
[root@marathon-master ~]# 
[root@marathon-master ~]# docker run \
           -e NS_IP=$NS_IP \
           -e NS_USER=$NS_USER \
           -e NS_PASSWORD=$NS_PASSWORD \
           -e APP_INFO='{"apps": [{"name": "AccountService"}, {"name": "ProductCatalog"}, {"name":"ShoppingCart"}, {"name":"OrderServer"}]}' \
           -d \
           --name nitrox \
           chiradeeptest/nitrox \
           --marathon-url=http://marathon-master:8080/
````
Monitor the logs of the containers with `docker logs nitrox`

#### As a Marathon app
The nitrox container can be scheduled using the Marathon APIs:

````
curl -X POST http://marathon-master:8080/v2/apps -d @nitrox.json -H "Content-type: application/json"
````

You can find `nitrox.json` [here](https://github.com/chiradeep/nitrox/blob/master/nitrox.json)

### Test
Run some containers using Marathon and see your netscaler get reconfigured 

````
curl -X POST http://marathon-master:8080/v2/apps -d @basic-3.json -H "Content-type: application/json
````
Use the UI to scale the process up or down and watch the Netscaler being reconfigured



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

Run the code while pointing it to the Marathon environment. 

```
python main.py  --marathon-url=http://marathon-master:8080/ 
```

Test by launching containerized apps using the Marathon API and scaling them up/down using the GUI.

