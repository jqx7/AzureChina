#!/usr/bin/env python
# -*- coding:utf-8 -*-

import json,time
from msrestazure.azure_cloud import AZURE_CHINA_CLOUD
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.compute.models import DiskCreateOption
from azure.mgmt.resource import SubscriptionClient



#-------------------------------------login-------------------------------------------
def azurearm_credentials():
    credentials = ServicePrincipalCredentials(
        client_id='XXX',
        secret='XXX',
        tenant='XXX',
        cloud_environment=AZURE_CHINA_CLOUD
    )
    return credentials

#-------------------------------------resourcegroup--------------------------------------
#Resource Group Generated
def create_resource_group(resourcegroup_client):
    resourcegroup_result = resourcegroup_client.resource_groups.create_or_update(GROUP_NAME,{'location':LOCATION})
    return resourcegroup_result

#Availability Set Generated
def create_availability_set(compute_client):
    avset_params = {'location': LOCATION,'sku': { 'name': 'Aligned' },'platform_fault_domain_count': 2,'platform_update_domain_count':2}
    availability_set_result = compute_client.availability_sets.create_or_update(GROUP_NAME,AVSET_NAME,avset_params)
    return availability_set_result

#-------------------------------------net--------------------------------------
#VNET Generated
def create_vnet(network_client):
    vnet_params = {'location': LOCATION, 'address_space': {'address_prefixes': ['172.16.77.0/24']}}
    creation_result = network_client.virtual_networks.create_or_update(GROUP_NAME, VNET_NAME, vnet_params)
    return creation_result.result()

#Subnet Generated
def create_subnet(network_client):
    subnet_params = {'address_prefix': '172.16.77.0/24'}
    creation_result = network_client.subnets.create_or_update(GROUP_NAME, VNET_NAME, SUBNET_NAME, subnet_params)
    return creation_result.result()

#Public IP Generated
def create_public_ip_address(network_client):
    public_ip_addess_params = {'location': LOCATION,'public_ip_allocation_method': 'static','dns_settings': {'domain_name_label': DOMAIN_NAME_LABEL},'idle_timeout_in_minutes': 5}
    creation_result = network_client.public_ip_addresses.create_or_update(GROUP_NAME,PUBLICIP_NAME,public_ip_addess_params)
    public_ip_info = creation_result.result()
    return public_ip_info

#-------------------------------------lb--------------------------------------

def lb_creation(subscription_id, GROUP_NAME,PUBLICIP_NAME,LB_NAME, LB_RULE_NAME,PROBE_NAME,FRONTEND_POOL_NAME,ADDRESS_POOL_NAME,NATRULE_NAME1,NATRULE_NAME2,FRONTEND_PORT1,FRONTEND_PORT2,BACKEND_PORT):
    #Schdule the FrontEndId will be used.
    construct_fip_id = '/subscriptions/{}''/resourceGroups/{}''/providers/Microsoft.Network''/loadBalancers/{}''/frontendIPConfigurations/{}'.format(subscription_id, GROUP_NAME, LB_NAME, FRONTEND_POOL_NAME)
    #Schdule the ProbeId will be used.
    construct_bap_id = '/subscriptions/{}''/resourceGroups/{}''/providers/Microsoft.Network''/loadBalancers/{}''/backendAddressPools/{}'.format(subscription_id, GROUP_NAME, LB_NAME, ADDRESS_POOL_NAME)
    #Schdule the ProbeId will be used.
    construct_probe_id = '/subscriptions/{}''/resourceGroups/{}''/providers/Microsoft.Network''/loadBalancers/{}''/probes/{}'.format(subscription_id, GROUP_NAME, LB_NAME, PROBE_NAME)

    # Building a FrontEndIpPool
    publicIPAddress = network_client.public_ip_addresses.get(GROUP_NAME,PUBLICIP_NAME)
    frontend_ip_configurations = [{'name': FRONTEND_POOL_NAME,'private_ip_allocation_method': 'Dynamic','public_ip_address': {'id':publicIPAddress.id}}]
    print 'frontend_ip_configurations complated!',frontend_ip_configurations

    # Building a BackEnd address pool
    backend_address_pools = [{'name': ADDRESS_POOL_NAME}]
    print 'backend_address_pools complated!',backend_address_pools

    # Building a HealthProbe
    probes = [{'name': PROBE_NAME,'protocol': 'Http','port': 80,'interval_in_seconds': 15,'number_of_probes': 4,'request_path': 'healthprobe.aspx'}]

    # LoadBalancer rule
    load_balancing_rules = [{
        'name': LB_RULE_NAME,
        'protocol': 'tcp',
        'frontend_port': 80,
        'backend_port': 80,
        'idle_timeout_in_minutes': 4,
        'enable_floating_ip': False,
        'load_distribution': 'Default',
        'frontend_ip_configuration': {
            'id': construct_fip_id
        },
        'backend_address_pool': {
            'id': construct_bap_id
        },
        'probe': {
            'id': construct_probe_id
        }
    }]

    # Inbound NATRule1
    print('Create Inbound NATRule1')
    inbound_nat_rules = [{
        'name': NATRULE_NAME1,
        'protocol': 'tcp',
        'frontend_port': FRONTEND_PORT1,
        'backend_port': BACKEND_PORT,
        'enable_floating_ip': False,
        'idle_timeout_in_minutes': 4,
        'frontend_ip_configuration': {
            'id': construct_fip_id
        }
    }]
    #Inbound NATRule2
    print('Create Inbound NATRule2')
    inbound_nat_rules.append({
        'name': NATRULE_NAME2,
        'protocol': 'tcp',
        'frontend_port': FRONTEND_PORT2,
        'backend_port': BACKEND_PORT,
        'enable_floating_ip': False,
        'idle_timeout_in_minutes': 4,
        'frontend_ip_configuration': {
            'id': construct_fip_id
        }
    })
    # Creating Load Balancer
    print 'Creating Load Balancer'
    lb_creation = network_client.load_balancers.create_or_update(
        GROUP_NAME,
        LB_NAME,
        {
            'location': LOCATION,
            'frontend_ip_configurations': frontend_ip_configurations,
            'backend_address_pools': backend_address_pools,
            'probes': probes,
            'load_balancing_rules': load_balancing_rules,
            'inbound_nat_rules': inbound_nat_rules
        }
    )
    lb_info = lb_creation.result()
    backend_address_pools=lb_info.backend_address_pools
    return inbound_nat_rules,backend_address_pools

#-------------------------------------vm--------------------------------------

def create_nic(network_client):
    subnet_info = network_client.subnets.get(VNETGROUP_NAME,VNET_NAME,SUBNET_NAME)
    backend_info = backend_address_pools[0]
    inbound_info = network_client.inbound_nat_rules.get(GROUP_NAME, LB_NAME, NATRULE_NAME)
    #publicIPAddress = network_client.public_ip_addresses.get(GROUP_NAME,PUBLICIP_NAME)
    #nic_params = {'location': LOCATION,'ip_configurations': [{'name': NIC_CONFIG,'public_ip_address': publicIPAddress,'subnet': {'id': subnet_info.id}}]}
    #nic_params = {'location': LOCATION,'ip_configurations': [{'name': NIC_CONFIG,'subnet': {'id': subnet_info.id}}]}
    nic_params = {'location': LOCATION, 'ip_configurations': [{'name': NIC_CONFIG, 'subnet': {'id': subnet_info.id},'load_balancer_backend_address_pools': [{'id': backend_info.id}],'load_balancer_inbound_nat_rules': [{'id': inbound_info.id}]}]}
    creation_result = network_client.network_interfaces.create_or_update(GROUP_NAME,NIC_NAME,nic_params)
    return creation_result.result()

def create_vm(network_client, compute_client):
    nic = network_client.network_interfaces.get(GROUP_NAME, NIC_NAME)
    avset = compute_client.availability_sets.get(GROUP_NAME,AVSET_NAME)
    vm_parameters = {
        'location': LOCATION,
        'os_profile': {
            'computer_name':VM_NAME ,
            'admin_username': ADMIN_USER,
            'admin_password': ADMIN_PASSWORD
        },
        'hardware_profile': {
            'vm_size': VM_SIZE
        },
        'storage_profile': {
            'image_reference': {
                'publisher': PUBLISHER,
                'offer': OFFER,
                'sku': VM_SKU,
                'version': VM_VERSION
            }
        },
        'network_profile': {'network_interfaces': [{'id': nic.id}]},
        'availability_set': {'id': avset.id}
    }
    creation_result = compute_client.virtual_machines.create_or_update(GROUP_NAME,VM_NAME,vm_parameters)
    return creation_result.result()


#-------------------------------------feedbackvminfo to user--------------------------------------

def feedbackinfo():
    publicip = network_client.public_ip_addresses.get(GROUP_NAME,PUBLICIP_NAME).ip_address
    privateip = network_client.network_interface_ip_configurations.get(GROUP_NAME,NIC_NAME,NIC_CONFIG).private_ip_address
    privatemac = network_client.network_interfaces.get(GROUP_NAME,NIC_NAME).mac_address
    return VM_NAME,publicip,privateip,privatemac

# #############Loadbalance configuration################

LOCATION = 'chinanorth'   #list Beijing IDC    or Shanghai IDC (chinaeast)

VNETGROUP_NAME = 'RG-VNET-TEST-BJ'
VNET_NAME = 'TEST-BJ-Vnet'   #lsit
SUBNET_NAME = 'TEST-BJ-Subnet-1'  #list

GROUP_NAME = 'RG-TEST-BJ-LIZN'
AVSET_NAME = 'RG-TEST-BJ-LIZN'
PUBLICIP_NAME = 'RG-TEST-BJ-LIZN'
DOMAIN_NAME_LABEL = 'TEST-BJ-lizn'
PROBE_NAME = 'TEST-BJ-LIZN-PROBE1'
LB_RULE_NAME = 'TEST-BJ-LIZN-LBR1'
LB_NAME = 'TEST-BJ-LIZN-LBOUT'
ADDRESS_POOL_NAME = 'TEST-BJ-LIZN-PRIVATEPOOL'
FRONTEND_POOL_NAME = 'TEST-BJ-LIZN-PUBLICPOOL'

NATRULE_NAME1 = 'TEST-BJ-LIZN-NATR1'
NATRULE_NAME2 = 'TEST-BJ-LIZN-NATR2'
FRONTEND_PORT1 = 7788
FRONTEND_PORT2 = 8877
BACKEND_PORT = 3389
NATRULE_NAME = NATRULE_NAME1

##############VM configration###########################

NIC_NAME = 'TEST-BJ-LIZN-01-PrimaryNic'
VM_NAME = 'TEST-BJ-LIZN-01'
NIC_CONFIG = 'ipconfig1'
ADMIN_USER = 'admin'
ADMIN_PASSWORD = '1qaz2wsx'
VM_SIZE = 'Standard_D3'
PUBLISHER = 'MicrosoftWindowsServer'
OFFER = 'WindowsServer'
VM_SKU = '2012-R2-Datacenter'
VM_VERSION = 'latest'

subscription_id = '274aefb9-6bbd-4d5a-a871-50cdfac845d4'
credentials=azurearm_credentials()
resourcegroup_client = ResourceManagementClient(credentials, subscription_id,base_url=AZURE_CHINA_CLOUD.endpoints.resource_manager)
compute_client = ComputeManagementClient(credentials, subscription_id,base_url=AZURE_CHINA_CLOUD.endpoints.resource_manager)
network_client = NetworkManagementClient(credentials, subscription_id,base_url=AZURE_CHINA_CLOUD.endpoints.resource_manager)
storage_client = StorageManagementClient(credentials, subscription_id,base_url=AZURE_CHINA_CLOUD.endpoints.resource_manager)


# #################################################Vnet Generated########################################################

# print time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())), "vnet generation running;"
# create_vnet(network_client)
# print VNET_NAME,"vnet generated;",time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

# #Subnet Generated
# print time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())), "subnet generation running;"
# create_subnet(network_client)
# print SUBNET_NAME, "subnet generated;",time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))


#################################################Resource Group Generated##############################################
#Resource Group Generated
print time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())), "resource group generation running;"
create_resource_group(resourcegroup_client)
print  GROUP_NAME,"resource group generated;",time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

# Availability Set Generated
print time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())), "availability set generation running;"
create_availability_set(compute_client)
print AVSET_NAME,"availability set generated;",time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))


#################################################Loadbalance Generated#################################################
# Public IP Generated
print time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())), "publicip generation running;"
public_ip_info=create_public_ip_address(network_client)
print PUBLICIP_NAME, "publicip generated;",time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

# Loadbalance Generated
print time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())), "publicip generation running;"
inbound_nat_rules,backend_address_pools=lb_creation(
    subscription_id, GROUP_NAME,
    PUBLICIP_NAME,LB_NAME, LB_RULE_NAME,PROBE_NAME,FRONTEND_POOL_NAME,ADDRESS_POOL_NAME,NATRULE_NAME1,
    NATRULE_NAME2,FRONTEND_PORT1,FRONTEND_PORT2,BACKEND_PORT
)
print  LB_NAME,"loadbalance generated;",time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

###################################################VM Generated########################################################
#NIC Generated
print time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())), "nic generation running;"
create_nic(network_client)
print NIC_NAME,"nic generated;",time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

# VM Generated
print time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())), "vm generation running;"
sss=create_vm(network_client, compute_client)
print  VM_NAME,"vm generated;",time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

# feedbackinfo to user
print feedbackinfo()

NIC_NAME = 'TEST-BJ-LIZN-02-PrimaryNic'
VM_NAME = 'TEST-BJ-LIZN-02'
NATRULE_NAME = NATRULE_NAME2
#NIC Generated
print time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())), "nic generation running;"
create_nic(network_client)
print NIC_NAME,"nic generated;",time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

# VM Generated
print time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())), "vm generation running;"
sss=create_vm(network_client, compute_client)
print  VM_NAME,"vm generated;",time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

# feedbackinfo to user
print feedbackinfo()



