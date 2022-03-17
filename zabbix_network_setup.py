#!/usr/bin/python3

############ ZABBIX NETWORK SETUP SIUM SCRIPT XD =) #######
# Author: Federico Zota                                   #
# Project a lucky guy         		                      #
# alias SIUM=yay                                          #
###########################################################

#importing all necessary stuff

from api import API
from os import getcwd
from pprint import pp
from os.path import isfile
from json import dump as json_dump

from settings import (
	zabbix_from_port, zabbix_to_port, default_tags
)

from log import (
	l_info, l_error, l_warning
)

# importing all parameters when script is executed

from cli import (
	c_region, c_service_id, c_service_name,
	recursive_stack, stack_name,
	add_sg, cf_template_file,
	profile1, profile2
)

# check if using a custom local cf stack template

if cf_template_file:
	if not isfile(cf_template_file):
		msg = f"NO FILE NAMED '{cf_template_file}' in '{getcwd()}'"
		l_error(msg)
		exit()

msg = "Starting Network Integration For Zabbix"
l_info(msg)

# creating necessary data structure to be elaborated in different functions
vpcs_datas = []
vpcs_ids = []
subnets = {}
cidr_blocks = {}

# login through profile name to 'MASTER ACCOUNT' where zabbix server is located
aws_api_SRM = API(profile1, c_region, c_service_id, c_service_name)

# login through profile name to 'MEMBER ACCOUNT' where need to communicate with 'MASTER ACCOUNT' vpc endpoing
aws_api_ANY = API(profile2, c_region, c_service_id, c_service_name)

# function for scanning all avalaible VPC inside an account, in this case 'MEMBER ACCOUNT'

def scan_vpcs():
	msg = f"Scanning for avalaible VPCs in region '{c_region}'"
	l_info(msg)
	vpcs_data = aws_api_ANY.describe_vpcs()

	for vpc_data in vpcs_data:
		vpc_id = vpc_data['VpcId']
		msg = f"Found VPC: '{vpc_id}'"
		l_info(msg)

		c_data = {
			"vpc_id": vpc_id,
			"details": aws_api_ANY.get_vpc_tags_str(vpc_data),
		}

		cidr_blocks[vpc_id] = vpc_data['CidrBlock']

		vpcs_datas.append(c_data) # adding necessary information to list

# I don't think this need explanation :))

def display_help_vpc():
	print(
		"""
		\nTo choose multiple VPC (1,3,4) follow this format
		\nIf you want to monitor all, choose last option
		"""
	)

# function for displaying in the terminal all VPC found in the 'MEMBER ACCOUNT'

def choose_vpcs(l_vpcs_datas):
	vpcs_ids.clear() # this is a function which is called inside an 'while' statement so every time we need to 'reset' the list for avoid old data

	# simple for statement for displaying all data saved previously in the vpcs_datas list during 'scan_vpcs' function execution
	for a in range(l_vpcs_datas):
		c_vpc_id = vpcs_datas[a]['vpc_id']
		c_details = vpcs_datas[a]['details']

		print(f"\n{a + 1}): {c_vpc_id} ({c_details})")

	print(f"{a + 2}): Monitor all VPCs")

	display_help_vpc()
	ans = input("\nChoose the vpc you want to monitor: ")

	# condition statement for checking & sanitaze user input

	if ans == str(a + 2): # checking if user chose last option for monitoring all VPC
		for vpc_data in vpcs_datas:
			vpcs_ids.append(vpc_data['vpc_id'])
	else:
		# some input checks
		for num in ans.split(","):
			if not num.isdigit():
				msg = "Invalid input, not integer"
				l_error(msg)
				exit()

			index = int(num)

			if not(1 <= index <= l_vpcs_datas):
				msg = "Invalid input, number to high"
				l_error(msg)
				exit()

			c_vpc_id = vpcs_datas[index - 1]['vpc_id']

			if c_vpc_id in vpcs_ids:
				msg = f"You typed {c_vpc_id} twice. Ignoring duplication"
				l_warning(msg)
			else:
				vpcs_ids.append(c_vpc_id)

# function to create the CF stack template, modify it with very * 10 attention

def create_json_template():
	msg = "Creating JSON Template for the Cloudformation Stack"
	l_info(msg)
	description = "Template which creates the VPC Endpoint (Interface) to connect to StormReplyManagement Service Endpoint"
	aws_template_version = "2010-09-09"

	template_data = {
		"AWSTemplateFormatVersion": aws_template_version,
		"Description": description,
		"Parameters": {
			"ServiceNameParameter": {
				"Type": "String",
				"Default": c_service_name,
				"Description": "String VPC Endpoint ID corresponding to the region your are going to monitor"
			}
		},
		"Resources": {}
	}

	parameters = template_data['Parameters']
	resources = template_data['Resources']

	for vpc_id in vpcs_ids:
		c_vpc_id = vpc_id.replace("-", "")
		c_description = f"Monitoring VPC: {c_vpc_id}"
		c_vpc_id_parameter = f"VpcIdParameter{c_vpc_id}"
		c_resource_zabbix_vpce = f"ZabbixVPCEndpoint{c_vpc_id}"
		c_resource_zabbix_vpce_sg = f"ZabbixVPCEndpointSecurityGroup{c_vpc_id}"

		parameters[c_vpc_id_parameter] = {
			"Type": "String",
			"Default": vpc_id,
			"Description": c_description
		}

		exist, sg_id = aws_api_ANY.check_sg_exist(f"{vpc_id}-zabbix-endpoint-sg")

		if exist:
			ref = sg_id
		else:
			ref = {"Ref": c_resource_zabbix_vpce_sg}

		resources[c_resource_zabbix_vpce] = {
			"Type": "AWS::EC2::VPCEndpoint",
			"Properties": {
				"ServiceName": {
					"Ref": "ServiceNameParameter"
				},
				"VpcEndpointType": "Interface",
				"VpcId": {
					"Ref": c_vpc_id_parameter
				},
				"SecurityGroupIds": [ref]
			}
		}

		if exist:
			continue

		c_tags = default_tags.copy()

		c_tags.append(
			{
				"Key": "network_zabbix_sg",
				"Value": vpc_id
			}
        )

		c_tags.append(
			{
				"Key": "Name",
				"Value": f"Zabbix Asset SG by {c_vpc_id_parameter}"
			}
		)

		resources[c_resource_zabbix_vpce_sg] = {
			"Type": "AWS::EC2::SecurityGroup",
			"Properties": {
				"GroupDescription": "Allow VPC Endpoint Access",
				"GroupName": {
					"Fn::Sub": f"${{{c_vpc_id_parameter}}}-zabbix-endpoint-sg"
				},
				"SecurityGroupIngress": [
					{
						"IpProtocol": "tcp",
						"FromPort": zabbix_from_port,
						"ToPort": zabbix_to_port,
						"CidrIp": cidr_blocks[vpc_id]
					},
					{
						"CidrIp": cidr_blocks[vpc_id],
						"Description": "Access to Loki server",
						"FromPort": 3100,
						"ToPort": 3100,
						"IpProtocol": "tcp"
					}
				],
				"SecurityGroupEgress": [
					{
						"IpProtocol": "-1",
						"CidrIp": "127.0.0.1/32"
					},
				],
				"Tags": c_tags,
				"VpcId": {
					"Ref": c_vpc_id_parameter
				}
			}
		}

		# Add DeletionPolicy only if -asg param is specified

		if add_sg:
			resources[c_resource_zabbix_vpce_sg]['DeletionPolicy'] = "Retain"

	with open(cf_template_file, "w") as f:
		json_dump(template_data, f, indent = 4)

	msg = "JSON Template for the Cloudformation Stack created :)"
	l_info(msg)

# uploading/executing cf stack

def upload_cf_stack():
	with open(cf_template_file, "r") as template:
		aws_api_ANY.create_stack(stack_name, template, recursive_stack)

# function for getting all subnets in every VPC selected earlier

def get_subnets():
	msg = "Scanning for subnets to add to VPC Endpoints"
	l_info(msg)

	subnets_data = aws_api_ANY.describe_subnets(vpcs_ids)

	for subnet in subnets_data:
		vpc_id = subnet['VpcId']

		if not vpc_id in subnets:
			subnets[vpc_id] = {}

		zone = subnet['AvailabilityZone']
		c_data = subnets[vpc_id]
		subnet_id = subnet['SubnetId']

		# we only need a subnet for zone

		if not zone in c_data:
			c_data[zone] = {
				"subnet_id": subnet_id
			}

			msg = f"Added Subnet_Id: '{subnet_id}', for VPC_Id: '{vpc_id}' in zone: '{zone}'"
			l_info(msg)

# this function is necessary for enabling connection between the two endpoints, adding the subnets and enabling private DNS

def enable_endpoints():
	msg = "Enabling VPC Endpoints..."
	l_info(msg)

	vpc_endpoints = aws_api_ANY.describe_vpc_endpoints(vpcs_ids)

	for vpc_endpoint in vpc_endpoints:
		vpc_endpoint_id = vpc_endpoint['VpcEndpointId']
		vpc_id = vpc_endpoint['VpcId']

		c_subnets = [
			subnets[vpc_id][region]['subnet_id']
			for region in subnets[vpc_id]
		]

		aws_api_ANY.enable_vpc_dns(vpc_id)

		if add_sg:
			aws_api_ANY.add_sg_to_ec2(vpc_id)

		aws_api_ANY.modify_vpc_endpoint(vpc_endpoint_id, c_subnets)
		msg = f"VPC_Id '{vpc_id}' Enabled :))"
		l_info(msg)

# enabling principal in the 'MASTER ACCOUNT'

aws_api_SRM.allow_principal(aws_api_ANY.account_id)
scan_vpcs()

l_vpcs_datas = len(vpcs_datas)
c_ans = "n"

while c_ans != "y":
	choose_vpcs(l_vpcs_datas)
	print(f"\nYou choose these VPCs: {' & '.join(vpcs_ids)}")
	c_ans = input("Is this ok ? (y/n): ")

get_subnets()

if not cf_template_file:
	cf_template_file = f"ZabbixStack-{stack_name}.json"
	create_json_template()

upload_cf_stack()
aws_api_SRM.accept_vpc_endpoint(aws_api_ANY.account_id)
enable_endpoints()

msg_final = "ALL DONE SIUMMMMM =)))"
l_info(msg_final)