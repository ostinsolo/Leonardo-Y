"""
Leonardo Verification Layer - Tier 5 of Validation Wall
NLI claim verification + post-condition checking

Components:
- NLI Local: DistilRoBERTa-MNLI for fast claim verification
- Citation Store: RAG cache with deterministic citation format  
- Research Verifier: NLI-based claim verification
- Ops Verifier: Tool-specific post-condition checking
- Verification Layer: Integrated Tier 5 verification
"""

from .nli_local import LocalNLIRunner, NLIResult, quick_entails
from .citation_store import (
    CitationStore, ClaimCitation, CitationSource, 
    ContentSpan, StoredContent
)
from .research_verifier import (
    ResearchVerifier, ClaimVerificationResult, 
    ResearchVerificationResult
)
from .ops_verifier import OpsVerifier
from .verification_layer import VerificationLayer

# Re-export validation result types
from ..validation.validation_result import ValidationResult, ValidationError, RiskLevel

__all__ = [
    # NLI Components
    "LocalNLIRunner",
    "NLIResult", 
    "quick_entails",
    
    # Citation System
    "CitationStore",
    "ClaimCitation",
    "CitationSource", 
    "ContentSpan",
    "StoredContent",
    
    # Research Verification
    "ResearchVerifier",
    "ClaimVerificationResult",
    "ResearchVerificationResult",
    
    # Operations Verification  
    "OpsVerifier",
    
    # Main Verification Layer
    "VerificationLayer",
    
    # Validation Results
    "ValidationResult",
    "ValidationError", 
    "RiskLevel"
]