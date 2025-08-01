"""
Microsoft Teams bot integration for Azure resource provisioning.
"""

import asyncio
import logging
from typing import Dict, Any

from botbuilder.core import (
    ActivityHandler, TurnContext, MessageFactory,
    CardFactory, SuggestedActions
)
from botbuilder.schema import (
    Activity, ActivityTypes, ChannelAccount,
    SuggestedActions as SuggestedActionsSchema
)

from .agent import AzureProvisioningAgent
from .models import BotMessage
from .config import config


class AzureProvisioningBot(ActivityHandler):
    """Teams bot for Azure resource provisioning."""
    
    def __init__(self):
        """Initialize the bot."""
        self.agent = AzureProvisioningAgent()
        self.logger = logging.getLogger(__name__)
    
    async def on_message_activity(self, turn_context: TurnContext):
        """Handle incoming message activities."""
        try:
            # Get user and conversation info
            user_id = turn_context.activity.from_property.id
            conversation_id = turn_context.activity.conversation.id
            message_text = turn_context.activity.text
            
            self.logger.info(f"Received message from {user_id}: {message_text}")
            
            # Process the message with our agent
            response = await self.agent.process_message(user_id, conversation_id, message_text)
            
            # Handle confirmation responses
            if message_text.lower() in ["yes", "no"]:
                confirm = message_text.lower() == "yes"
                response = await self.agent.confirm_and_provision(user_id, conversation_id, confirm)
            
            # Send the response
            await self._send_response(turn_context, response)
            
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            await turn_context.send_activity(
                MessageFactory.text("Sorry, I encountered an error. Please try again.")
            )
    
    async def on_members_added_activity(
        self, members_added: [ChannelAccount], turn_context: TurnContext
    ):
        """Handle when members are added to the conversation."""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                welcome_message = BotMessage(
                    text="👋 Welcome! I'm your Azure Resource Provisioning Assistant.\n\n"
                         "I can help you create various Azure resources like:\n"
                         "• Virtual Machines\n"
                         "• Storage Accounts\n"
                         "• Web Apps\n"
                         "• Databases\n"
                         "• And more!\n\n"
                         "Just tell me what you want to create, or type 'help' for more information."
                )
                await self._send_response(turn_context, welcome_message)
    
    async def _send_response(self, turn_context: TurnContext, bot_message: BotMessage):
        """Send a response to the user."""
        try:
            if bot_message.is_typing:
                await turn_context.send_activities([
                    Activity(type=ActivityTypes.typing)
                ])
            
            # Create the main message
            message = MessageFactory.text(bot_message.text)
            
            # Add suggested actions if provided
            if bot_message.suggested_actions:
                actions = []
                for action in bot_message.suggested_actions:
                    actions.append(
                        SuggestedActionsSchema(
                            title=action["title"],
                            type=action["type"],
                            value=action["value"]
                        )
                    )
                message.suggested_actions = SuggestedActions(actions=actions)
            
            # Send the message
            await turn_context.send_activity(message)
            
            # Send attachments if provided
            if bot_message.attachments:
                for attachment in bot_message.attachments:
                    if attachment.get("type") == "card":
                        card = CardFactory.adaptive_card(attachment["content"])
                        await turn_context.send_activity(MessageFactory.attachment(card))
            
        except Exception as e:
            self.logger.error(f"Error sending response: {e}")
            await turn_context.send_activity(
                MessageFactory.text("Sorry, I couldn't send the response. Please try again.")
            )
    
    async def on_typing_activity(self, turn_context: TurnContext):
        """Handle typing activities."""
        # You can implement typing indicators here if needed
        pass
    
    async def on_end_of_conversation_activity(self, turn_context: TurnContext):
        """Handle end of conversation activities."""
        # Clean up any conversation state if needed
        pass 
