"""
Natural Language Processing module for understanding user requests
and extracting resource provisioning parameters.
"""

import re
import spacy
from typing import Dict, List, Optional, Tuple, Any
from .models import ResourceType, VMType, StorageAccountType, WebAppRuntime, ResourceRequest


class NLPProcessor:
    """Natural language processor for understanding resource provisioning requests."""
    
    def __init__(self):
        """Initialize the NLP processor."""
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            # Fallback to basic processing if spaCy model is not available
            self.nlp = None
        
        # Keywords for different resource types
        self.resource_keywords = {
            ResourceType.VIRTUAL_MACHINE: [
                "vm", "virtual machine", "server", "instance", "compute",
                "windows server", "linux server", "ubuntu", "centos"
            ],
            ResourceType.STORAGE_ACCOUNT: [
                "storage", "storage account", "blob", "file storage",
                "queue", "table storage", "data storage"
            ],
            ResourceType.WEB_APP: [
                "web app", "app service", "website", "web application",
                "node.js", "python", "dotnet", "java", "php", "ruby"
            ],
            ResourceType.SQL_DATABASE: [
                "sql", "database", "sql database", "sql server",
                "relational database", "rdbms"
            ],
            ResourceType.COSMOS_DB: [
                "cosmos", "cosmos db", "nosql", "document database",
                "mongodb", "cassandra", "table api"
            ],
            ResourceType.VIRTUAL_NETWORK: [
                "vnet", "virtual network", "network", "subnet",
                "network security group", "nsg"
            ],
            ResourceType.CONTAINER_INSTANCE: [
                "container", "aci", "container instance", "docker",
                "containerized", "microservice"
            ],
            ResourceType.AKS_CLUSTER: [
                "aks", "kubernetes", "k8s", "container cluster",
                "orchestration", "microservices"
            ]
        }
        
        # VM size patterns
        self.vm_size_patterns = {
            "basic": ["b1s", "b1ms", "b2s", "b2ms"],
            "standard": ["d2s", "d4s", "d8s", "d16s"],
            "memory_optimized": ["e2s", "e4s", "e8s", "e16s"],
            "compute_optimized": ["f2s", "f4s", "f8s", "f16s"]
        }
        
        # Location patterns
        self.location_patterns = {
            "east_us": ["east us", "eastus", "virginia"],
            "west_us": ["west us", "westus", "california"],
            "central_us": ["central us", "centralus", "iowa"],
            "north_europe": ["north europe", "northeurope", "ireland"],
            "west_europe": ["west europe", "westeurope", "netherlands"]
        }
    
    def extract_resource_type(self, text: str) -> Optional[ResourceType]:
        """Extract the resource type from user input."""
        text_lower = text.lower()
        
        for resource_type, keywords in self.resource_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return resource_type
        
        return None
    
    def extract_vm_parameters(self, text: str) -> Dict[str, Any]:
        """Extract VM-specific parameters from text."""
        text_lower = text.lower()
        parameters = {}
        
        # Extract VM type
        if any(word in text_lower for word in ["windows", "win"]):
            parameters["vm_type"] = VMType.WINDOWS
        elif any(word in text_lower for word in ["linux", "ubuntu", "centos", "debian"]):
            parameters["vm_type"] = VMType.LINUX
        
        # Extract size
        for size_category, sizes in self.vm_size_patterns.items():
            for size in sizes:
                if size in text_lower:
                    parameters["size"] = f"Standard_{size.upper()}"
                    break
        
        # Extract RAM
        ram_match = re.search(r'(\d+)\s*(gb|gigabytes?|g)', text_lower)
        if ram_match:
            ram_gb = int(ram_match.group(1))
            # Map RAM to appropriate VM size
            if ram_gb <= 1:
                parameters["size"] = "Standard_B1s"
            elif ram_gb <= 2:
                parameters["size"] = "Standard_B2s"
            elif ram_gb <= 4:
                parameters["size"] = "Standard_D2s_v3"
            elif ram_gb <= 8:
                parameters["size"] = "Standard_D4s_v3"
            elif ram_gb <= 16:
                parameters["size"] = "Standard_D8s_v3"
            else:
                parameters["size"] = "Standard_D16s_v3"
        
        # Extract admin username
        username_match = re.search(r'username[:\s]+(\w+)', text_lower)
        if username_match:
            parameters["admin_username"] = username_match.group(1)
        
        return parameters
    
    def extract_storage_parameters(self, text: str) -> Dict[str, Any]:
        """Extract storage account parameters from text."""
        text_lower = text.lower()
        parameters = {}
        
        # Extract account type
        if "premium" in text_lower:
            parameters["account_type"] = StorageAccountType.PREMIUM_LRS
        elif "geo" in text_lower or "redundant" in text_lower:
            parameters["account_type"] = StorageAccountType.STANDARD_GRS
        else:
            parameters["account_type"] = StorageAccountType.STANDARD_LRS
        
        # Extract access tier
        if "cool" in text_lower:
            parameters["access_tier"] = "Cool"
        else:
            parameters["access_tier"] = "Hot"
        
        return parameters
    
    def extract_webapp_parameters(self, text: str) -> Dict[str, Any]:
        """Extract web app parameters from text."""
        text_lower = text.lower()
        parameters = {}
        
        # Extract runtime
        if "node" in text_lower or "javascript" in text_lower:
            parameters["runtime"] = WebAppRuntime.NODE_JS
        elif "python" in text_lower:
            parameters["runtime"] = WebAppRuntime.PYTHON
        elif "dotnet" in text_lower or "c#" in text_lower or ".net" in text_lower:
            parameters["runtime"] = WebAppRuntime.DOTNET
        elif "java" in text_lower:
            parameters["runtime"] = WebAppRuntime.JAVA
        elif "php" in text_lower:
            parameters["runtime"] = WebAppRuntime.PHP
        elif "ruby" in text_lower:
            parameters["runtime"] = WebAppRuntime.RUBY
        
        # Extract plan SKU
        if "basic" in text_lower:
            parameters["plan_sku"] = "B1"
        elif "standard" in text_lower:
            parameters["plan_sku"] = "S1"
        elif "premium" in text_lower:
            parameters["plan_sku"] = "P1v2"
        else:
            parameters["plan_sku"] = "F1"  # Free tier
        
        return parameters
    
    def extract_location(self, text: str) -> Optional[str]:
        """Extract location from text."""
        text_lower = text.lower()
        
        for location_name, patterns in self.location_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    return location_name.replace("_", " ").title()
        
        return None
    
    def extract_name(self, text: str) -> Optional[str]:
        """Extract resource name from text."""
        # Look for patterns like "name it X" or "call it X"
        name_patterns = [
            r'name\s+(?:it\s+)?([a-zA-Z0-9\-_]+)',
            r'call\s+(?:it\s+)?([a-zA-Z0-9\-_]+)',
            r'named\s+([a-zA-Z0-9\-_]+)',
            r'called\s+([a-zA-Z0-9\-_]+)'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def extract_tags(self, text: str) -> Dict[str, str]:
        """Extract tags from text."""
        tags = {}
        text_lower = text.lower()
        
        # Common tag patterns
        if "production" in text_lower:
            tags["environment"] = "production"
        elif "development" in text_lower or "dev" in text_lower:
            tags["environment"] = "development"
        elif "test" in text_lower or "testing" in text_lower:
            tags["environment"] = "testing"
        
        if "project" in text_lower:
            # Extract project name
            project_match = re.search(r'project[:\s]+([a-zA-Z0-9\-_]+)', text_lower)
            if project_match:
                tags["project"] = project_match.group(1)
        
        return tags
    
    def parse_request(self, text: str, user_id: str) -> Tuple[Optional[ResourceRequest], List[str]]:
        """
        Parse user input and extract resource request parameters.
        
        Returns:
            Tuple of (ResourceRequest, List of missing parameters)
        """
        text_lower = text.lower()
        missing_params = []
        
        # Extract resource type
        resource_type = self.extract_resource_type(text)
        if not resource_type:
            return None, ["I couldn't determine what type of resource you want to create. Please specify the resource type."]
        
        # Extract name
        name = self.extract_name(text)
        if not name:
            missing_params.append("What would you like to name this resource?")
        
        # Extract location
        location = self.extract_location(text)
        if not location:
            missing_params.append("Which Azure region would you prefer?")
        
        # Extract resource-specific parameters
        parameters = {}
        if resource_type == ResourceType.VIRTUAL_MACHINE:
            vm_params = self.extract_vm_parameters(text)
            parameters.update(vm_params)
            
            if "vm_type" not in vm_params:
                missing_params.append("What type of VM would you like? (Windows or Linux)")
            if "admin_username" not in vm_params:
                missing_params.append("What admin username would you like to use?")
        
        elif resource_type == ResourceType.STORAGE_ACCOUNT:
            storage_params = self.extract_storage_parameters(text)
            parameters.update(storage_params)
        
        elif resource_type == ResourceType.WEB_APP:
            webapp_params = self.extract_webapp_parameters(text)
            parameters.update(webapp_params)
            
            if "runtime" not in webapp_params:
                missing_params.append("What runtime would you like? (Node.js, Python, .NET, Java, PHP, Ruby)")
        
        # Extract tags
        tags = self.extract_tags(text)
        
        # Create request if we have enough information
        if not missing_params:
            request = ResourceRequest(
                resource_type=resource_type,
                name=name,
                location=location,
                parameters=parameters,
                tags=tags,
                user_id=user_id
            )
            return request, []
        
        return None, missing_params
    
    def generate_response(self, request: ResourceRequest, status: str) -> str:
        """Generate a human-readable response for the request."""
        resource_name = request.resource_type.value.replace("_", " ").title()
        
        if status == "confirm":
            return f"I'll create a {resource_name} named '{request.name}' in {request.location}. Is this correct?"
        elif status == "in_progress":
            return f"Creating your {resource_name} '{request.name}' in {request.location}. This may take a few minutes."
        elif status == "completed":
            return f"✅ Your {resource_name} '{request.name}' has been successfully created in {request.location}!"
        elif status == "failed":
            return f"❌ Sorry, I couldn't create the {resource_name}. Please try again or contact support."
        
        return f"Processing your {resource_name} request..." 
