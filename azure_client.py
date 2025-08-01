"""
Azure client for managing resource provisioning operations.
"""

import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from azure.identity import ClientSecretCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.web import WebSiteManagementClient
from azure.mgmt.sql import SqlManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.containerservice import ContainerServiceManagementClient
from azure.mgmt.cosmosdb import CosmosDBManagementClient
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
from azure.mgmt.machinelearningservices import MachineLearningServicesMgmtClient

from .models import (
    ResourceRequest, ProvisioningResponse, ProvisioningStatus,
    ResourceType, VMType, StorageAccountType, WebAppRuntime
)
from .config import config


class AzureClient:
    """Azure client for resource provisioning operations."""
    
    def __init__(self):
        """Initialize the Azure client with credentials."""
        self.credential = ClientSecretCredential(
            tenant_id=config.azure.tenant_id,
            client_id=config.azure.client_id,
            client_secret=config.azure.client_secret
        )
        
        self.subscription_id = config.azure.subscription_id
        self.default_resource_group = config.azure.default_resource_group
        self.default_location = config.azure.default_location
        
        # Initialize management clients
        self.resource_client = ResourceManagementClient(
            credential=self.credential,
            subscription_id=self.subscription_id
        )
        
        self.compute_client = ComputeManagementClient(
            credential=self.credential,
            subscription_id=self.subscription_id
        )
        
        self.storage_client = StorageManagementClient(
            credential=self.credential,
            subscription_id=self.subscription_id
        )
        
        self.web_client = WebSiteManagementClient(
            credential=self.credential,
            subscription_id=self.subscription_id
        )
        
        self.sql_client = SqlManagementClient(
            credential=self.credential,
            subscription_id=self.subscription_id
        )
        
        self.network_client = NetworkManagementClient(
            credential=self.credential,
            subscription_id=self.subscription_id
        )
        
        self.container_instance_client = ContainerInstanceManagementClient(
            credential=self.credential,
            subscription_id=self.subscription_id
        )
        
        self.aks_client = ContainerServiceManagementClient(
            credential=self.credential,
            subscription_id=self.subscription_id
        )
        
        self.cosmos_client = CosmosDBManagementClient(
            credential=self.credential,
            subscription_id=self.subscription_id
        )
        
        self.cognitive_client = CognitiveServicesManagementClient(
            credential=self.credential,
            subscription_id=self.subscription_id
        )
        
        self.ml_client = MachineLearningServicesMgmtClient(
            credential=self.credential,
            subscription_id=self.subscription_id
        )
        
        self.logger = logging.getLogger(__name__)
    
    def ensure_resource_group(self, resource_group: str, location: str) -> bool:
        """Ensure the resource group exists."""
        try:
            self.resource_client.resource_groups.create_or_update(
                resource_group,
                {"location": location}
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to create resource group {resource_group}: {e}")
            return False
    
    def provision_virtual_machine(self, request: ResourceRequest) -> ProvisioningResponse:
        """Provision a virtual machine."""
        request_id = str(uuid.uuid4())
        resource_group = request.resource_group or self.default_resource_group
        location = request.location or self.default_location
        
        try:
            # Ensure resource group exists
            if not self.ensure_resource_group(resource_group, location):
                return ProvisioningResponse(
                    request_id=request_id,
                    status=ProvisioningStatus.FAILED,
                    resource_name=request.name,
                    resource_type=request.resource_type,
                    location=location,
                    resource_group=resource_group,
                    message="Failed to create resource group",
                    created_at=datetime.utcnow()
                )
            
            # Extract VM parameters
            vm_type = request.parameters.get("vm_type", VMType.WINDOWS)
            size = request.parameters.get("size", "Standard_B1s")
            admin_username = request.parameters.get("admin_username", "azureuser")
            admin_password = request.parameters.get("admin_password", "Azure123456!")
            
            # Create network interface
            nic_name = f"{request.name}-nic"
            vnet_name = f"{request.name}-vnet"
            subnet_name = f"{request.name}-subnet"
            
            # Create virtual network
            vnet_params = {
                "location": location,
                "address_space": {"address_prefixes": ["10.0.0.0/16"]},
                "subnets": [{
                    "name": subnet_name,
                    "address_prefix": "10.0.0.0/24"
                }]
            }
            
            vnet_poller = self.network_client.virtual_networks.begin_create_or_update(
                resource_group, vnet_name, vnet_params
            )
            vnet = vnet_poller.result()
            
            # Create network interface
            nic_params = {
                "location": location,
                "ip_configurations": [{
                    "name": "ipconfig1",
                    "subnet": {"id": vnet.subnets[0].id}
                }]
            }
            
            nic_poller = self.network_client.network_interfaces.begin_create_or_update(
                resource_group, nic_name, nic_params
            )
            nic = nic_poller.result()
            
            # Create VM
            if vm_type == VMType.WINDOWS:
                image_reference = {
                    "publisher": "MicrosoftWindowsServer",
                    "offer": "WindowsServer",
                    "sku": "2019-Datacenter",
                    "version": "latest"
                }
            else:
                image_reference = {
                    "publisher": "Canonical",
                    "offer": "UbuntuServer",
                    "sku": "18.04-LTS",
                    "version": "latest"
                }
            
            vm_params = {
                "location": location,
                "hardware_profile": {"vm_size": size},
                "storage_profile": {
                    "image_reference": image_reference,
                    "os_disk": {
                        "caching": "ReadWrite",
                        "managed_disk": {"storage_account_type": "Standard_LRS"}
                    }
                },
                "network_profile": {
                    "network_interfaces": [{"id": nic.id}]
                },
                "os_profile": {
                    "computer_name": request.name,
                    "admin_username": admin_username,
                    "admin_password": admin_password
                }
            }
            
            vm_poller = self.compute_client.virtual_machines.begin_create_or_update(
                resource_group, request.name, vm_params
            )
            vm = vm_poller.result()
            
            return ProvisioningResponse(
                request_id=request_id,
                status=ProvisioningStatus.COMPLETED,
                resource_id=vm.id,
                resource_name=request.name,
                resource_type=request.resource_type,
                location=location,
                resource_group=resource_group,
                message=f"Virtual machine '{request.name}' created successfully",
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                tags=request.tags
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create VM {request.name}: {e}")
            return ProvisioningResponse(
                request_id=request_id,
                status=ProvisioningStatus.FAILED,
                resource_name=request.name,
                resource_type=request.resource_type,
                location=location,
                resource_group=resource_group,
                message="Failed to create virtual machine",
                error_details=str(e),
                created_at=datetime.utcnow()
            )
    
    def provision_storage_account(self, request: ResourceRequest) -> ProvisioningResponse:
        """Provision a storage account."""
        request_id = str(uuid.uuid4())
        resource_group = request.resource_group or self.default_resource_group
        location = request.location or self.default_location
        
        try:
            # Ensure resource group exists
            if not self.ensure_resource_group(resource_group, location):
                return ProvisioningResponse(
                    request_id=request_id,
                    status=ProvisioningStatus.FAILED,
                    resource_name=request.name,
                    resource_type=request.resource_type,
                    location=location,
                    resource_group=resource_group,
                    message="Failed to create resource group",
                    created_at=datetime.utcnow()
                )
            
            # Extract storage parameters
            account_type = request.parameters.get("account_type", StorageAccountType.STANDARD_LRS)
            access_tier = request.parameters.get("access_tier", "Hot")
            enable_https = request.parameters.get("enable_https_traffic_only", True)
            
            storage_params = {
                "location": location,
                "sku": {"name": account_type},
                "kind": "StorageV2",
                "access_tier": access_tier,
                "enable_https_traffic_only": enable_https,
                "minimum_tls_version": "TLS1_2"
            }
            
            storage_poller = self.storage_client.storage_accounts.begin_create(
                resource_group, request.name, storage_params
            )
            storage_account = storage_poller.result()
            
            return ProvisioningResponse(
                request_id=request_id,
                status=ProvisioningStatus.COMPLETED,
                resource_id=storage_account.id,
                resource_name=request.name,
                resource_type=request.resource_type,
                location=location,
                resource_group=resource_group,
                message=f"Storage account '{request.name}' created successfully",
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                tags=request.tags
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create storage account {request.name}: {e}")
            return ProvisioningResponse(
                request_id=request_id,
                status=ProvisioningStatus.FAILED,
                resource_name=request.name,
                resource_type=request.resource_type,
                location=location,
                resource_group=resource_group,
                message="Failed to create storage account",
                error_details=str(e),
                created_at=datetime.utcnow()
            )
    
    def provision_web_app(self, request: ResourceRequest) -> ProvisioningResponse:
        """Provision a web app."""
        request_id = str(uuid.uuid4())
        resource_group = request.resource_group or self.default_resource_group
        location = request.location or self.default_location
        
        try:
            # Ensure resource group exists
            if not self.ensure_resource_group(resource_group, location):
                return ProvisioningResponse(
                    request_id=request_id,
                    status=ProvisioningStatus.FAILED,
                    resource_name=request.name,
                    resource_type=request.resource_type,
                    location=location,
                    resource_group=resource_group,
                    message="Failed to create resource group",
                    created_at=datetime.utcnow()
                )
            
            # Extract web app parameters
            runtime = request.parameters.get("runtime", WebAppRuntime.NODE_JS)
            plan_sku = request.parameters.get("plan_sku", "B1")
            plan_name = request.parameters.get("plan_name", f"{request.name}-plan")
            
            # Create app service plan
            plan_params = {
                "location": location,
                "sku": {"name": plan_sku, "tier": "Basic"}
            }
            
            plan_poller = self.web_client.app_service_plans.begin_create_or_update(
                resource_group, plan_name, plan_params
            )
            plan = plan_poller.result()
            
            # Create web app
            web_app_params = {
                "location": location,
                "server_farm_id": plan.id,
                "site_config": {
                    "app_settings": request.parameters.get("app_settings", {})
                }
            }
            
            web_app_poller = self.web_client.web_apps.begin_create_or_update(
                resource_group, request.name, web_app_params
            )
            web_app = web_app_poller.result()
            
            return ProvisioningResponse(
                request_id=request_id,
                status=ProvisioningStatus.COMPLETED,
                resource_id=web_app.id,
                resource_name=request.name,
                resource_type=request.resource_type,
                location=location,
                resource_group=resource_group,
                message=f"Web app '{request.name}' created successfully",
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                tags=request.tags
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create web app {request.name}: {e}")
            return ProvisioningResponse(
                request_id=request_id,
                status=ProvisioningStatus.FAILED,
                resource_name=request.name,
                resource_type=request.resource_type,
                location=location,
                resource_group=resource_group,
                message="Failed to create web app",
                error_details=str(e),
                created_at=datetime.utcnow()
            )
    
    def provision_resource(self, request: ResourceRequest) -> ProvisioningResponse:
        """Provision a resource based on the request type."""
        if request.resource_type == ResourceType.VIRTUAL_MACHINE:
            return self.provision_virtual_machine(request)
        elif request.resource_type == ResourceType.STORAGE_ACCOUNT:
            return self.provision_storage_account(request)
        elif request.resource_type == ResourceType.WEB_APP:
            return self.provision_web_app(request)
        else:
            return ProvisioningResponse(
                request_id=str(uuid.uuid4()),
                status=ProvisioningStatus.FAILED,
                resource_name=request.name,
                resource_type=request.resource_type,
                location=request.location or self.default_location,
                resource_group=request.resource_group or self.default_resource_group,
                message=f"Resource type {request.resource_type} not yet implemented",
                created_at=datetime.utcnow()
            )
    
    def list_resources(self, resource_group: Optional[str] = None) -> List[Dict[str, Any]]:
        """List resources in a resource group."""
        try:
            rg = resource_group or self.default_resource_group
            resources = self.resource_client.resources.list_by_resource_group(rg)
            
            return [
                {
                    "id": resource.id,
                    "name": resource.name,
                    "type": resource.type,
                    "location": resource.location,
                    "tags": resource.tags
                }
                for resource in resources
            ]
        except Exception as e:
            self.logger.error(f"Failed to list resources: {e}")
            return []
    
    def delete_resource(self, resource_id: str) -> bool:
        """Delete a resource by ID."""
        try:
            self.resource_client.resources.begin_delete_by_id(resource_id).result()
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete resource {resource_id}: {e}")
            return False 
