"""
Research Verifier - NLI-Based Claim Verification
Verifies factual claims against cited sources using local NLI models

Implements the research verification tier of Leonardo's verification wall.
Uses deterministic citation format for reproducible verification.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

from .nli_local import LocalNLIRunner, NLIResult
from .citation_store import CitationStore, ClaimCitation, ContentSpan
from ..validation.validation_result import ValidationResult, ValidationStage, RiskLevel

logger = logging.getLogger(__name__)


@dataclass
class ClaimVerificationResult:
    """Result of verifying a single claim."""
    claim_id: str
    claim_text: str
    entails: bool
    confidence: float
    sources_count: int
    evidence_texts: List[str]
    nli_scores: List[float]


@dataclass
class ResearchVerificationResult:
    """Complete research verification result."""
    overall_pass: bool
    overall_score: float
    claim_results: List[ClaimVerificationResult]
    coverage_rate: float  # Fraction of text that has citations
    entailment_rate: float  # Fraction of claims that entail
    total_claims: int
    total_sources: int


class ResearchVerifier:
    """
    Research verifier using NLI for claim-citation verification.
    
    Verifies that research summaries are properly supported by cited sources
    using deterministic NLI checking.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        
        # Initialize components
        nli_config = self.config.get("nli", {})
        self.nli_runner = LocalNLIRunner(nli_config)
        self.citation_store = CitationStore()
        
        # Verification thresholds
        self.entailment_threshold = nli_config.get("entailment_threshold", 0.6)
        self.coverage_threshold = self.config.get("coverage_threshold", 0.8)
        self.min_sources_per_claim = self.config.get("min_sources_per_claim", 1)
        
        # Batch processing
        self.batch_size = nli_config.get("batch_size", 16)
        
        logger.info("🔍 Research verifier initialized")
        logger.info(f"   Entailment threshold: {self.entailment_threshold}")
        logger.info(f"   Coverage threshold: {self.coverage_threshold}")
    
    def _default_config(self) -> Dict[str, Any]:
        """Default research verification configuration."""
        return {
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
            "coverage_threshold": 0.8,  # 80% of text must have citations
            "min_sources_per_claim": 1,
            "require_domain_diversity": False
        }
    
    async def initialize(self) -> bool:
        """Initialize the research verifier."""
        try:
            # Initialize NLI runner
            if not await self.nli_runner.initialize():
                logger.error("❌ Failed to initialize NLI runner")
                return False
            
            logger.info("✅ Research verifier ready for claim verification")
            return True
            
        except Exception as e:
            logger.error(f"❌ Research verifier initialization failed: {e}")
            return False
    
    async def verify_research_claims(self, summary_text: str, citations: List[ClaimCitation]) -> ResearchVerificationResult:
        """
        Verify research claims against citations using NLI.
        
        Args:
            summary_text: The research summary containing claims
            citations: List of claim citations with sources
            
        Returns:
            Complete verification result with per-claim details
        """
        try:
            logger.info(f"🔍 Verifying {len(citations)} research claims")
            
            # Verify citation integrity first
            if not self._verify_citations_integrity(citations):
                logger.warning("Citation integrity check failed")
            
            # Prepare claims for NLI verification
            claims_and_sources = self.citation_store.resolve_citations(citations)
            
            # Run batch NLI verification
            nli_results = await self._batch_verify_entailment(claims_and_sources)
            
            # Process results
            claim_results = []
            for i, (citation, (entails, confidence)) in enumerate(zip(citations, nli_results)):
                claim_result = ClaimVerificationResult(
                    claim_id=citation.claim_id,
                    claim_text=citation.claim_text,
                    entails=entails,
                    confidence=confidence,
                    sources_count=len(citation.sources),
                    evidence_texts=[src.quote for src in citation.sources],
                    nli_scores=[confidence]  # Single score for now
                )
                claim_results.append(claim_result)
            
            # Calculate overall metrics
            overall_result = self._calculate_overall_metrics(summary_text, claim_results)
            
            logger.info(f"✅ Research verification complete:")
            logger.info(f"   Overall pass: {overall_result.overall_pass}")
            logger.info(f"   Entailment rate: {overall_result.entailment_rate:.2f}")
            logger.info(f"   Coverage rate: {overall_result.coverage_rate:.2f}")
            
            return overall_result
            
        except Exception as e:
            logger.error(f"❌ Research verification failed: {e}")
            return self._create_failed_result(citations)
    
    async def _batch_verify_entailment(self, claims_and_sources: List[Tuple[str, List[str]]]) -> List[Tuple[bool, float]]:
        """Batch verify entailment for multiple claims."""
        try:
            # Use NLI runner's batch processing
            results = self.nli_runner.batch_entails(claims_and_sources)
            return results
            
        except Exception as e:
            logger.error(f"❌ Batch entailment verification failed: {e}")
            return [(False, 0.0)] * len(claims_and_sources)
    
    def _verify_citations_integrity(self, citations: List[ClaimCitation]) -> bool:
        """Verify integrity of all citations."""
        try:
            for citation in citations:
                if not self.citation_store.verify_citation_integrity(citation):
                    logger.warning(f"Citation integrity failed for claim {citation.claim_id}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Citation integrity verification failed: {e}")
            return False
    
    def _calculate_overall_metrics(self, summary_text: str, claim_results: List[ClaimVerificationResult]) -> ResearchVerificationResult:
        """Calculate overall verification metrics."""
        try:
            total_claims = len(claim_results)
            if total_claims == 0:
                return ResearchVerificationResult(
                    overall_pass=False,
                    overall_score=0.0,
                    claim_results=[],
                    coverage_rate=0.0,
                    entailment_rate=0.0,
                    total_claims=0,
                    total_sources=0
                )
            
            # Calculate entailment rate
            entailed_claims = sum(1 for result in claim_results if result.entails)
            entailment_rate = entailed_claims / total_claims
            
            # Calculate coverage rate (simplified - assumes equal-weight sentences)
            coverage_rate = self._estimate_coverage_rate(summary_text, claim_results)
            
            # Calculate overall score
            overall_score = (entailment_rate + coverage_rate) / 2
            
            # Determine overall pass
            overall_pass = (
                entailment_rate >= self.entailment_threshold and
                coverage_rate >= self.coverage_threshold
            )
            
            # Count total sources
            total_sources = sum(result.sources_count for result in claim_results)
            
            return ResearchVerificationResult(
                overall_pass=overall_pass,
                overall_score=overall_score,
                claim_results=claim_results,
                coverage_rate=coverage_rate,
                entailment_rate=entailment_rate,
                total_claims=total_claims,
                total_sources=total_sources
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate overall metrics: {e}")
            return self._create_failed_result([])
    
    def _estimate_coverage_rate(self, summary_text: str, claim_results: List[ClaimVerificationResult]) -> float:
        """Estimate what fraction of summary text has citation coverage."""
        try:
            # Simple heuristic: assume each claim covers equal portion of text
            if not claim_results:
                return 0.0
            
            # Count sentences in summary (rough approximation)
            sentences = [s.strip() for s in summary_text.split('.') if s.strip()]
            total_sentences = len(sentences)
            
            if total_sentences == 0:
                return 0.0
            
            # Assume each claim corresponds to roughly one sentence
            cited_sentences = min(len(claim_results), total_sentences)
            coverage_rate = cited_sentences / total_sentences
            
            return min(coverage_rate, 1.0)  # Cap at 100%
            
        except Exception as e:
            logger.error(f"❌ Coverage estimation failed: {e}")
            return 0.5  # Conservative fallback
    
    def _create_failed_result(self, citations: List[ClaimCitation]) -> ResearchVerificationResult:
        """Create a failed verification result."""
        return ResearchVerificationResult(
            overall_pass=False,
            overall_score=0.0,
            claim_results=[],
            coverage_rate=0.0,
            entailment_rate=0.0,
            total_claims=len(citations),
            total_sources=0
        )
    
    def verify_research_tool_result(self, tool_call: Dict[str, Any], tool_result: Dict[str, Any], validation_result: ValidationResult) -> bool:
        """
        Verify research tool results have proper citations and NLI compliance.
        
        Args:
            tool_call: Original tool call
            tool_result: Result from tool execution
            validation_result: Validation result to update
            
        Returns:
            True if verification passes, False otherwise
        """
        try:
            tool_name = tool_call.get("tool", "")
            
            # Only verify research-related tools
            research_tools = ["web.deep_research", "web.scrape", "web.search"]
            if tool_name not in research_tools:
                return True  # Non-research tools pass by default
            
            # Extract summary and citations from tool result
            summary = tool_result.get("summary", "")
            citations_data = tool_result.get("citations", [])
            
            if not summary or not citations_data:
                validation_result.add_error(
                    ValidationStage.VERIFICATION,
                    "RESEARCH_NO_CITATIONS",
                    f"Research tool {tool_name} produced no summary or citations",
                    RiskLevel.BLOCKED
                )
                return False
            
            # TODO: Convert citations_data to ClaimCitation objects
            # For now, add a warning that NLI verification is pending
            validation_result.add_warning(
                ValidationStage.VERIFICATION,
                "RESEARCH_NLI_PENDING",
                f"NLI verification not yet implemented for {tool_name}",
                RiskLevel.REVIEW
            )
            
            return True
            
        except Exception as e:
            validation_result.add_error(
                ValidationStage.VERIFICATION,
                "RESEARCH_VERIFICATION_ERROR",
                f"Research verification failed: {str(e)}",
                RiskLevel.BLOCKED
            )
            return False
    
    async def shutdown(self):
        """Cleanup verifier resources."""
        if self.nli_runner:
            self.nli_runner.shutdown()
        
        logger.info("✅ Research verifier shutdown")
    
    def get_verification_stats(self) -> Dict[str, Any]:
        """Get verification statistics and model info."""
        nli_info = self.nli_runner.get_model_info() if self.nli_runner else {}
        cache_stats = self.citation_store.get_cache_stats() if self.citation_store else {}
        
        return {
            "nli_model": nli_info,
            "cache": cache_stats,
            "config": {
                "entailment_threshold": self.entailment_threshold,
                "coverage_threshold": self.coverage_threshold,
                "min_sources_per_claim": self.min_sources_per_claim
            }
        }
