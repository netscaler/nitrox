# Nitrox
Configure Citrix Netscaler loadbalancing for container platforms such as Docker Swarm and Mesos Marathon. Currently only Docker Swarm is supported.

# Theory of Operation
1. Containers that form a load-balanced backend for an app/microservice are labeled with the same label (e.g., com.citrix.lb.appname=AccountService, or AccountService)
2. Information (host IP and port) from the container platform (such as  [Docker Swarm](https://docs.docker.com/swarm/)) API for the labeled containers are used to configure a Netscaler loadbalancer.
3. The Netscaler admin creates the "frontend" `lb vserver` with the label used in #1

<img src="https://github.com/chiradeep/nitrox/blob/master/nitrox.png" width="480"/>

# Netscaler Pre-requisites

1. Credentials for a running Citrix Netscaler (VPX/MPX/SDX). On the host where you run the container/code, replace with your own:

   ````
   export NS_IP=10.220.73.33
   export NS_USER=nsroot
   export NS_PASSWORD=3df8jha@k0
   ````

2. List of microservices / apps that have to be load balanced. For example, 'AccountService', 'ProductCatalog', 'ShoppingCart', etc.
3. Netscaler that has been configured with VIP(s) for above apps. For example, lets say there is a microservice/app called 'AccountService' with a load balanced IP of 10.220.73.222. On the Netscaler:
    ```
    add lb vserver AccountService HTTP 10.220.73.222 80 -persistenceType COOKIE -lbMethod LEASTCONNECTION
    ```
    Alternatively, if the `lb_ip` and `lb_port` are included in the `APP_INFO` env variable, the `lb vserver` is configured automatically with some default options (`ROUNDROBIN`)

#Container Platforms

### Docker Swarm
[Docker Swarm] (https://docs.docker.com/swarm/) is a clustered container manager. Instructions are [here](https://github.com/chiradeep/nitrox/swarm/blob/master/swarm/README.swarm.md)

### Marathon
[Marathon] (https://mesosphere.github.io/marathon/) is a PAAS framework that can run containerized workloads. Instructions are [here](https://github.com/chiradeep/nitrox/blob/master/marathon/README.marathon.md)
