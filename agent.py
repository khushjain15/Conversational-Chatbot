"""
Main agent class for Azure resource provisioning.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .models import (
    ResourceRequest, ProvisioningResponse, ConversationContext,
    BotMessage, ProvisioningStatus
)
from .nlp_processor import NLPProcessor
from .azure_client import AzureClient
from .config import config


class AzureProvisioningAgent:
    """Main agent for Azure resource provisioning."""
    
    def __init__(self):
        """Initialize the agent."""
        self.nlp_processor = NLPProcessor()
        self.azure_client = AzureClient()
        self.conversation_contexts: Dict[str, ConversationContext] = {}
        self.logger = logging.getLogger(__name__)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, config.monitoring.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _get_conversation_context(self, user_id: str, conversation_id: str) -> ConversationContext:
        """Get or create conversation context."""
        context_key = f"{user_id}:{conversation_id}"
        
        if context_key not in self.conversation_contexts:
            self.conversation_contexts[context_key] = ConversationContext(
                user_id=user_id,
                conversation_id=conversation_id
            )
        
        # Update last activity
        self.conversation_contexts[context_key].last_activity = datetime.utcnow()
        return self.conversation_contexts[context_key]
    
    def _cleanup_old_contexts(self, max_age_hours: int = 24):
        """Clean up old conversation contexts."""
        cutoff_time = datetime.utcnow().replace(hour=datetime.utcnow().hour - max_age_hours)
        
        keys_to_remove = []
        for key, context in self.conversation_contexts.items():
            if context.last_activity < cutoff_time:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.conversation_contexts[key]
            self.logger.info(f"Cleaned up old conversation context: {key}")
    
    def _check_user_permissions(self, user_id: str) -> bool:
        """Check if user has permissions to provision resources."""
        # Check if user is in allowed users list
        if config.security.allowed_users and user_id not in config.security.allowed_users:
            return False
        
        # Admin users have full access
        if user_id in config.security.admin_users:
            return True
        
        # For now, allow all users if no restrictions are set
        return len(config.security.allowed_users) == 0
    
    async def process_message(self, user_id: str, conversation_id: str, message: str) -> BotMessage:
        """
        Process a user message and return a bot response.
        
        Args:
            user_id: The user's ID
            conversation_id: The conversation ID
            message: The user's message
            
        Returns:
            BotMessage: The bot's response
        """
        try:
            # Clean up old contexts
            self._cleanup_old_contexts()
            
            # Check user permissions
            if not self._check_user_permissions(user_id):
                return BotMessage(
                    text="Sorry, you don't have permission to provision Azure resources. Please contact your administrator."
                )
            
            # Get conversation context
            context = self._get_conversation_context(user_id, conversation_id)
            
            # Check for cancellation
            if message.lower() in ["cancel", "stop", "abort"]:
                context.current_request = None
                context.pending_questions = []
                context.collected_parameters = {}
                return BotMessage(text="Operation cancelled. How can I help you?")
            
            # Check for help request
            if message.lower() in ["help", "what can you do", "?"]:
                return self._get_help_message()
            
            # Check for resource listing
            if any(word in message.lower() for word in ["list", "show", "what", "resources"]):
                return await self._handle_list_resources(user_id)
            
            # If we have pending questions, handle the answer
            if context.pending_questions:
                return await self._handle_parameter_collection(context, message)
            
            # Parse the request
            request, missing_params = self.nlp_processor.parse_request(message, user_id)
            
            if request:
                # We have a complete request
                return await self._handle_complete_request(context, request)
            else:
                # We need more information
                context.pending_questions = missing_params
                return BotMessage(
                    text=f"I need some more information to create your resource:\n\n" + 
                         "\n".join(f"• {question}" for question in missing_params)
                )
        
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return BotMessage(
                text="Sorry, I encountered an error while processing your request. Please try again."
            )
    
    async def _handle_parameter_collection(self, context: ConversationContext, message: str) -> BotMessage:
        """Handle parameter collection for incomplete requests."""
        if not context.pending_questions:
            return BotMessage(text="I'm not sure what you're referring to. Could you please clarify?")
        
        # Store the answer
        current_question = context.pending_questions[0]
        context.collected_parameters[current_question] = message
        context.pending_questions.pop(0)
        
        # If we still have questions, ask the next one
        if context.pending_questions:
            return BotMessage(text=context.pending_questions[0])
        
        # Try to create a complete request from collected parameters
        # This is a simplified version - in a real implementation, you'd want more sophisticated
        # parameter mapping and validation
        try:
            # For now, just create a basic request
            request = ResourceRequest(
                resource_type=context.current_request.resource_type if context.current_request else None,
                name=context.collected_parameters.get("name", "unnamed-resource"),
                location=context.collected_parameters.get("location", config.azure.default_location),
                user_id=context.user_id
            )
            
            return await self._handle_complete_request(context, request)
        
        except Exception as e:
            self.logger.error(f"Error creating request from collected parameters: {e}")
            return BotMessage(
                text="I'm having trouble understanding the parameters. Please try again with a complete request."
            )
    
    async def _handle_complete_request(self, context: ConversationContext, request: ResourceRequest) -> BotMessage:
        """Handle a complete resource request."""
        # Store the request in context
        context.current_request = request
        
        # Generate confirmation message
        confirmation_text = self.nlp_processor.generate_response(request, "confirm")
        
        # Create suggested actions for confirmation
        suggested_actions = [
            {
                "type": "imBack",
                "title": "Yes, create it",
                "value": "yes"
            },
            {
                "type": "imBack",
                "title": "No, cancel",
                "value": "no"
            }
        ]
        
        return BotMessage(
            text=confirmation_text,
            suggested_actions=suggested_actions
        )
    
    async def _handle_list_resources(self, user_id: str) -> BotMessage:
        """Handle resource listing request."""
        try:
            resources = self.azure_client.list_resources()
            
            if not resources:
                return BotMessage(text="No resources found in the default resource group.")
            
            # Create a formatted list
            resource_list = []
            for resource in resources[:10]:  # Limit to 10 resources
                resource_list.append(
                    f"• {resource['name']} ({resource['type']}) - {resource['location']}"
                )
            
            text = f"Here are your resources:\n\n" + "\n".join(resource_list)
            
            if len(resources) > 10:
                text += f"\n\n... and {len(resources) - 10} more resources."
            
            return BotMessage(text=text)
        
        except Exception as e:
            self.logger.error(f"Error listing resources: {e}")
            return BotMessage(text="Sorry, I couldn't retrieve your resources. Please try again.")
    
    def _get_help_message(self) -> BotMessage:
        """Get help message with supported resource types."""
        help_text = """
🤖 **Azure Resource Provisioning Agent**

I can help you create various Azure resources. Here's what I support:

**Virtual Machines**
• Windows and Linux VMs
• Custom sizes and configurations
• Example: "Create a Windows VM with 4GB RAM"

**Storage Accounts**
• Blob, File, Queue, and Table storage
• Different redundancy options
• Example: "Create a storage account for my project"

**Web Apps**
• Node.js, Python, .NET, Java, PHP, Ruby
• App Service with custom plans
• Example: "Deploy a Node.js web app"

**Other Resources**
• SQL Databases
• Cosmos DB
• Virtual Networks
• Container Instances
• AKS Clusters
• And more!

**Commands**
• "help" - Show this message
• "list resources" - Show your existing resources
• "cancel" - Cancel current operation

Just tell me what you want to create! 🚀
        """
        
        return BotMessage(text=help_text.strip())
    
    async def confirm_and_provision(self, user_id: str, conversation_id: str, confirm: bool) -> BotMessage:
        """Confirm and provision a resource."""
        context = self._get_conversation_context(user_id, conversation_id)
        
        if not context.current_request:
            return BotMessage(text="No pending request to confirm. Please start a new request.")
        
        if not confirm:
            # Clear the context
            context.current_request = None
            context.pending_questions = []
            context.collected_parameters = {}
            return BotMessage(text="Request cancelled. How can I help you?")
        
        # Provision the resource
        try:
            # Send initial status
            status_message = self.nlp_processor.generate_response(context.current_request, "in_progress")
            
            # Provision the resource (this is synchronous for now, but could be async)
            response = self.azure_client.provision_resource(context.current_request)
            
            # Clear the context
            context.current_request = None
            context.pending_questions = []
            context.collected_parameters = {}
            
            # Return the result
            if response.status == ProvisioningStatus.COMPLETED:
                # Create a temporary request object for the response message
                temp_request = ResourceRequest(
                    resource_type=response.resource_type,
                    name=response.resource_name,
                    location=response.location,
                    user_id=context.user_id
                )
                return BotMessage(
                    text=self.nlp_processor.generate_response(temp_request, "completed")
                )
            else:
                return BotMessage(
                    text=f"❌ Failed to create resource: {response.message}"
                )
        
        except Exception as e:
            self.logger.error(f"Error provisioning resource: {e}")
            return BotMessage(
                text="Sorry, I encountered an error while creating your resource. Please try again."
            )
    
    async def get_provisioning_status(self, request_id: str) -> Optional[ProvisioningResponse]:
        """Get the status of a provisioning request."""
        # In a real implementation, you'd store requests in a database
        # and retrieve their status. For now, we'll return None.
        return None 
