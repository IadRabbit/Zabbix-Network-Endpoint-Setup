#!/usr/bin/python3

from json import load as json_load
from argparse import ArgumentParser
from requests import get as req_get

from settings import (
	script_description, assets_url, default_assets_file
)

parser = ArgumentParser(description = script_description)

parser.add_argument(
	"-p1", "--profile1",
	required = True,
	help = "Storm Reply Management aws profile name"
)

parser.add_argument(
	"-p2", "--profile2",
	required = True,
	help = "Account to integrate zabbix monitoring aws profile name"
)

parser.add_argument(
	"-asg", "--add-sg",
	default = False,
	action = "store_true",
	help = "Adding to all ec2's security group an outbound rule for Zabbix IP"
)

parser.add_argument(
	"-ct", "--custom-template",
	default = False,
	help = "Choose a custom Cloudformation Template to use"
)

parser.add_argument(
	"-ac", "--assets-config",
	default = True,
	action = "store_false",
	help = "Parameter for specify a custom 'assets_services.json'"
)

c_args = parser.parse_known_args()
assets_config = c_args[0].assets_config

if assets_config:
	assets_services = req_get(assets_url).json()
else:
	with open(default_assets_file, "r") as f:
		assets_services = json_load(f)

regions = assets_services.keys()

parser.add_argument(
	"-r", "--region",
	required = True,
	choices = regions,
	help = "Account region where are the ec2 instances"
)

parser.add_argument(
	"-rs", "--recursive-stack",
	default = False,
	action = "store_true",
	help = "Continue the setup even if a previous setup has been detected (NOT SUGGESTED)"
)

c_args = parser.parse_known_args()
c_region = c_args[0].region
c_service_region =  assets_services[c_region]['region']

parser.add_argument(
	"-sn", "--stack-name",
	default = f"VPCEndpointMonitoring{c_service_region}",
	help = "Choose a stack name"
)

args = parser.parse_args()

c_region = args.region
c_services = assets_services[c_region]
c_service_id = c_services['service_id']
c_service_region = c_services['region']
c_service_name = c_services['service_name']
recursive_stack = args.recursive_stack
stack_name = args.stack_name
add_sg = args.add_sg
cf_template_file = args.custom_template
profile1 = args.profile1
profile2 = args.profile2