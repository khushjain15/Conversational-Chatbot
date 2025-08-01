"""
Configuration management for the Azure Resource Provisioning Agent.
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, Field


class AzureConfig(BaseSettings):
    """Azure-specific configuration settings."""
    
    subscription_id: str = Field(..., env="AZURE_SUBSCRIPTION_ID")
    tenant_id: str = Field(..., env="AZURE_TENANT_ID")
    client_id: str = Field(..., env="AZURE_CLIENT_ID")
    client_secret: str = Field(..., env="AZURE_CLIENT_SECRET")
    
    default_resource_group: str = Field("azure-provisioning-rg", env="DEFAULT_RESOURCE_GROUP")
    default_location: str = Field("East US", env="DEFAULT_LOCATION")


class BotConfig(BaseSettings):
    """Bot Framework configuration settings."""
    
    app_id: str = Field(..., env="BOT_APP_ID")
    app_password: str = Field(..., env="BOT_APP_PASSWORD")
    endpoint: str = Field(..., env="BOT_ENDPOINT")


class SecurityConfig(BaseSettings):
    """Security and access control configuration."""
    
    allowed_users: List[str] = Field(default_factory=list)
    admin_users: List[str] = Field(default_factory=list)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Parse comma-separated user lists
        if isinstance(self.allowed_users, str):
            self.allowed_users = [u.strip() for u in self.allowed_users.split(",") if u.strip()]
        if isinstance(self.admin_users, str):
            self.admin_users = [u.strip() for u in self.admin_users.split(",") if u.strip()]


class MonitoringConfig(BaseSettings):
    """Monitoring and logging configuration."""
    
    application_insights_connection_string: Optional[str] = Field(None, env="APPLICATION_INSIGHTS_CONNECTION_STRING")
    log_level: str = Field("INFO", env="LOG_LEVEL")


class Config(BaseSettings):
    """Main configuration class that combines all settings."""
    
    azure: AzureConfig = Field(default_factory=AzureConfig)
    bot: BotConfig = Field(default_factory=BotConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global configuration instance
config = Config() 
