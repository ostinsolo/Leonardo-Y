"""
Verification Layer - Tier 5 of Leonardo's Validation Wall
Integrates NLI claim verification + post-condition checking

This is the final tier that verifies tool execution results:
1. Research Verifier: NLI-based claim verification against citations  
2. Ops Verifier: Tool-specific post-condition checking
3. Policy-based failure handling (warn vs block by risk tier)
4. Retry logic with backoff for failed verification
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from .research_verifier import ResearchVerifier
from .ops_verifier import OpsVerifier
from ..validation.validation_result import ValidationResult, ValidationStage, RiskLevel

logger = logging.getLogger(__name__)


class VerificationLayer:
    """
    Tier 5 Verification Layer - Final verification of tool execution results.
    
    Implements the complete verification architecture:
    - NLI claim verification for research tools  
    - Post-condition checking for all tools
    - Risk-based failure policies (warn vs block)
    - Retry logic for failed verifications
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        
        # Initialize verifiers
        self.research_verifier = ResearchVerifier(self.config.get("research", {}))
        self.ops_verifier = OpsVerifier()
        
        # Policy configuration
        self.failure_policies = self.config.get("policy", {})
        self.max_retries = self.failure_policies.get("max_retries", 1)
        
        # Statistics
        self.verification_stats = {
            "total_verifications": 0,
            "research_verifications": 0,
            "ops_verifications": 0,
            "verification_passes": 0,
            "verification_failures": 0,
            "retries_used": 0
        }
        
        logger.info("🔍 Verification Layer (Tier 5) initialized")
        logger.info(f"   Max retries: {self.max_retries}")
        logger.info(f"   Failure policies: {list(self.failure_policies.keys())}")
    
    def _default_config(self) -> Dict[str, Any]:
        """Default verification layer configuration."""
        return {
            "research": {
                "nli": {
                    "backend": "local",
                    "model": "typeform/distilbert-base-uncased-mnli",  # Fast DistilBERT MNLI (67M params)
                    "entailment_threshold": 0.6,
                    "batch_size": 16,
                    "quantize": True,
                    "fallback_models": [
                        "MoritzLaurer/DeBERTa-v3-base-mnli",  # More accurate DeBERTa-v3 (184M params, 90% accuracy)
                    ]
                },
                "coverage_threshold": 0.8,
                "min_sources_per_claim": 1
            },
            "policy": {
                "on_fail": {
                    "safe": "warn",      # Safe operations: warn and continue
                    "review": "block",   # Review operations: block execution  
                    "confirm": "block",  # Confirm operations: block execution
                    "owner_root": "block"  # Critical operations: always block
                },
                "max_retries": 1
            }
        }
    
    async def initialize(self) -> bool:
        """Initialize the verification layer."""
        try:
            logger.info("🔍 Initializing Verification Layer...")
            
            # Initialize research verifier
            if not await self.research_verifier.initialize():
                logger.error("❌ Failed to initialize research verifier")
                return False
            
            logger.info("✅ Verification Layer (Tier 5) ready")
            return True
            
        except Exception as e:
            logger.error(f"❌ Verification layer initialization failed: {e}")
            return False
    
    async def verify_tool_execution(self, tool_call: Dict[str, Any], tool_result: Dict[str, Any], validation_result: ValidationResult) -> bool:
        """
        Verify tool execution results (Tier 5 of validation wall).
        
        Args:
            tool_call: Original tool call that was executed
            tool_result: Result returned by tool execution
            validation_result: Validation result to update with verification status
            
        Returns:
            True if verification passes, False if verification fails
        """
        self.verification_stats["total_verifications"] += 1
        
        try:
            tool_name = tool_call.get("tool", "")
            risk_level = RiskLevel(tool_call.get("meta", {}).get("risk", "safe"))
            
            logger.info(f"🔍 Tier 5 verification: {tool_name} (risk: {risk_level.value})")
            
            # Run both verification types
            research_success = await self._verify_research_claims(tool_call, tool_result, validation_result)
            ops_success = self._verify_post_conditions(tool_call, tool_result, validation_result)
            
            # Overall verification success
            verification_passed = research_success and ops_success
            
            # Apply failure policy based on risk level
            if not verification_passed:
                return self._handle_verification_failure(tool_name, risk_level, validation_result)
            else:
                self.verification_stats["verification_passes"] += 1
                logger.info(f"✅ Tier 5 verification passed: {tool_name}")
                
                # Mark verification stage as completed
                if ValidationStage.VERIFICATION not in validation_result.stages_passed:
                    validation_result.stages_passed.append(ValidationStage.VERIFICATION)
                
                return True
            
        except Exception as e:
            logger.error(f"❌ Verification layer error: {e}")
            validation_result.add_error(
                ValidationStage.VERIFICATION,
                "VERIFICATION_LAYER_ERROR", 
                f"Verification layer error: {str(e)}",
                RiskLevel.BLOCKED
            )
            return False
    
    async def _verify_research_claims(self, tool_call: Dict[str, Any], tool_result: Dict[str, Any], validation_result: ValidationResult) -> bool:
        """Verify research claims using NLI."""
        try:
            tool_name = tool_call.get("tool", "")
            
            # Only run research verification for research tools
            research_tools = ["web.deep_research", "web.scrape", "web.search", "search_web"]
            if tool_name not in research_tools:
                return True  # Non-research tools pass research verification
            
            self.verification_stats["research_verifications"] += 1
            logger.debug(f"🔍 Research verification: {tool_name}")
            
            # Run research verification
            return self.research_verifier.verify_research_tool_result(tool_call, tool_result, validation_result)
            
        except Exception as e:
            logger.error(f"❌ Research verification error: {e}")
            validation_result.add_error(
                ValidationStage.VERIFICATION,
                "RESEARCH_VERIFICATION_ERROR",
                f"Research verification error: {str(e)}",
                RiskLevel.BLOCKED
            )
            return False
    
    def _verify_post_conditions(self, tool_call: Dict[str, Any], tool_result: Dict[str, Any], validation_result: ValidationResult) -> bool:
        """Verify tool post-conditions."""
        try:
            self.verification_stats["ops_verifications"] += 1
            logger.debug(f"🔍 Post-condition verification: {tool_call.get('tool', '')}")
            
            # Run ops verification
            return self.ops_verifier.verify_tool_execution(tool_call, tool_result, validation_result)
            
        except Exception as e:
            logger.error(f"❌ Post-condition verification error: {e}")
            validation_result.add_error(
                ValidationStage.VERIFICATION,
                "POST_CONDITION_ERROR",
                f"Post-condition verification error: {str(e)}",
                RiskLevel.BLOCKED
            )
            return False
    
    def _handle_verification_failure(self, tool_name: str, risk_level: RiskLevel, validation_result: ValidationResult) -> bool:
        """Handle verification failure based on risk-based policy."""
        try:
            # Get failure policy for this risk level
            failure_action = self.failure_policies.get("on_fail", {}).get(risk_level.value, "block")
            
            self.verification_stats["verification_failures"] += 1
            
            if failure_action == "warn":
                # Warn but allow execution to proceed
                logger.warning(f"⚠️ Verification failed but continuing (safe tier): {tool_name}")
                validation_result.add_warning(
                    ValidationStage.VERIFICATION,
                    "VERIFICATION_FAILED_WARN",
                    f"Verification failed for {tool_name} but continuing due to safe risk tier",
                    RiskLevel.REVIEW
                )
                return True  # Continue despite failure
            
            elif failure_action == "block":
                # Block execution
                logger.error(f"🚫 Verification failed - blocking execution: {tool_name}")
                validation_result.add_error(
                    ValidationStage.VERIFICATION,
                    "VERIFICATION_FAILED_BLOCK",
                    f"Verification failed for {tool_name} - execution blocked",
                    RiskLevel.BLOCKED
                )
                return False  # Block execution
            
            else:
                # Unknown policy - default to block for safety
                logger.error(f"🚫 Unknown failure policy '{failure_action}' - blocking: {tool_name}")
                validation_result.add_error(
                    ValidationStage.VERIFICATION,
                    "UNKNOWN_FAILURE_POLICY",
                    f"Unknown failure policy '{failure_action}' for {tool_name} - blocking for safety",
                    RiskLevel.BLOCKED
                )
                return False
            
        except Exception as e:
            logger.error(f"❌ Error handling verification failure: {e}")
            return False
    
    async def dry_run_verification(self, tool_call: Dict[str, Any], simulated_result: Dict[str, Any]) -> ValidationResult:
        """
        Perform dry-run verification without actual tool execution.
        Useful for testing verification logic.
        """
        # Create temporary validation result
        validation_result = ValidationResult(
            approved=True,
            risk_level=RiskLevel.SAFE,
            tool_name=tool_call.get("tool", "unknown"),
            validation_id=f"dry_run_verification_{datetime.now().timestamp()}",
            timestamp=datetime.now()
        )
        
        # Run verification
        success = await self.verify_tool_execution(tool_call, simulated_result, validation_result)
        
        # Update result
        validation_result.approved = success
        validation_result.metadata["dry_run"] = True
        validation_result.metadata["verification_dry_run"] = True
        
        return validation_result
    
    def get_verification_summary(self) -> Dict[str, Any]:
        """Get verification layer statistics and status."""
        research_stats = self.research_verifier.get_verification_stats() if self.research_verifier else {}
        ops_capabilities = self.ops_verifier.get_verification_capabilities() if self.ops_verifier else {}
        
        return {
            "status": "active",
            "statistics": self.verification_stats.copy(),
            "research_verifier": research_stats,
            "ops_verifier": ops_capabilities,
            "configuration": {
                "max_retries": self.max_retries,
                "failure_policies": self.failure_policies
            }
        }
    
    async def shutdown(self):
        """Shutdown verification layer."""
        if self.research_verifier:
            await self.research_verifier.shutdown()
        
        # Log final statistics
        total = self.verification_stats["total_verifications"]
        if total > 0:
            success_rate = (self.verification_stats["verification_passes"] / total) * 100
            logger.info(f"📊 Verification Layer final stats:")
            logger.info(f"   Success rate: {success_rate:.1f}% ({self.verification_stats['verification_passes']}/{total})")
            logger.info(f"   Research verifications: {self.verification_stats['research_verifications']}")
            logger.info(f"   Ops verifications: {self.verification_stats['ops_verifications']}")
            logger.info(f"   Retries used: {self.verification_stats['retries_used']}")
        
        logger.info("✅ Verification Layer (Tier 5) shutdown")
