#!/usr/bin/env python3
"""
Response Tool - Handles conversational responses and general communication
Most commonly used tool for natural conversation flow
"""

from typing import Dict, Any
from .base_tool import BaseTool


class ResponseTool(BaseTool):
    """Tool for generating conversational responses."""
    
    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Execute conversational response."""
        
        if tool_name == "respond":
            return self._generate_response(args)
        else:
            raise ValueError(f"Unknown response tool: {tool_name}")
    
    def _generate_response(self, args: Dict[str, Any]) -> str:
        """Generate a conversational response."""
        message = args.get("message", "")
        response_type = args.get("type", "conversational")
        context = args.get("context", {})
        
        if not message:
            return "I'm here to help! What would you like to know?"
        
        # Handle different response types
        if response_type == "greeting":
            return self._generate_greeting_response(message, context)
        elif response_type == "farewell":
            return self._generate_farewell_response(message, context)
        elif response_type == "acknowledgment":
            return self._generate_acknowledgment_response(message, context)
        elif response_type == "clarification":
            return self._generate_clarification_response(message, context)
        else:
            return self._generate_conversational_response(message, context)
    
    def _generate_greeting_response(self, message: str, context: Dict[str, Any]) -> str:
        """Generate greeting responses."""
        greetings = [
            "Hello! I'm Leonardo, your voice-first AI assistant. How can I help you today?",
            "Hi there! I'm ready to assist you with anything you need.",
            "Good to hear from you! What can I do for you?",
            "Hello! I'm here and ready to help. What's on your mind?"
        ]
        
        # Use context to personalize if available
        user_name = context.get("user_name", "")
        if user_name:
            return f"Hello {user_name}! I'm Leonardo, your AI assistant. How can I help you today?"
        
        # Simple context-based selection (could be enhanced with ML)
        message_lower = message.lower()
        if any(word in message_lower for word in ['good morning', 'morning']):
            return "Good morning! I hope you're having a great start to your day. How can I assist you?"
        elif any(word in message_lower for word in ['good evening', 'evening']):
            return "Good evening! I hope you've had a productive day. What can I help you with?"
        
        return greetings[0]  # Default greeting
    
    def _generate_farewell_response(self, message: str, context: Dict[str, Any]) -> str:
        """Generate farewell responses."""
        farewells = [
            "Goodbye! Feel free to ask me anything anytime.",
            "Take care! I'm always here when you need assistance.",
            "See you later! Don't hesitate to reach out if you need help.",
            "Have a great day! I'll be here whenever you need me."
        ]
        
        message_lower = message.lower()
        if any(word in message_lower for word in ['good night', 'goodnight']):
            return "Good night! Sleep well and have pleasant dreams!"
        elif any(word in message_lower for word in ['see you', 'talk later']):
            return "Looking forward to talking with you again soon!"
        
        return farewells[0]
    
    def _generate_acknowledgment_response(self, message: str, context: Dict[str, Any]) -> str:
        """Generate acknowledgment responses."""
        acknowledgments = [
            "I understand. Is there anything specific you'd like me to help you with?",
            "Got it! What would you like to do next?",
            "Understood. How can I assist you further?",
            "I see. What else can I help you with today?"
        ]
        
        if "thank" in message.lower():
            return "You're very welcome! I'm glad I could help. Is there anything else you need?"
        
        return acknowledgments[0]
    
    def _generate_clarification_response(self, message: str, context: Dict[str, Any]) -> str:
        """Generate clarification responses."""
        clarifications = [
            "I'm not sure I understood that completely. Could you please clarify or ask in a different way?",
            "Could you provide a bit more detail about what you're looking for?",
            "I want to make sure I help you correctly. Can you rephrase that or give me more context?",
            "I'm here to help, but I need a bit more information. What specifically would you like me to do?"
        ]
        
        return clarifications[0]
    
    def _generate_conversational_response(self, message: str, context: Dict[str, Any]) -> str:
        """Generate intelligent conversational responses using the actual message content."""
        message_lower = message.lower()
        
        # 🚀 INTELLIGENT RESPONSE: Use the actual message content instead of generic templates
        # This preserves intelligent responses from other tools (like DeepSearcher)
        
        # Handle common conversational topics with generic queries only
        if any(word in message_lower for word in ['how are you', 'how do you do']):
            return "I'm doing well, thank you for asking! I'm ready to help you with whatever you need. How are you doing today?"
        
        elif any(word in message_lower for word in ['what can you do', 'what are you capable of']):
            return ("I can help you with many things! I can check the weather, search the web, manage files, "
                   "perform calculations, get system information, and have conversations with you. "
                   "I also remember our previous conversations. What would you like to try?")
        
        elif any(word in message_lower for word in ['tell me about yourself', 'who are you']):
            return ("I'm Leonardo, your voice-first AI assistant. I'm designed to be helpful, conversational, "
                   "and to remember our interactions. I can assist with information, tasks, and just chat "
                   "whenever you need. What interests you most about what I can do?")
        
        elif any(word in message_lower for word in ['interesting', 'cool', 'awesome', 'great']):
            return "I'm glad you find that interesting! Is there anything specific you'd like to explore or learn more about?"
        
        # 🔧 FIX: Only return generic help for explicit help requests
        elif message_lower.strip() in ['help', 'assist', 'support', 'what can you help with', 'help me']:
            return ("I'm here to help! You can ask me to check the weather, search for information, "
                   "manage files, do calculations, get the time or date, or just have a conversation. "
                   "What would you like assistance with?")
        
        elif any(word in message_lower for word in ['busy', 'working', 'stressed']):
            return ("It sounds like you have a lot going on. I'm here to help make things easier. "
                   "Is there anything I can assist you with to lighten your load?")
        
        elif any(word in message_lower for word in ['bored', 'nothing to do']):
            return ("I can help with that! We could have an interesting conversation, I could search for "
                   "something fun to read about, or help you discover something new. What kind of things interest you?")
        
        else:
            # 🎯 BREAKTHROUGH FIX: Return the actual intelligent message content instead of generic response
            # This preserves DeepSearcher research, contextual responses, and other intelligent tool outputs
            if len(message.strip()) > 50:  # Likely intelligent content
                return message
            else:
                # For short messages, add minimal context
                return f"{message} Is there anything specific you'd like to know more about?"
    
    async def _validate_args(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Validate response tool arguments."""
        if tool_name == "respond":
            if "message" not in args:
                return "Response tool requires 'message' argument"
        
        return None  # Valid
