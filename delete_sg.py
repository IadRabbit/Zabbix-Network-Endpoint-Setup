#!/usr/bin/python3

from sys import argv
from pprint import pp
from boto3 import Session

profile = argv[1]
region = argv[2]
sg_id = argv[3]

aws_session = Session(
	profile_name = profile,
	region_name = region
)

ec2_api = aws_session.client("ec2")

sg_data = ec2_api.describe_security_groups(
	Filters=[
		{
			"Name": "egress.ip-permission.group-id",
			"Values": [
				sg_id
			]
		},
	],
)['SecurityGroups']

for sg in sg_data:
	c_sg_id = sg['GroupId']
	print(c_sg_id)

	resp = ec2_api.revoke_security_group_egress(
		GroupId = c_sg_id,
		IpPermissions = [
			{
				"FromPort": 10051,
				"ToPort": 10051,
				"IpProtocol": "tcp",
				"UserIdGroupPairs": [
					{
						"GroupId": sg_id
					}
				]
			}
		]
	)


resp = ec2_api.delete_security_group(GroupId = sg_id)