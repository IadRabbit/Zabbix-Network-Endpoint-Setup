# Zabbix Network Endpoint Setup
A nice script wrote to setup the connection from a member account to a master account enabling connection to Zabbix server

### Disclaimer

Some content as photo in below aren't mine, I just took it from this [GUIDE](https://tomgregory.com/cross-account-vpc-access-in-aws/#Option_2_VPC_endpoint_service_PrivateLink_cross-account_access) where the **Option 2** explain the process very well.

### If you encounter bugs, it isn't a bug it is a feature :)

<!-- TABLE OF CONTENTS -->

## Table of contents

   * [Network Explanation](#network-explanation)
   * [Getting Started](#getting-started)
      * [Prerequisites](#prerequisites)
      * [What Script Does](#what-script-does)
      * [Installation](#installation)
      * [Configuration](#configuration)
   * [Usage](#usage)
      * [delete sg.py (Delete the Zabbix rule from all SG)](#delete_sg)
      * [zabbix_network_setup.py (Main)](#zabbix_network_setup)
   * [Manual](#manual)
      * [man zabbix_network_setup.py](#man-zabbix_network_setup)

 ## Network Explanation

This photo explain the infrastructure between the 2 endpoints

![network-infrastructure](https://lucid.app/publicSegments/view/3d4ad304-ad6f-4439-b679-43820b5f15e5/image.png)

There are two accounts:
* MASTER ACCOUNT (VPC A)
* MEMBER ACCOUNT (VPC B)

We need to establish a connection between 2 different AWS accounts the **MASTER**, where there is our Zabbix Server & **MEMBER** where there are our EC2 instances we need to monitor.

So we need to create an:
* **Endpoint Service**
* associate our **ELB**, which redirect to our **Zabbix Server**
* Allowing the **Member account**
* Accept endpoint connection request

## Getting Started

This project will only try to automate **ONLY** the operation from **ALLOWING THE MEMBER ACCOUNT**.

### Prerequisites

**REMEMBER THAT THE ENDPOINT SERVICE AND THE EC2 INSTANCES MUST BE IN THE SAME REGION. CAN'T CREATE A CONNECTION BETWEEN AN ACCOUNT HOSTED IN IRELAND AND ONE IN FRANKFURT, SO YOU NEED TO CREATE A ENDPOINT SERVICE FOR EVERY DIFFERENT REGION**

* The **Enpoint Service** must already exist, the script won't create one
* The **ELB** must already be associated to the **Endpoint Service**

### What Script Does

1. Allow Principal how is explained [here](https://docs.aws.amazon.com/vpc/latest/privatelink/add-endpoint-service-permissions.html)
2. Display all VPC in the account, for choosing which one you want to setup the connection to the endpoint service
3. Create a Cloud Formation Template with the input received as VPC/Zabbix Ports etc & upload it
4. Accept the VPC endpoint on the MASTER ACCOUNT
5. Enable the endpoints, Enable the DNS Hostname for VPC, Enable DNS Support, Enable Private DNS, Add subnets to the VPC endpoint

### Installation

1. You need **python >= 3.9**, may work even with other python3 versions
2. Clone the repo
   ```sh
   git clone https://github.com/IadRabbit/Zabbix-Network-Endpoint-Setup.git
   ```
3. Open a terminal, go inside the cloned project & install the libs with this command
    ```sh
    pip3 install -r req.txt
    ```
 
 ### Configuration
 
 In the **settings.py** file there are some **settings variables**
 
 ![immagine](https://user-images.githubusercontent.com/87022719/158791048-41f4c7f9-ecec-4185-ab89-bdf37d03de5c.png)

I suggest you to upload your **assets_services.json** to a **S3 BUCKET** with public access & copy the url in the **assets_url** variable.

The **assets_services.json** in your cloned folder should look like this

![immagine](https://user-images.githubusercontent.com/87022719/158791125-d94ae242-379a-43e4-a5e5-3b542a6ee45e.png)

The JSON Keys are identical to the information to copy located in the **Details Tab** of your **Endpoint Service**.

The JSON **Region** key is INDIPENDENT it is only a variable used for the default CF (Cloudformation) template name, just to make more sense instead of using 'eu-west-1' etc.

## Usage

Be sure first you followed the [Configuration](#configuration)

### zabbix_network_setup

First we have to login with our aws credentials you may follow this [guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) in order to setup the **Programatic Access** in the way you prefer. Personally I use [saml2aws](https://github.com/Versent/saml2aws), **REMEMBER** to use different profile name

  * Let login in our master account

     ```sh
     saml2aws login -p MASTER_ACCOUNT
     ```

  * Let login in our member account

     ```sh
     saml2aws login -p MEMBER_ACCOUNT
     ```
     
  * Let start our awesome (PLEASE WORK) script

    ```sh
    python3 zabbix_network_setup.py -p1 MASTER_ACCOUNT -p2 MEMBER_ACCOUNT -r eu-west-1
    ```
    
    ### CAREFUL

    Remember that profile names can have every name you want and most important the region can change 'eu-west-1' is just an example in your case may be 'eu-center-1' look to your aws console to see the Endpoint Service Location
   
  * THAT IS ALL :). WAIT SOME MINUTES AND THE SETUP SHOULD BE ACCOMPLISHED

## delete_sg

If you have chosen to use the **zabbix_network_setup.py** with the '**-asg**' param for adding a custom outbound rule for you EC2 instances due your restricted access & deleted the CF stack you can use this script to delete permanently all the SG associated with the CF stack

```sh
saml2aws login -p MEMBER_ACCOUNT
python3 delete_sg.py MEMBER_ACCOUNT eu-west-1 sg-0123456789
```

  ### Careful
  You need to be sure what is the region of your SG and the SG ID associated with the VPC, you can look for something like 'Zabbix Asset SG by' in the AWS console in the section of Security Groups

## Manual

### man zabbix_network_setup

  The [cli.py](https://github.com/IadRabbit/Zabbix-Network-Endpoint-Setup/blob/main/cli.py) contains all params for the zabbix_network_setup.py script.
  
  * -p1 (--profile1) is the param used for specify the "**MASTER ACCOUNT**" (ALWAYS REQUIRED)
  * -p2 (--profile2) is the param used for specify the "**MEMBER ACCOUNT**" (ALWAYS REQUIRED)
  * -r (--region) is the param used for specify the "**REGION**" of the VPC endpoint service (ALWAYS REQUIRED)
  * -asg (--add-sg) is the param used to add to all EC2 in the VPC you selected a SG rule in outbound to reach Zabbix Server (Default: False)
    * Use this option if you have restricted access to your EC2 in outbound, if you want then delete all these exceptions rules execute [delete_sg.py](https://github.com/IadRabbit/Zabbix-Network-Endpoint-Setup/blob/main/delete_sg.py)

  * -ct (--custom-template) is the param used to specify a custom CF (Cloud Formation) template for creating the Network Setup stack with zabbix (Default: False)
  * -ac (--assets-config) is the param used to specify a custom '**assets_services.json**' in your local folder, if you don't want to get the json configuration from an S3 bucket how told in the [Configuration](#configuration) (Default: Does a request to the S3 url specified in the [settings.py](https://github.com/IadRabbit/Zabbix-Network-Endpoint-Setup/blob/main/settings.py)
  * -rs (--recursive-stack) is the param used to specify the continuation of the setup even if a previous CF template exists. Isn't really suggested would be better delete the previous CF stack (Default: False)
  * -sn (--stack-name) is the param used to specify how to call the CF stack (Default: VPCEndpointMonitoring<REGION_NAME>
