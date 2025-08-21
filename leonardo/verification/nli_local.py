"""
Local NLI (Natural Language Inference) for Claim Verification
Distilled MNLI model for fast, offline claim checking against citations

Uses DistilRoBERTa-MNLI or DeBERTa-v3-small-MNLI for speed.
Batched processing with configurable entailment thresholds.
"""

import logging
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json

# Transformers for NLI models
try:
    from transformers import (
        AutoTokenizer, AutoModelForSequenceClassification,
        pipeline, Pipeline
    )
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

# from ..config import LeonardoConfig  # Config import optional for now

logger = logging.getLogger(__name__)


@dataclass
class NLIResult:
    """Result of NLI inference."""
    entails: bool
    score: float
    label: str  # 'ENTAILMENT', 'CONTRADICTION', 'NEUTRAL'
    confidence: float


class LocalNLIRunner:
    """
    Local NLI model for claim verification.
    Optimized for speed with distilled models and batching.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        
        # Model configuration - using validated HuggingFace NLI models
        self.model_name = self.config.get("model", "typeform/distilbert-base-uncased-mnli")
        self.entailment_threshold = self.config.get("entailment_threshold", 0.6)
        self.batch_size = self.config.get("batch_size", 16)
        self.quantize = self.config.get("quantize", True)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Model pipeline
        self.pipeline: Optional[Pipeline] = None
        self.model_loaded = False
        
        logger.info(f"🔍 NLI Runner initialized: {self.model_name}")
        logger.info(f"   Threshold: {self.entailment_threshold}, Batch: {self.batch_size}")
    
    def _default_config(self) -> Dict[str, Any]:
        """Default NLI configuration."""
        return {
            "backend": "local",
            "model": "typeform/distilbert-base-uncased-mnli",  # Fast DistilBERT MNLI (67M params)
            "entailment_threshold": 0.6,
            "batch_size": 16,
            "quantize": True,
            "fallback_models": [
                "MoritzLaurer/DeBERTa-v3-base-mnli",  # More accurate DeBERTa-v3 (184M params, 90% accuracy)
            ]
        }
    
    async def initialize(self) -> bool:
        """Initialize the NLI model pipeline."""
        if not TRANSFORMERS_AVAILABLE:
            logger.error("❌ Transformers not available for NLI")
            return False
        
        # Check for testing mode
        if self.config.get("testing_mode", False):
            logger.info("🧪 NLI Testing mode - using mock entailment")
            self.model_loaded = True
            return True
        
        # Try primary model first, then fallbacks
        models_to_try = [self.model_name] + self.config.get("fallback_models", [])
        
        for model_name in models_to_try:
            try:
                logger.info(f"🧠 Loading NLI model: {model_name}")
                
                # Initialize pipeline with appropriate settings
                pipeline_kwargs = {
                    "task": "text-classification",
                    "model": model_name,
                    "device": 0 if self.device == "cuda" else -1,
                    "return_all_scores": True
                }
                
                # Add quantization if requested and available
                if self.quantize and hasattr(torch, "quantization"):
                    try:
                        pipeline_kwargs["model_kwargs"] = {"torch_dtype": torch.float16}
                        logger.info("   Using FP16 quantization")
                    except Exception:
                        logger.warning("   FP16 quantization not available")
                
                self.pipeline = pipeline(**pipeline_kwargs)
                self.model_loaded = True
                self.model_name = model_name  # Update to successful model
                
                logger.info(f"✅ NLI model loaded: {model_name}")
                return True
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to load {model_name}: {e}")
                if model_name == models_to_try[-1]:  # Last model failed
                    logger.error(f"❌ All NLI models failed to load")
                    return False
                else:
                    logger.info(f"🔄 Trying fallback model...")
                    continue
        
        # Should not reach here, but fallback
        logger.error(f"❌ Unexpected NLI model loading error")
        return False
    
    def entails(self, claim: str, evidence_sources: List[str]) -> Tuple[bool, float]:
        """
        Check if claim is entailed by evidence sources.
        
        Args:
            claim: The claim to verify
            evidence_sources: List of source text snippets
            
        Returns:
            (entails, confidence_score)
        """
        if not self.model_loaded:
            logger.warning("NLI model not loaded, returning False")
            return False, 0.0
        
        if not evidence_sources:
            logger.warning(f"No evidence sources for claim: {claim[:50]}...")
            return False, 0.0
        
        # Testing mode - use simple keyword matching
        if self.config.get("testing_mode", False):
            return self._mock_entailment(claim, evidence_sources)
        
        try:
            # Check claim against each evidence source
            results = []
            for evidence in evidence_sources:
                result = self._check_entailment(claim, evidence)
                results.append(result)
            
            # Aggregate results - claim is entailed if ANY source entails it
            best_result = max(results, key=lambda x: x.score if x.entails else 0.0)
            
            entails = best_result.entails
            confidence = best_result.score
            
            logger.debug(f"NLI: {claim[:30]}... → {entails} ({confidence:.3f})")
            return entails, confidence
            
        except Exception as e:
            logger.error(f"❌ NLI entailment check failed: {e}")
            return False, 0.0
    
    def batch_entails(self, claims_and_sources: List[Tuple[str, List[str]]]) -> List[Tuple[bool, float]]:
        """
        Batch process multiple claim-evidence pairs.
        
        Args:
            claims_and_sources: List of (claim, evidence_sources) tuples
            
        Returns:
            List of (entails, confidence_score) tuples
        """
        if not self.model_loaded:
            logger.warning("NLI model not loaded")
            return [(False, 0.0)] * len(claims_and_sources)
        
        try:
            results = []
            
            # Process in batches for efficiency
            for i in range(0, len(claims_and_sources), self.batch_size):
                batch = claims_and_sources[i:i + self.batch_size]
                batch_results = []
                
                for claim, evidence_sources in batch:
                    entails, confidence = self.entails(claim, evidence_sources)
                    batch_results.append((entails, confidence))
                
                results.extend(batch_results)
                
                if len(batch) == self.batch_size:
                    logger.debug(f"Processed NLI batch: {i//self.batch_size + 1}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Batch NLI processing failed: {e}")
            return [(False, 0.0)] * len(claims_and_sources)
    
    def _check_entailment(self, premise: str, hypothesis: str) -> NLIResult:
        """Check if premise entails hypothesis using NLI model."""
        try:
            # Format input for NLI model
            input_text = f"{premise} [SEP] {hypothesis}"
            
            # Run inference
            results = self.pipeline(input_text)
            
            # Parse results - find entailment score
            entailment_score = 0.0
            contradiction_score = 0.0
            neutral_score = 0.0
            
            for result in results[0]:  # First (and only) input
                label = result['label']
                score = result['score']
                
                if label in ['ENTAILMENT', 'entailment']:
                    entailment_score = score
                elif label in ['CONTRADICTION', 'contradiction']:
                    contradiction_score = score  
                elif label in ['NEUTRAL', 'neutral']:
                    neutral_score = score
            
            # Determine if entailed based on threshold
            entails = entailment_score >= self.entailment_threshold
            
            # Use entailment score as confidence
            confidence = entailment_score
            best_label = max(
                [('ENTAILMENT', entailment_score), 
                 ('CONTRADICTION', contradiction_score), 
                 ('NEUTRAL', neutral_score)],
                key=lambda x: x[1]
            )[0]
            
            return NLIResult(
                entails=entails,
                score=entailment_score,
                label=best_label,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"❌ NLI inference error: {e}")
            return NLIResult(
                entails=False,
                score=0.0,
                label="ERROR",
                confidence=0.0
            )
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        return {
            "model_name": self.model_name,
            "loaded": self.model_loaded,
            "device": self.device,
            "entailment_threshold": self.entailment_threshold,
            "batch_size": self.batch_size,
            "quantized": self.quantize
        }
    
    def shutdown(self):
        """Clean up model resources."""
        if self.pipeline:
            # Clear GPU memory if using CUDA
            if hasattr(self.pipeline.model, 'to'):
                self.pipeline.model.to('cpu')
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        
        self.pipeline = None
        self.model_loaded = False
        logger.info("✅ NLI model shutdown")
    
    def _mock_entailment(self, claim: str, evidence_sources: List[str]) -> Tuple[bool, float]:
        """Mock entailment for testing mode using keyword overlap."""
        try:
            claim_words = set(word.lower().strip() for word in claim.split() if len(word.strip()) > 2)
            
            best_score = 0.0
            for evidence in evidence_sources:
                evidence_words = set(word.lower().strip() for word in evidence.split() if len(word.strip()) > 2)
                
                # Simple Jaccard similarity with minimum boost
                intersection = len(claim_words & evidence_words)
                union = len(claim_words | evidence_words)
                
                if union > 0:
                    score = intersection / union
                    # Add small boost for any overlap to ensure positive scores
                    if intersection > 0:
                        score = max(score, 0.3)  # Minimum 30% if any words match
                    best_score = max(best_score, score)
            
            # If no good overlap, still give minimal score for testing
            if best_score == 0.0 and evidence_sources:
                best_score = 0.1  # Minimal confidence for testing
            
            # Apply threshold
            entails = best_score >= self.entailment_threshold
            
            logger.debug(f"🧪 Mock NLI: {claim[:30]}... → {entails} ({best_score:.3f})")
            return entails, best_score
            
        except Exception as e:
            logger.error(f"❌ Mock entailment error: {e}")
            return False, 0.0


# Convenience function for quick NLI checks
async def quick_entails(claim: str, evidence: str, threshold: float = 0.6, testing_mode: bool = True) -> Tuple[bool, float]:
    """Quick entailment check for single claim-evidence pair."""
    config = {
        "entailment_threshold": threshold,
        "testing_mode": testing_mode  # Default to testing mode for quick checks
    }
    nli = LocalNLIRunner(config)
    
    if await nli.initialize():
        result = nli.entails(claim, [evidence])
        nli.shutdown()
        return result
    else:
        return False, 0.0
