# Nitrox for Consul-Template

# Usage
## Pre-requisites
1. [Consul-template] (https://github.com/hashicorp/consul-template)
2. Netscaler pre-requisites are [here](https://github.com/chiradeep/nitrox/blob/master/README.md)

## Theory  of operation
`consul-template` creates a JSON config file for a Consul service. This config file is fed to the python script which drives Netscaler configuration

## Example

````
consul-template -consul $CONSUL_IP:8500 -template consul_single_svc.ctmpl:cfg.json:"python cfg_file.py --cfg-file cfg.json"
````



