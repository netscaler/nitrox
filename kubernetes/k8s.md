#Kubernetes Configuration

## Authentication
The simplest way to get services in pods to use the API server is to run the API server with token authentication enabled. If not already enabled, here are some steps:

1. If not already using certificates, generate certificates using this [script](https://github.com/kubernetes/kubernetes/blob/master/cluster/saltbase/salt/generate-cert/make-ca-cert.sh).  The certificate material will be in /srv/kubernetes

    ```
    export CLUSTER_IP=$(kubectl get service kubernetes -o template --template {{.spec.clusterIP}})
    export CERT_GROUP=kube
    ./make-ca-cert.sh <master_ip> IP:<master_ip>,IP:$CLUSTER_IP,DNS:kubernetes,DNS:kubernetes.default,DNS:kubernetes.default.svc,DNS:kubernetes.default.svc.cluster.local
    touch /srv/kubernetes/known_tokens.csv
    ```
    
2. Change the parameters of the kube-apiserver and kube-controller-manager using the files `/etc/kubernetes/apiserver` and `/etc/kubernetes/controller-manager`. 

    ````
    /etc/kubernetes/apiserver:
    KUBE_API_ARGS="--client-ca-file=/srv/kubernetes/ca.crt --tls-cert-file=/srv/kubernetes/server.cert --tls-private-key-file=/srv/kubernetes/server.key --token-auth-file=/srv/kubernetes/known_tokens.csv"
    /etc/kubernetes/controller-manager
    KUBE_CONTROLLER_MANAGER_ARGS="--root-ca-file=/srv/kubernetes/ca.crt --service-account-private-key-file=/srv/kubernetes/server.key"
    ````
3. Restart

   ````
   systemctl restart kube-apiserver
   systemctl restart kube-controller-manager
   ````
4. You may have to clean up all existing services and create them from scratch (YMMV)
5. You can add users by editing `/srv/kubernetes/known_tokens.csv`

    ````
    echo 'ABCDEFGHIKLMNOPQRSTUVWXYZ,scout,admin' >> /srv/kubernetes/known_tokens.csv
    systemctl restart kube-apiserver
    ````
    Your cluster users can use this token
    
    ````
    kubectl config set-credentials --token=ABCDEFGHIJKLMNOPQRSTUVWXYZ
    ````
6. See the [Kubernetes User Guide to Accessing the Cluster](https://github.com/kubernetes/kubernetes/blob/master/docs/user-guide/accessing-the-cluster.md) for more help

## Service Accounts
We need to enable service accounts. Edit `/etc/kubernetes/apiserver`. Ensure that this line has `ServiceAccount`:

````
KUBE_ADMISSION_CONTROL="--admission_control=NamespaceLifecycle,NamespaceExists,LimitRanger,SecurityContextDeny,ResourceQuota,ServiceAccount"
````

and restart: `systemctl restart kube-apiserver`

