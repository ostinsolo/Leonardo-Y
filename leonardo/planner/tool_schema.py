"""
Tool call schemas and data structures.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class RiskLevel(str, Enum):
    """Risk levels for tool execution."""
    SAFE = "safe"
    REVIEW = "review"
    CONFIRM = "confirm"
    OWNER_ROOT = "owner_root"


class ToolCall(BaseModel):
    """Tool call structure with constrained JSON schema."""
    
    tool: str = Field(..., description="Tool identifier")
    args: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Metadata")
    
    @property
    def risk_level(self) -> RiskLevel:
        """Get risk level from metadata."""
        return RiskLevel(self.meta.get("risk", "safe"))
    
    @property
    def command_id(self) -> Optional[str]:
        """Get command ID from metadata."""
        return self.meta.get("command_id")


class PlanResult(BaseModel):
    """Result of LLM planning."""
    
    tool_call: Dict[str, Any] = Field(..., description="Generated tool call")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    reasoning: str = Field(..., description="Planning reasoning")
    alternatives: List[Dict[str, Any]] = Field(default_factory=list, description="Alternative plans")
    
    def to_tool_call(self) -> ToolCall:
        """Convert to ToolCall object."""
        return ToolCall(**self.tool_call)
