"""
Validation Wall - Multi-Tier Security Validation System
Main coordinator for Leonardo's safety validation pipeline

Architecture:
Tier 1: Schema Validation → JSON schema compliance
Tier 2: Policy Engine → Risk assessment, allowlists, rate limits  
Tier 3: Code Linter → AST analysis, dangerous code detection
Tier 4: Audit Logger → Complete compliance trail
Tier 5: Verification Layer → NLI claim verification + post-condition checking

This system ensures NO dangerous operations reach the sandbox executor.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from .validation_result import ValidationResult, ValidationStage, RiskLevel
from .schema_validator import SchemaValidator
from .policy_engine import PolicyEngine
from .linters import CodeLinter
from .audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class ValidationWall:
    """
    Multi-tier validation wall for tool execution safety.
    
    This is the critical security component that stands between
    the LLM planner and the sandbox executor.
    """
    
    def __init__(self, audit_dir: Optional[str] = None):
        # Initialize all validation tiers
        self.schema_validator = SchemaValidator()
        self.policy_engine = PolicyEngine()
        self.code_linter = CodeLinter()
        self.audit_logger = AuditLogger(audit_dir)
        
        # Verification layer will be lazily initialized
        self.verification_layer = None
        self._verification_initialized = False
        
        # Validation statistics
        self.stats = {
            "total_validations": 0,
            "schema_failures": 0,
            "policy_failures": 0,
            "linter_failures": 0,
            "verification_failures": 0,
            "approvals": 0,
            "blocks": 0,
            "confirmations_required": 0
        }
        
        logger.info("🛡️ Validation Wall initialized - Multi-tier security active")
        logger.info("   Tier 1: JSON Schema Validation ✅")
        logger.info("   Tier 2: Policy Engine ✅") 
        logger.info("   Tier 3: Code Linter ✅")
        logger.info("   Tier 4: Audit Logger ✅")
        logger.info("   Tier 5: Verification Layer ⏳ (post-execution, lazy init)")
        
        # Note: Tier 5 runs AFTER tool execution to verify results
    
    async def validate_tool_call(self, tool_call: Dict[str, Any], 
                                user_id: str = "default",
                                session_id: Optional[str] = None) -> ValidationResult:
        """
        Execute complete validation wall analysis.
        
        Returns ValidationResult with approval/denial decision.
        This is the main entry point for all tool validations.
        """
        self.stats["total_validations"] += 1
        
        # Initialize validation result
        result = ValidationResult(
            approved=True,  # Start optimistic, fail if issues found
            risk_level=RiskLevel.SAFE,
            tool_name=tool_call.get("tool", "unknown"),
            validation_id=str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            timestamp=datetime.now()
        )
        
        try:
            logger.info(f"🛡️ Validating: {result.tool_name} (user: {user_id})")
            
            # TIER 1: Schema Validation
            if not await self._run_schema_validation(tool_call, result):
                self.stats["schema_failures"] += 1
                result.approved = False
                result.risk_level = RiskLevel.BLOCKED
            else:
                result.stages_passed.append(ValidationStage.SCHEMA)
            
            # TIER 2: Policy Engine (only if schema passed)
            if result.approved and not await self._run_policy_validation(tool_call, result):
                self.stats["policy_failures"] += 1
                # Policy failures may not always block, depends on specific violation
            else:
                result.stages_passed.append(ValidationStage.POLICY)
            
            # TIER 3: Code Linter (only if previous tiers passed)
            if result.approved and not await self._run_code_linting(tool_call, result):
                self.stats["linter_failures"] += 1
                result.approved = False
                result.risk_level = RiskLevel.BLOCKED
            else:
                result.stages_passed.append(ValidationStage.LINTER)
            
            # TIER 4: Audit Logging (always runs)
            audit_id = await self._run_audit_logging(tool_call, result)
            result.metadata["audit_id"] = audit_id
            result.stages_passed.append(ValidationStage.AUDIT)
            
            # Final decision logic
            self._finalize_validation_decision(result)
            
            # Update statistics
            self._update_statistics(result)
            
            # Log final decision
            self._log_validation_decision(result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Validation wall error: {e}")
            
            # Fail secure - block on any validation error
            result.approved = False
            result.risk_level = RiskLevel.BLOCKED
            result.add_error(
                ValidationStage.AUDIT,
                "VALIDATION_WALL_ERROR",
                f"Validation system error: {str(e)}",
                RiskLevel.BLOCKED
            )
            
            return result
    
    async def _run_schema_validation(self, tool_call: Dict[str, Any], result: ValidationResult) -> bool:
        """Run Tier 1: Schema Validation."""
        try:
            logger.debug("🔍 Tier 1: Schema validation...")
            return self.schema_validator.validate_tool_call(tool_call, result)
        except Exception as e:
            result.add_error(
                ValidationStage.SCHEMA,
                "SCHEMA_VALIDATION_ERROR",
                f"Schema validation failed: {str(e)}",
                RiskLevel.BLOCKED
            )
            return False
    
    async def _run_policy_validation(self, tool_call: Dict[str, Any], result: ValidationResult) -> bool:
        """Run Tier 2: Policy Engine."""
        try:
            logger.debug("🔍 Tier 2: Policy validation...")
            return self.policy_engine.validate_policy(tool_call, result)
        except Exception as e:
            result.add_error(
                ValidationStage.POLICY,
                "POLICY_VALIDATION_ERROR",
                f"Policy validation failed: {str(e)}",
                RiskLevel.BLOCKED
            )
            return False
    
    async def _run_code_linting(self, tool_call: Dict[str, Any], result: ValidationResult) -> bool:
        """Run Tier 3: Code Linting."""
        try:
            logger.debug("🔍 Tier 3: Code linting...")
            return self.code_linter.lint_tool_call(tool_call, result)
        except Exception as e:
            result.add_error(
                ValidationStage.LINTER,
                "LINTER_VALIDATION_ERROR",
                f"Code linting failed: {str(e)}",
                RiskLevel.BLOCKED
            )
            return False
    
    async def _run_audit_logging(self, tool_call: Dict[str, Any], result: ValidationResult) -> str:
        """Run Tier 4: Audit Logging."""
        try:
            logger.debug("🔍 Tier 4: Audit logging...")
            return self.audit_logger.log_validation_result(tool_call, result)
        except Exception as e:
            result.add_error(
                ValidationStage.AUDIT,
                "AUDIT_LOGGING_ERROR",
                f"Audit logging failed: {str(e)}",
                RiskLevel.REVIEW
            )
            return "audit_error"
    
    def _finalize_validation_decision(self, result: ValidationResult):
        """Finalize the validation decision based on all tiers."""
        
        # If any blocking errors, deny execution
        blocking_errors = [e for e in result.errors if e.severity == RiskLevel.BLOCKED]
        if blocking_errors:
            result.approved = False
            result.risk_level = RiskLevel.BLOCKED
            return
        
        # Set confirmation requirements based on risk level
        if result.risk_level in [RiskLevel.CONFIRM, RiskLevel.OWNER_ROOT]:
            result.requires_confirmation = True
        
        # Set dry run requirements for risky operations
        if result.risk_level == RiskLevel.REVIEW and len(result.warnings) > 0:
            result.requires_dry_run = True
        
        # Set execution timeout based on risk level
        timeout_map = {
            RiskLevel.SAFE: 30,      # 30 seconds for safe operations
            RiskLevel.REVIEW: 60,    # 1 minute for review operations  
            RiskLevel.CONFIRM: 300,  # 5 minutes for confirmed operations
            RiskLevel.OWNER_ROOT: 900 # 15 minutes for critical operations
        }
        result.execution_timeout = timeout_map.get(result.risk_level, 60)
    
    def _update_statistics(self, result: ValidationResult):
        """Update validation statistics."""
        if result.approved:
            self.stats["approvals"] += 1
        else:
            self.stats["blocks"] += 1
        
        if result.requires_confirmation:
            self.stats["confirmations_required"] += 1
    
    def _log_validation_decision(self, result: ValidationResult):
        """Log the final validation decision."""
        if result.approved:
            if result.requires_confirmation:
                logger.info(f"⚠️ APPROVAL WITH CONFIRMATION: {result.tool_name} (risk: {result.risk_level.value})")
            else:
                logger.info(f"✅ APPROVED: {result.tool_name} (risk: {result.risk_level.value})")
        else:
            logger.warning(f"🚫 BLOCKED: {result.tool_name} - {len(result.errors)} errors")
            for error in result.errors:
                logger.warning(f"   • {error}")
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get validation wall statistics and status."""
        return {
            "status": "active",
            "tiers": {
                "schema_validator": "active",
                "policy_engine": "active", 
                "code_linter": "active",
                "audit_logger": "active",
                "verification_layer": "active" if self._verification_initialized else "pending"
            },
            "statistics": self.stats.copy(),
            "policy_summary": self.policy_engine.get_policy_summary(),
            "available_tools": self.schema_validator.get_available_tools(),
            "recent_validations": self.audit_logger.get_recent_validations(5),
            "security_summary": self.audit_logger.get_security_summary(),
            "verification_summary": self.verification_layer.get_verification_summary() if self._verification_initialized else {"status": "not_initialized"}
        }
    
    def get_tool_risk_assessment(self, tool_name: str) -> Dict[str, Any]:
        """Get risk assessment for a specific tool."""
        schema = self.schema_validator.get_tool_schema(tool_name)
        policy_summary = self.policy_engine.get_policy_summary()
        
        return {
            "tool": tool_name,
            "has_schema": schema is not None,
            "default_risk_level": policy_summary.get("tool_risk_levels", {}).get(tool_name, "review"),
            "schema_requirements": schema.get("properties", {}).get("args", {}) if schema else None,
            "validation_tiers": ["schema", "policy", "linter", "audit", "verification"]
        }
    
    async def dry_run_validation(self, tool_call: Dict[str, Any], user_id: str = "default") -> ValidationResult:
        """
        Perform dry-run validation without executing or logging to audit trail.
        Useful for testing and preview purposes.
        """
        # Create temporary result for dry run
        result = ValidationResult(
            approved=True,
            risk_level=RiskLevel.SAFE,
            tool_name=tool_call.get("tool", "unknown"),
            validation_id=f"dry_run_{uuid.uuid4()}",
            user_id=user_id,
            timestamp=datetime.now()
        )
        
        # Run only schema and policy validation (skip audit logging)
        await self._run_schema_validation(tool_call, result)
        if result.approved:
            await self._run_policy_validation(tool_call, result)
        if result.approved:
            await self._run_code_linting(tool_call, result)
        
        self._finalize_validation_decision(result)
        
        # Mark as dry run
        result.metadata["dry_run"] = True
        
        return result
    
    async def initialize_verification_layer(self) -> bool:
        """Initialize the verification layer (Tier 5) for post-execution verification."""
        if not self._verification_initialized:
            try:
                logger.info("🔍 Initializing Tier 5: Verification Layer...")
                
                # Lazy import to avoid circular dependencies
                from ..verification.verification_layer import VerificationLayer
                
                # Initialize verification layer
                self.verification_layer = VerificationLayer()
                if await self.verification_layer.initialize():
                    self._verification_initialized = True
                    logger.info("✅ Tier 5: Verification Layer ready for post-execution verification")
                    return True
                else:
                    logger.error("❌ Failed to initialize Tier 5: Verification Layer")
                    return False
            except Exception as e:
                logger.error(f"❌ Verification layer initialization error: {e}")
                return False
        return True
    
    async def verify_tool_execution(self, tool_call: Dict[str, Any], tool_result: Dict[str, Any], 
                                  user_id: str = "default", session_id: Optional[str] = None) -> ValidationResult:
        """
        Execute Tier 5: Post-execution verification of tool results.
        
        This runs AFTER tool execution to verify:
        1. Research claims against citations (NLI verification)
        2. Tool post-conditions (files exist, apps focused, etc.)
        
        Args:
            tool_call: Original tool call that was executed
            tool_result: Result returned by tool execution
            user_id: User identifier for audit trail
            session_id: Session identifier for audit trail
            
        Returns:
            ValidationResult indicating if verification passed
        """
        # Ensure verification layer is initialized
        if not await self.initialize_verification_layer():
            # Return failed verification result
            result = ValidationResult(
                approved=False,
                risk_level=RiskLevel.BLOCKED,
                tool_name=tool_call.get("tool", "unknown"),
                validation_id=f"verification_{uuid.uuid4()}",
                user_id=user_id,
                session_id=session_id,
                timestamp=datetime.now()
            )
            result.add_error(
                ValidationStage.VERIFICATION,
                "VERIFICATION_INIT_FAILED",
                "Verification layer initialization failed",
                RiskLevel.BLOCKED
            )
            return result
        
        # Create verification result
        result = ValidationResult(
            approved=True,  # Start optimistic
            risk_level=RiskLevel.SAFE,
            tool_name=tool_call.get("tool", "unknown"),
            validation_id=f"verification_{uuid.uuid4()}",
            user_id=user_id,
            session_id=session_id,
            timestamp=datetime.now()
        )
        
        try:
            logger.info(f"🔍 Tier 5 verification: {result.tool_name}")
            
            # Run verification layer
            verification_passed = await self.verification_layer.verify_tool_execution(tool_call, tool_result, result)
            
            if not verification_passed:
                self.stats["verification_failures"] += 1
                result.approved = False
                # Risk level is set by verification layer based on failure policy
            else:
                logger.info(f"✅ Tier 5 verification passed: {result.tool_name}")
            
            # Log verification decision to audit trail  
            audit_id = await self._run_verification_audit_logging(tool_call, result)
            result.metadata["verification_audit_id"] = audit_id
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Post-execution verification error: {e}")
            
            # Fail secure - block on verification error
            self.stats["verification_failures"] += 1
            result.approved = False
            result.risk_level = RiskLevel.BLOCKED
            result.add_error(
                ValidationStage.VERIFICATION,
                "VERIFICATION_ERROR",
                f"Post-execution verification failed: {str(e)}",
                RiskLevel.BLOCKED
            )
            
            return result
    
    async def _run_verification_audit_logging(self, tool_call: Dict[str, Any], result: ValidationResult) -> str:
        """Run audit logging for verification phase."""
        try:
            logger.debug("📝 Tier 4: Audit logging (post-execution verification)...")
            return self.audit_logger.log_validation_decision(tool_call, result)
        except Exception as e:
            result.add_error(
                ValidationStage.AUDIT,
                "AUDIT_LOGGING_ERROR",
                f"Verification audit logging failed: {str(e)}",
                RiskLevel.REVIEW
            )
            return f"verification_audit_error_{uuid.uuid4()}"
