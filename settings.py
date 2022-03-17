#!/usr/bin/python3

assets_url = "" #a your own url which return an assets.json configuration
zabbix_from_port = 10051 #port range for SG
zabbix_to_port = 10051
log_file = "zabbix_network_setup.log"
script_description = "ZABBIX NETWORK SETUP"
default_assets_file = "assets_services.json"
cf_creation_timeout = 120 #timeout for waiting a cloudformation stack creation

# default tags for the VPC SG
default_tags = [
	{
		"Key": "Project",
		"Value": "progetto-bellissimo"
	},
	{
		"Key": "Env",
		"Value": "prod"
	},
	{
		"Key": "Owner",
		"Value": "a beautiful guy"
	}
]