"""
Data models for Azure resource provisioning requests and responses.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ResourceType(str, Enum):
    """Supported Azure resource types."""
    
    VIRTUAL_MACHINE = "virtual_machine"
    STORAGE_ACCOUNT = "storage_account"
    WEB_APP = "web_app"
    SQL_DATABASE = "sql_database"
    COSMOS_DB = "cosmos_db"
    VIRTUAL_NETWORK = "virtual_network"
    LOAD_BALANCER = "load_balancer"
    CONTAINER_INSTANCE = "container_instance"
    AKS_CLUSTER = "aks_cluster"
    COGNITIVE_SERVICE = "cognitive_service"
    MACHINE_LEARNING_WORKSPACE = "machine_learning_workspace"


class VMType(str, Enum):
    """Virtual machine types."""
    
    WINDOWS = "windows"
    LINUX = "linux"


class StorageAccountType(str, Enum):
    """Storage account types."""
    
    STANDARD_LRS = "Standard_LRS"
    STANDARD_GRS = "Standard_GRS"
    STANDARD_RAGRS = "Standard_RAGRS"
    PREMIUM_LRS = "Premium_LRS"


class WebAppRuntime(str, Enum):
    """Web app runtime stacks."""
    
    NODE_JS = "node"
    PYTHON = "python"
    DOTNET = "dotnet"
    JAVA = "java"
    PHP = "php"
    RUBY = "ruby"


class ProvisioningStatus(str, Enum):
    """Resource provisioning status."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResourceRequest(BaseModel):
    """Request model for resource provisioning."""
    
    resource_type: ResourceType
    name: str
    location: Optional[str] = None
    resource_group: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    user_id: str
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class VirtualMachineRequest(ResourceRequest):
    """Specific request model for virtual machine provisioning."""
    
    resource_type: ResourceType = ResourceType.VIRTUAL_MACHINE
    vm_type: VMType
    size: str = "Standard_B1s"
    admin_username: str
    admin_password: Optional[str] = None
    ssh_key: Optional[str] = None
    image_publisher: str = "MicrosoftWindowsServer"
    image_offer: str = "WindowsServer"
    image_sku: str = "2019-Datacenter"
    image_version: str = "latest"


class StorageAccountRequest(ResourceRequest):
    """Specific request model for storage account provisioning."""
    
    resource_type: ResourceType = ResourceType.STORAGE_ACCOUNT
    account_type: StorageAccountType = StorageAccountType.STANDARD_LRS
    access_tier: str = "Hot"
    enable_https_traffic_only: bool = True


class WebAppRequest(ResourceRequest):
    """Specific request model for web app provisioning."""
    
    resource_type: ResourceType = ResourceType.WEB_APP
    runtime: WebAppRuntime
    plan_name: Optional[str] = None
    plan_sku: str = "B1"
    app_settings: Optional[Dict[str, str]] = None


class ProvisioningResponse(BaseModel):
    """Response model for resource provisioning."""
    
    request_id: str
    status: ProvisioningStatus
    resource_id: Optional[str] = None
    resource_name: str
    resource_type: ResourceType
    location: str
    resource_group: str
    message: str
    error_details: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    tags: Optional[Dict[str, str]] = None


class ConversationContext(BaseModel):
    """Context for ongoing conversations."""
    
    user_id: str
    conversation_id: str
    current_request: Optional[ResourceRequest] = None
    pending_questions: List[str] = Field(default_factory=list)
    collected_parameters: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)


class BotMessage(BaseModel):
    """Message model for bot responses."""
    
    text: str
    attachments: Optional[List[Dict[str, Any]]] = None
    suggested_actions: Optional[List[Dict[str, Any]]] = None
    card_actions: Optional[List[Dict[str, Any]]] = None
    is_typing: bool = False 
