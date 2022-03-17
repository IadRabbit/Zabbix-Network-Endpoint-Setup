#!/usr/bin/python3

from time import sleep
from boto3 import Session
from botocore.errorfactory import ClientError

from settings import (
	log_file, cf_creation_timeout,
	zabbix_from_port, zabbix_to_port
)

from log import (
	l_info, l_error, l_warning
)

class API:
	# class constructor with necessary information
	def __init__(
		self, profile,
		region, c_service_id,
		c_service_name
	):
		self.__aws_session = Session(
			profile_name = profile,
			region_name = region
		)

		self.c_service_id = c_service_id
		self.c_service_name = c_service_name
		self.account_id = self.__get_account_id()
		self.set_ec2_api()
		self.set_cf_api()

	@staticmethod
	def get_vpc_tags_str(tags):
		c_str = ""

		if "Tags" in tags:
			for tag in tags['Tags']:
				c_str += f"{tag['Key']}: \033[0;32;40m{tag['Value']}\033[0;37;40m, "

		return c_str[:-2]

	def set_ec2_api(self):
		self.__ec2_api = self.__aws_session.client("ec2")

	def set_cf_api(self):
		self.__cf_api = self.__aws_session.client("cloudformation")

	def __get_account_id(self):
		account_id = (
			self.__aws_session
			.client("sts")
			.get_caller_identity()
			.get("Account")
		)

		return account_id

	def allow_principal(self, rem_account_id):
		msg = f"Allowing account_id: '{rem_account_id}' ..."
		l_info(msg)

		resp = self.__ec2_api.modify_vpc_endpoint_service_permissions(
			ServiceId = self.c_service_id,
			AddAllowedPrincipals = [
				f"arn:aws:iam::{rem_account_id}:root"
			]
		)

		if resp['ReturnValue']:
			msg = f"Account: '{rem_account_id}' has been allowed :)"
			l_info(msg)
		else:
			msg = f"Account: '{rem_account_id}' has NOT been allowed :("
			l_error(msg)
			exit()

	def describe_vpcs(self):
		vpcs_data = self.__ec2_api.describe_vpcs()['Vpcs']

		return vpcs_data

	def describe_stack(self, stack_name):
		stack_data = self.__cf_api.describe_stacks(StackName = stack_name)

		return stack_data

	def check_cf_stack_progress(self, stack_name, recursive_stack):
		msg = "Wait, the Stack is doing his job :), may take 1 minute"
		l_info(msg)
		step = 0

		while True:
			resp = self.describe_stack(stack_name)

			if resp['Stacks'][0]['StackStatus'] == "CREATE_COMPLETE":
				break

			elif resp['Stacks'][0]['StackStatus'] == "ROLLBACK_IN_PROGRESS":
				msg = f"It appears that there is a conflict with previous stack :(, look in the AWS console"
				l_error(msg)

				if not recursive_stack:
					exit()

				msg = f"Recursive enabled... continuing with setup"
				l_warning(msg)
				break

			elif step == cf_creation_timeout:
				msg = f"Something went wrong during the creation of stack: {stack_name}.\n Check on the CloudFormation Console"
				l_error(resp)
				exit()

			else:
				step += 1
				sleep(1)

	def create_stack(
		self,
		stack_name, template,
		recursive_stack = False
	):
		try:
			resp = self.__cf_api.create_stack(
				StackName = stack_name,
				TemplateBody = template.read()
			)

			self.check_cf_stack_progress(stack_name, recursive_stack)
		except ClientError as err:
			if err.response['Error']['Code'] == "AlreadyExistsException":
				msg = f"A Cloudformation Stack named: '{stack_name}' already exist, my job here is done :)"
				l_warning(msg)
			else:
				msg = f"An expected error happened read the {log_file}' for details :("
				l_error(err)

			if not recursive_stack:
				exit()

		msg = f"Stack: '{stack_name}' has been successful created =)"
		l_info(msg)

	def accept_vpc_endpoint(self, account_id):
		msg = f"Accepting the VPC Endpoint for '{account_id}'"
		l_info(msg)

		vpc_endpoints_data = self.__ec2_api.describe_vpc_endpoint_connections(
			Filters = [
				{
					"Name": "vpc-endpoint-state",
					"Values": [
						"pendingAcceptance"
					]
				},
				{
					"Name": "vpc-endpoint-owner",
					"Values": [
						account_id
					]
				}
			]
		)['VpcEndpointConnections']

		vpc_endpoints = [
			vpc_endpoint['VpcEndpointId']
			for vpc_endpoint in vpc_endpoints_data
		]

		if vpc_endpoints:
			self.__ec2_api.accept_vpc_endpoint_connections(
				ServiceId = self.c_service_id,
				VpcEndpointIds = vpc_endpoints
			)

			msg = f"VPC Endpoint accepted for '{account_id}'"
		else:
			msg = f"No current pending VPC endopoints"

		l_info(msg)

	def describe_subnets(self, vpcs_ids):
		subnets_data = self.__ec2_api.describe_subnets(
			Filters = [
				{
					"Name": "vpc-id",
					"Values": vpcs_ids
				}
			]
		)['Subnets']

		return subnets_data

	def enable_vpc_dns(self, vpc_id):
		msg = f"Enabling DNS Hostname for '{vpc_id}'"
		l_info(msg)

		self.__ec2_api.modify_vpc_attribute(
			EnableDnsHostnames = {
				"Value": True
			},
			VpcId = vpc_id
		)

		msg = f"Enabling DNS Support for '{vpc_id}'"
		l_info(msg)

		self.__ec2_api.modify_vpc_attribute(
			EnableDnsSupport = {
				"Value": True
			},
			VpcId = vpc_id
		)

	def add_sg_to_ec2(self, vpc_id):
		msg = f"Adding SG rules in outbound for EC2 instances inside '{vpc_id}'"
		l_info(msg)

		sg_data = self.__ec2_api.describe_security_groups(
			Filters=[
				{
					"Name": "tag:network_zabbix_sg",
					"Values": [
						vpc_id
					]
				},
			],
		)['SecurityGroups']

		zabbix_sg_id = sg_data[0]['GroupId']

		ec2s_data = self.__ec2_api.describe_instances(
			Filters = [
				{
					"Name": "vpc-id",
					"Values": [
						vpc_id
					]
				}
			]
		)['Reservations']

		c_sgs_ids = []

		for ec2_data in ec2s_data:
			c_ec2 = ec2_data['Instances'][0]
			sg_id = c_ec2['SecurityGroups'][0]['GroupId']
			msg = f"Adding SG rules in outbound for EC2 '{c_ec2['InstanceId']}' SG '{sg_id}'"
			l_info(msg)

			if sg_id in c_sgs_ids:
				continue

			try:
				resp_sg_auth = self.__ec2_api.authorize_security_group_egress(
					GroupId = sg_id,
					IpPermissions = [
						{
							"FromPort": zabbix_from_port,
							"IpProtocol": "tcp",
							"UserIdGroupPairs": [
								{
									"GroupId": zabbix_sg_id,
									"Description": "Zabbix Endpoint SG"
								}
							],
							"ToPort": zabbix_to_port
						}
					]
				)
			except ClientError:
				msg = f"!! There is already a rule for SG {sg_id}"
				l_warning(msg)

			c_sgs_ids.append(sg_id)

		msg = f"Added all SG rules for EC2 inside '{vpc_id}'"
		l_info(msg)

	def describe_vpc_endpoints(self, vpcs_ids):
		vpc_endpoints_data = self.__ec2_api.describe_vpc_endpoints(
			Filters = [
				{
					"Name": "vpc-endpoint-type",
					"Values": [
						"Interface",
					]
				},
				{
					"Name": "vpc-id",
					"Values": vpcs_ids
				}
			]
		)['VpcEndpoints']

		return vpc_endpoints_data

	def modify_vpc_endpoint(self, vpc_endpoint_id, c_subnets):
		resp = self.__ec2_api.modify_vpc_endpoint(
			VpcEndpointId = vpc_endpoint_id,
			PrivateDnsEnabled = True,
			AddSubnetIds = c_subnets
		)

	def check_sg_exist(self, sg_name):
		exist, sg_id = False, True
		print(sg_name)

		sg_data = self.__ec2_api.describe_security_groups(
			Filters=[
				{
					"Name": "group-name",
					"Values": [
						sg_name
					]
				},
			],
		)['SecurityGroups']

		if len(sg_data) > 0:
			exist, sg_id = True, sg_data[0]['GroupId']

		return exist, sg_id