#!/usr/bin/env python3
"""
Base Tool Class - Foundation for all Leonardo tools
Defines the interface and common functionality for tool implementations
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel
from pathlib import Path

from leonardo.config import LeonardoConfig


class ToolResult(BaseModel):
    """Standardized result from tool execution."""
    success: bool
    output: Any = None
    error: str = ""
    duration: float = 0.0
    metadata: Dict[str, Any] = {}
    tool_name: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration": self.duration,
            "metadata": self.metadata,
            "tool_name": self.tool_name
        }


class BaseTool(ABC):
    """
    Abstract base class for all Leonardo tools.
    
    Provides common functionality:
    - Logging and error handling
    - Execution timing
    - Configuration access
    - Safety checks
    """
    
    def __init__(self, config: LeonardoConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.initialized = False
        
    async def initialize(self) -> bool:
        """Initialize the tool. Override in subclasses if needed."""
        try:
            await self._setup()
            self.initialized = True
            self.logger.info(f"✅ {self.__class__.__name__} initialized")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize {self.__class__.__name__}: {e}")
            return False
    
    async def _setup(self) -> None:
        """Tool-specific setup logic. Override in subclasses."""
        pass
        
    async def shutdown(self) -> None:
        """Shutdown the tool. Override in subclasses if needed."""
        self.initialized = False
        self.logger.info(f"✅ {self.__class__.__name__} shutdown")
    
    async def execute(self, tool_name: str, args: Dict[str, Any]) -> ToolResult:
        """
        Execute the tool with given arguments.
        
        Args:
            tool_name: Name of the specific tool function to execute
            args: Arguments for the tool execution
            
        Returns:
            ToolResult with success/failure and output/error information
        """
        start_time = time.time()
        
        try:
            if not self.initialized:
                raise RuntimeError(f"{self.__class__.__name__} not initialized")
            
            # Log the execution attempt
            self.logger.info(f"🔧 Executing {tool_name} with args: {args}")
            
            # Pre-execution validation
            validation_error = await self._validate_args(tool_name, args)
            if validation_error:
                raise ValueError(validation_error)
            
            # Execute the specific tool
            output = await self._execute_tool(tool_name, args)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Create successful result
            result = ToolResult(
                success=True,
                output=output,
                duration=duration,
                tool_name=tool_name,
                metadata={
                    "tool_class": self.__class__.__name__,
                    "args": args
                }
            )
            
            self.logger.info(f"✅ {tool_name} completed in {duration:.2f}s")
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            self.logger.error(f"❌ {tool_name} failed after {duration:.2f}s: {error_msg}")
            
            return ToolResult(
                success=False,
                error=error_msg,
                duration=duration,
                tool_name=tool_name,
                metadata={
                    "tool_class": self.__class__.__name__,
                    "args": args
                }
            )
    
    @abstractmethod
    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        Execute the specific tool logic. Must be implemented by subclasses.
        
        Args:
            tool_name: Name of the tool function to execute
            args: Tool arguments
            
        Returns:
            Tool output (any type)
            
        Raises:
            Exception: If execution fails
        """
        pass
    
    async def _validate_args(self, tool_name: str, args: Dict[str, Any]) -> Optional[str]:
        """
        Validate tool arguments before execution.
        
        Args:
            tool_name: Name of the tool
            args: Arguments to validate
            
        Returns:
            Error message if validation fails, None if valid
        """
        # Basic validation - subclasses can override for specific validation
        if not isinstance(args, dict):
            return "Arguments must be a dictionary"
            
        return None  # Valid by default
    
    def _safe_file_path(self, path: str) -> Path:
        """
        Safely resolve file path within allowed directories.
        
        Args:
            path: File path string
            
        Returns:
            Resolved Path object
            
        Raises:
            ValueError: If path is outside allowed directories
        """
        try:
            path_obj = Path(path).resolve()
            
            # Define safe directories (configurable)
            safe_dirs = [
                Path.home(),
                Path.cwd(),
                self.config.data_dir if hasattr(self.config, 'data_dir') else Path.cwd()
            ]
            
            # Check if path is within safe directories
            for safe_dir in safe_dirs:
                try:
                    path_obj.relative_to(safe_dir.resolve())
                    return path_obj
                except ValueError:
                    continue
            
            raise ValueError(f"Path '{path}' is outside allowed directories")
            
        except Exception as e:
            raise ValueError(f"Invalid file path '{path}': {e}")
    
    def _get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value with fallback."""
        try:
            parts = key.split('.')
            value = self.config
            for part in parts:
                value = getattr(value, part, None)
                if value is None:
                    return default
            return value
        except Exception:
            return default
