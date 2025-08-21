"""
Validation Wall Results and Risk Assessment
Core data structures for validation decisions
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class RiskLevel(str, Enum):
    """Risk levels for tool execution."""
    SAFE = "safe"           # Auto-execute, no confirmation
    REVIEW = "review"       # Preview before execution  
    CONFIRM = "confirm"     # User confirmation required
    OWNER_ROOT = "owner_root"  # Critical operations, owner passphrase
    BLOCKED = "blocked"     # Dangerous, execution denied


class ValidationStage(str, Enum):
    """Validation wall stages."""
    SCHEMA = "schema"       # JSON schema validation
    POLICY = "policy"       # Policy engine assessment
    LINTER = "linter"       # Code analysis and safety checks
    AUDIT = "audit"         # Logging and compliance
    VERIFICATION = "verification"  # Post-execution verification (NLI + post-conditions)


class ValidationError(BaseModel):
    """Individual validation error."""
    stage: ValidationStage
    code: str
    message: str
    severity: RiskLevel
    details: Dict[str, Any] = Field(default_factory=dict)
    
    def __str__(self) -> str:
        return f"[{self.stage.upper()}] {self.code}: {self.message}"


class ValidationResult(BaseModel):
    """Complete validation wall result."""
    
    # Validation decision
    approved: bool = Field(..., description="Whether tool execution is approved")
    risk_level: RiskLevel = Field(..., description="Final assessed risk level")
    
    # Validation details
    tool_name: str = Field(..., description="Tool being validated")
    errors: List[ValidationError] = Field(default_factory=list, description="Validation errors")
    warnings: List[ValidationError] = Field(default_factory=list, description="Validation warnings")
    
    # Policy decisions
    requires_confirmation: bool = Field(default=False, description="User confirmation required")
    requires_dry_run: bool = Field(default=False, description="Dry run required before execution")
    execution_timeout: Optional[int] = Field(default=None, description="Max execution time seconds")
    
    # Audit trail
    validation_id: str = Field(..., description="Unique validation identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="Validation timestamp")
    stages_passed: List[ValidationStage] = Field(default_factory=list, description="Completed stages")
    
    # Additional context
    user_id: str = Field(default="default", description="User requesting tool execution")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional validation data")
    
    @property
    def is_safe(self) -> bool:
        """Check if tool execution is safe (no user interaction required)."""
        return self.approved and self.risk_level == RiskLevel.SAFE
    
    @property
    def is_blocked(self) -> bool:
        """Check if tool execution is completely blocked."""
        return not self.approved or self.risk_level == RiskLevel.BLOCKED
    
    @property
    def needs_user_approval(self) -> bool:
        """Check if user approval is required."""
        return self.approved and self.risk_level in [RiskLevel.CONFIRM, RiskLevel.OWNER_ROOT]
    
    def add_error(self, stage: ValidationStage, code: str, message: str, 
                  severity: RiskLevel = RiskLevel.BLOCKED, **details):
        """Add validation error."""
        error = ValidationError(
            stage=stage,
            code=code, 
            message=message,
            severity=severity,
            details=details
        )
        self.errors.append(error)
        
        # Update approval status based on error severity
        if severity == RiskLevel.BLOCKED:
            self.approved = False
            self.risk_level = RiskLevel.BLOCKED
    
    def add_warning(self, stage: ValidationStage, code: str, message: str,
                   severity: RiskLevel = RiskLevel.REVIEW, **details):
        """Add validation warning."""
        warning = ValidationError(
            stage=stage,
            code=code,
            message=message, 
            severity=severity,
            details=details
        )
        self.warnings.append(warning)
        
        # Elevate risk level if needed
        if self.risk_level == RiskLevel.SAFE and severity in [RiskLevel.REVIEW, RiskLevel.CONFIRM]:
            self.risk_level = severity
    
    def get_summary(self) -> str:
        """Get human-readable validation summary."""
        if self.is_blocked:
            return f"🚫 BLOCKED: {len(self.errors)} critical errors"
        elif self.needs_user_approval:
            return f"⚠️ {self.risk_level.upper()}: User approval required"
        elif self.warnings:
            return f"✅ APPROVED with {len(self.warnings)} warnings"
        else:
            return "✅ APPROVED: Safe for execution"
    
    def get_error_summary(self) -> str:
        """Get summary of all errors and warnings."""
        lines = []
        
        if self.errors:
            lines.append(f"🚫 Errors ({len(self.errors)}):")
            for error in self.errors:
                lines.append(f"  • {error}")
        
        if self.warnings:
            lines.append(f"⚠️ Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                lines.append(f"  • {warning}")
        
        return "\n".join(lines) if lines else "No issues found"
