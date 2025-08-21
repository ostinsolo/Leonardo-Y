"""
Leonardo - Voice-First AI Assistant

A groundbreaking voice-first AI assistant with comprehensive safety validation,
sandbox execution, and continuous learning capabilities.

Architecture: wake → listen → understand → plan → validate → execute → verify → learn
"""

__version__ = "0.1.0"
__author__ = "Leonardo Development Team"

# Core imports
from .main import Leonardo
from .config import LeonardoConfig

__all__ = ["Leonardo", "LeonardoConfig"]
